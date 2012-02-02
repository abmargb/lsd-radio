from flask import Flask, render_template, request, redirect, url_for
import logging
import simplejson, urllib
import os
import utils
from config import RADIO_ROOT, SERVER_URL

app = Flask(__name__)

@app.route('/vote', methods=["POST"])
def vote():
    
    vote = request.form["vote"]
    
    url = "http://gdata.youtube.com/feeds/api/videos?q=%s&max-results=1&v=2&alt=jsonc" % urllib.quote_plus(vote)
    result = simplejson.load(urllib.urlopen(url))
    video_id = result['data']['items'][0]['id']
    
    utils.append(utils.get_path(RADIO_ROOT, 'to_process_votes'), video_id)
    
    return 'OK'

@app.route('/')
def index():
    return render_template("index.html", server_url=SERVER_URL)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')
    app.run(host='0.0.0.0')