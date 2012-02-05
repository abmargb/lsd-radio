from flask import Flask, render_template, request, redirect, url_for, make_response
from threading import Thread
import logging
import simplejson, urllib
import os
import utils
import string
import random

from config import RADIO_ROOT, SERVER_URL, ICES_PID, STATUS_PAGE, ICES_PIPE
from xml.dom import minidom

app = Flask(__name__)
unlike_votes = []
like_votes = []
current_status = {'satisfaction' : 0.5, 'song': '', 'listeners': 0}

LISTENERS_IDX = 14
PLAYING_IDX = 16

@app.route('/vote', methods=["POST"])
def vote():
    
    vote = request.form["vote"]
    
    params = urllib.urlencode({'q': vote.encode('utf-8'), 'max-results': '1', 'v': '2', 'alt': 'jsonc'})
    
    url = "http://gdata.youtube.com/feeds/api/videos?%s" % params
    result = simplejson.load(urllib.urlopen(url))
    item = result['data']['items'][0]
    
    video_json = simplejson.dumps({"id": item['id'], "title": item['title']})
    
    utils.append(utils.get_path(RADIO_ROOT, 'to_process_votes'), video_json)
    
    return current_status['satisfaction']

def get_vote(token):
    vote = 'none'
    if (token):
        if (token in unlike_votes):
            vote = 'unlike'
        if (token in like_votes):
            vote = 'like'
    return vote

def update_satisfaction():
    
    def skip_song():
        f = open(ICES_PID, 'r')
        pid = f.readline()

        print "Skipping..."
        os.system("echo 'kill -SIGUSR1 %s' > kill_; bash kill_; rm kill_;" % pid)
        f.close()
    
    listeners = current_status['listeners']
    satisfaction = float(len(like_votes) - len(unlike_votes)) / float(max(listeners,1))
    satisfaction = (satisfaction + 1) / 2
    
    current_status['satisfaction'] = satisfaction
    
    if (satisfaction < 0.25):
        skip_song()

@app.route('/status')
def status():
    token = request.cookies.get('token')
    return simplejson.dumps({"vote": get_vote(token), "current_song": current_status['song'], 
                             "satisfaction": current_status['satisfaction']})

@app.route('/like')
def like():
    token = request.cookies.get('token')
    
    if (not token in like_votes) :
        like_votes.append(token)
        update_satisfaction()
        
    return 'OK'

@app.route('/unlike')
def unlike():
    token = request.cookies.get('token')
    
    if (not token in unlike_votes) :
        unlike_votes.append(token)
        update_satisfaction()
        
    return 'OK'

@app.route('/')
def index():
    
    def id_generator(size=8, chars=string.ascii_letters + string.digits):
        return ''.join(random.choice(chars) for x in range(size))
    
    token = request.cookies.get('token')
    vote = get_vote(token)
    resp = make_response(render_template("index.html", server_url=SERVER_URL, vote=vote))
    
    if (not token) :
        resp.set_cookie('token', id_generator())
    
    return resp

def update_song():
    del unlike_votes[0:len(unlike_votes)]
    del like_votes[0:len(like_votes)]
    current_status['satistaction'] = 0.5
    update_status()
    
def update_status():
    
    def ice_status():
        status_xml = urllib.urlopen(STATUS_PAGE).read()
        xml_doc = minidom.parseString(status_xml)
        pre = xml_doc.getElementsByTagName('pre')[0]
        status_text = pre.firstChild.nodeValue
        status_list = status_text.split(',')
        
        return status_list
    
    status_list = ice_status()
    current_status['song'] = status_list[PLAYING_IDX]
    current_status['listeners'] = int(status_list[LISTENERS_IDX])

def check_newsong():
    
    while (True):
        f = open(ICES_PIPE, 'r')
        f.read()
        update_song()
        f.close()

if __name__ == '__main__':
    
    th=Thread(target=check_newsong)
    th.start()
    update_status()
    
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')
    app.run(host='0.0.0.0')
