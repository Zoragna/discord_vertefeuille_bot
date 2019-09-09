from flask import request, Flask
from hashlib import sha256

import twitchio
import os

application = Flask(__name__)
#twitch = twitchio.client.Client(client_id=os.environ["TWITCH_CLIENT_ID"])
#setup topic

@application.route("/")
def hello():
    return "Hello World!"


@application.route("/twitch/fish")
def receive_twitch_fish():
    if request.method == "POST":
        sha256("a", "b")
        # register topic change
        pass
