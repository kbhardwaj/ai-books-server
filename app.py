import atexit
import base64
import json
import hashlib
import requests
import os

from flask import Flask
from flask import request
from flask import render_template
from dotenv import load_dotenv

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

load_dotenv()

@app.route('/')
def home():
    return render_template(
        'home.html',
        title='Once upon a time...',
        description='A story generator for children.',
    )

def buildPrompt(
    name,
    age,
    gender,
    childAttributes,
    storyAttributes,
):
    # convert the inputs into a prompt.
    # convert a list of child attributes into a string.
    childAttributesString = ""
    for idx, childAttribute in enumerate(childAttributes):
        if idx == len(childAttributes) - 1:
            childAttributesString += "and " + childAttribute
        else:
            childAttributesString += childAttribute + ", "

    # convert a list of story attributes into a string.
    storyAttributesString = ""
    for idx, storyAttribute in enumerate(storyAttributes):
        if idx == len(storyAttributes) - 1:
            storyAttributesString += "and " + storyAttribute
        else:
            storyAttributesString += storyAttribute + ", "

    combinedAttributes = childAttributes + storyAttributes
    combinedAttributesString = ""
    for idx, combinedAttribute in enumerate(combinedAttributes):
        if idx == len(combinedAttributes) - 1:
            combinedAttributesString += "or " + combinedAttribute
        else:
            combinedAttributesString += combinedAttribute + ", "

    prompt = "Tell me a story about a {age} year old {gender} named {name} who demonstrates great {childAttributesString} and tell me how {pronoun} demonstrates those qualities in this childrens tale about {storyAttributesString}, but do not use the terms {combinedAttributesString}, and break up your response into paragraphs, separated by a newline.".format(
            age=age,
            name=name,
            gender=gender,
            pronoun= 'she' if gender == 'girl' else 'he',
            childAttributesString=childAttributesString,
            storyAttributesString=storyAttributesString,
            combinedAttributesString=combinedAttributesString,
        )
    return prompt

def buildImagePrompt(
    prompt,
    name,
    age,
    gender,
):
    # prompt = '{prompt}, {name} is a sweet {age} year old little {gender}, illustration by Artgerm Lau and Krenz Cushart, hyperdetailed, photorealistic colored pencil.'.format(
    # prompt = '{prompt}, {name} is a sweet, clean and pleasant {age} year old little {gender}, made in maya, blender and photoshop, octane render, In style of Yoji Shinkawa, Jackson Pollock, wojtek fus, by Makoto Shinkai, concept art, celestial, amazing, astonishing, wonderful, beautiful, highly detailed, cinematic atmosphere, dynamic dramatic cinematic lighting, aesthetic, very inspirational, anatomically correct, arthouse, colored pencil.'.format(
    prompt = '{prompt}, {name} is a sweet {age} year old little {gender}, illustration by Artgerm Lau and Krenz Cushart, hyperdetailed, photorealistic colored pencil.'.format(
        prompt=prompt,
        name=name,
        age=age,
        gender=gender
    )

    # 'made in maya, blender and photoshop, octane render, In style of Yoji Shinkawa, Jackson Pollock, wojtek fus, by Makoto Shinkai, concept art, celestial, amazing, astonishing, wonderful, beautiful, highly detailed, cinematic atmosphere, dynamic dramatic cinematic lighting, aesthetic, very inspirational, arthouse'

def generateImage(
    name,
    age,
    gender,
    childAttributes,
    storyAttributes,
    prompt,
):
    model_id = '22h/vintedois-diffusion-v0-1'
    api_url = 'https://api-inference.huggingface.co/models/{model_id}'.format(model_id=model_id)
    headers = {'Authorization': 'Bearer {}'.format(os.getenv('HF_API_KEY'))}

    prompt = '{prompt}, {name} is a sweet {age} year old little {gender}, illustration by Artgerm Lau and Krenz Cushart, hyperdetailed, photorealistic colored pencil.'.format(
        prompt=prompt,
        name=name,
        age=age,
        gender=gender
    )

    response = requests.post(
        api_url, 
        headers=headers,
        json={
            'inputs': prompt,
            'options': {
                'wait_for_model': True,
            },
        },
    )
    mimeType = response.headers['Content-type']

    result = response.content

    base64data = base64.b64encode(result).decode('utf-8')

    img = 'data:{mimeType};base64,{base64data}'.format(
        mimeType=mimeType,
        base64data=base64data
    )

    return img

def addToQueue(hashed):
    with open("data/raw-stories/index.json", "r") as jsonFile:
        data = json.load(jsonFile)
    data[hashed] = True
    with open("data/raw-stories/index.json", "w") as jsonFile:
        json.dump(data, jsonFile)

