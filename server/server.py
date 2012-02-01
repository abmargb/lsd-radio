from flask import Flask, render_template, request, redirect, url_for
import logging
import simplejson, urllib
import os
import utils
from config import RADIO_ROOT

app = Flask(__name__)

@app.route('/vote', methods=["GET", "POST"])
def vote():
    if request.method == "POST" :
        
        vote = request.form["vote"]
        
        url = "http://gdata.youtube.com/feeds/api/videos?q=%s&max-results=1&v=2&alt=jsonc" % urllib.quote_plus(vote)
        result = simplejson.load(urllib.urlopen(url))
        video_id = result['data']['items'][0]['id']
        
        utils.append(utils.get_path(RADIO_ROOT, 'to_process_votes'), video_id)
        
    return render_template("vote.html")

@app.route('/player')
def player():
    return render_template("player.html")

@app.route('/')
def index():
    return redirect(url_for("vote"))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')
    app.run(host='0.0.0.0')