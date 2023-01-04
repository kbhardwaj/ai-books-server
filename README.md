# README

# API keys

Add your openai key and your huggingface key to a .env file in your local:

```
OAI_API_KEY='xyz'
HF_API_KEY='abc'
```

then pip3 install (I'm using python 3.10), and start the app:
```
$ pip3 install -r requirements.txt
$ gunicorn app:app
```

This is the [Flask](http://flask.pocoo.org/) [quick start](http://flask.pocoo.org/docs/1.0/quickstart/#a-minimal-application) example for [Render](https://render.com).

The app in this repo is deployed at [https://flask.onrender.com](https://flask.onrender.com).

## Deployment

Follow the guide at https://render.com/docs/deploy-flask.
