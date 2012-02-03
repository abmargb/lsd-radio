from flask import Flask, render_template, request, redirect, url_for, make_response
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

LISTENERS_IDX = 14
PLAYING_IDX = 16

@app.route('/vote', methods=["POST"])
def vote():
    
    vote = request.form["vote"]
    
    params = urllib.urlencode({'q': vote.encode('utf-8'), 'max-results': '1', 'v': '2', 'alt': 'jsonc'})
    
    url = "http://gdata.youtube.com/feeds/api/videos?%s" % params
    result = simplejson.load(urllib.urlopen(url))
    video_id = result['data']['items'][0]['id']
    
    utils.append(utils.get_path(RADIO_ROOT, 'to_process_votes'), video_id)
    
    return 'OK'

@app.route('/unlike')
def unlike():
    token = request.cookies.get('token')
    
    if (not token in unlike_votes) :
        unlike_votes.append(token)
    
    insatisfaction = float(len(unlike_votes)) / float(get_connections())
    
    if (insatisfaction > 0.5) :
        skip_song()
        
    return 'OK'

@app.route('/')
def index():
    
    token = request.cookies.get('token')
    resp = make_response(render_template("index.html", server_url=SERVER_URL))
    
    if (not token) :
        resp.set_cookie('token', id_generator())
    
    return resp

def skip_song():
    f = open(ICES_PID, 'r')
    pid = f.readline()
    os.system("kill -s SIGUSR1 %s" % pid);
    f.close()

def update_song():
    if (updated) :
        del unlike_votes[0:len(unlike_votes)]

def get_connections():
    status_xml = urllib.urlopen(STATUS_PAGE).read()
    xml_doc = minidom.parseString(status_xml)
    pre = xml_doc.getElementsByTagName('pre')[0]
    
    status_text = pre.firstChild.nodeValue
    
    status_list = status_text.split(',')
    
    return int(status_list[LISTENERS_IDX])

def id_generator(size=8, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def check_newsong():
    
    f = open(ICES_PIPE, 'r')
    while (True):
        f.read()
        update_song()

if __name__ == '__main__':
    
    th=Thread(target=check_newsong)
    th.start()
    
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')
    app.run(host='0.0.0.0')