def removeFromQueue(hashed):
    with open("data/raw-stories/index.json", "r") as jsonFile:
        data = json.load(jsonFile)
    data.pop(hashed, None)
    with open("data/raw-stories/index.json", "w") as jsonFile:
        json.dump(data, jsonFile)

def addToStories(
    hashed,
    storyChunks,
):
    with open('data/stories/{}.json'.format(hashed), 'w') as f:
        f.write(json.dumps({ 'storyChunks': storyChunks }))

def registerRawStory(
    hashed,
    story,
    name,
    age,
    gender,
    childAttributes,
    storyAttributes,
):
    sentences = [s for s in story.split('\n') if s]
    with open('data/raw-stories/{}.json'.format(hashed), 'w') as f:
        f.write(json.dumps({ 
            'rawStory': {
                'sentences': sentences,
                'name': name,
                'age': age,
                'gender': gender,
                'childAttributes': childAttributes,
                'storyAttributes': storyAttributes,
            } 
        }))

    # append to index json file
    addToQueue(hashed)

def generateStory(
    hashed,
    name,
    age,
    gender,
    childAttributes,
    storyAttributes,
):
    """
    This function generates a story with images based on the raw story data.
    """
    # sentences = [s for s in story.split('\n') if s]
    with open('data/raw-stories/{}.json'.format(hashed), 'r') as jsonFile:
        data = json.load(jsonFile)

    rawStory = data['rawStory']
    sentences = rawStory['sentences']
    name = rawStory['name']
    age = rawStory['age']
    gender = rawStory['gender']
    childAttributes = rawStory['childAttributes']
    storyAttributes = rawStory['storyAttributes']
    storyChunks = []
    for sentence in sentences:
        img = generateImage(
            name,
            age,
            gender,
            childAttributes,
            storyAttributes,
            sentence,
        )
        storyChunks.append({
            'sentence': sentence,
            'image': img,
        })

    addToStories(hashed, storyChunks)
    removeFromQueue(hashed)

@app.route('/story/<path:hashed>', methods=['GET'])
def get_story(hashed):
    try:
        with open('data/stories/{}.json'.format(hashed), 'r') as jsonFile:
            data = json.load(jsonFile)

        if data.get('storyChunks'):
            return render_template(
                'home.html',
                storyChunks=data['storyChunks'],
            )
        else:
            return render_template(
                'home.html',
                message='could not find story'
            )
    except:
        return render_template(
            'home.html',
            message='could not find story, it may be processing. Try again in a few minutes.'
        )

@app.route('/submit-story-request', methods=['POST'])
def submit_story_request():
    req = request.form
    name=req['name']
    age = req['age']
    gender = req['gender']
    childAttributes = req.getlist('childAttributes')
    storyAttributes = req.getlist('storyAttributes')

    if not name or not age or not gender or not childAttributes or not storyAttributes:
        return render_template(
            'home.html',
            story='missing parameters'
        )

    prompt = buildPrompt(
        name,
        age,
        gender,
        childAttributes,
        storyAttributes,
    )

    response = requests.post(
        'https://api.openai.com/v1/completions', 
        headers={'Authorization': 'Bearer {}'.format(os.getenv('OAI_API_KEY'))},
        json={
            'model': 'text-davinci-003',
            'prompt': prompt,
            'max_tokens': 2150,
            "temperature": 0.7,
        },
    )

    response = response.json()
    story = response['choices'][0]['text']
    id = response['id']

    # # save the story to a file with md5 hash of the id as the filename
    hashed = hashlib.md5(id.encode('utf-8')).hexdigest()

    # call async function to generate the story
    registerRawStory(
        hashed,
        story,
        name,
        age,
        gender,
        childAttributes,
        storyAttributes,
    )

    return {
        'hashed': hashed,
        'story': story,
    }


def checkQueue():
    with open("data/raw-stories/index.json", "r") as jsonFile:
        data = json.load(jsonFile)
    for hashed in data:
        with open('data/raw-stories/{}.json'.format(hashed), 'r') as jsonFile:
            storyData = json.load(jsonFile)
        generateStory(
            hashed,
            storyData['rawStory']['name'],
            storyData['rawStory']['age'],
            storyData['rawStory']['gender'],
            storyData['rawStory']['childAttributes'],
            storyData['rawStory']['storyAttributes'],
        )

scheduler = BackgroundScheduler()
scheduler.add_job(func=checkQueue, trigger="interval", seconds=120)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())
