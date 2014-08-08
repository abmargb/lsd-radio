from flask import Flask, render_template, request, redirect, url_for, make_response, session, json
from threading import Thread
import logging
import simplejson, urllib, urllib2, base64
import os
import radio_utils
import string
import random
import time
import jsonpickle


from song import Song
from radio_config import RADIO_ROOT, SERVER_URL, ICES_PID, STATUS_PAGE, ICES_PIPE
from xml.dom import minidom

app = Flask(__name__)
global currentResults
unlike_votes = []
like_votes = []
current_status = {'satisfaction' : 0.5, 'song': '', 'last_song':'', 'listeners': 0}

LISTENERS_IDX = 14
PLAYING_IDX = 16

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='/tmp/logs/ices.log',
                    filemode='a')

LOGGER = logging.getLogger('radio-ices')


@app.route('/busca_resultados', methods=["POST"])
def busca_resultados():
    vote = request.form["vote"]
    session['vote'] = vote
    params = urllib.urlencode({'q': vote.encode('utf-8'), 'max-results': '10', 'v': '2', 'alt': 'jsonc'})
    url = "http://gdata.youtube.com/feeds/api/videos?%s" % params
    result = simplejson.load(urllib.urlopen(url))
    return simplejson.dumps(result)

@app.route('/perform_vote', methods= ["POST"]) 
def perform_vote():
    index = request.json["index"]
    params = urllib.urlencode({'q': session['vote'].encode('utf-8'), 'max-results': '10', 'v': '2', 'alt': 'jsonc'})
    url = "http://gdata.youtube.com/feeds/api/videos?%s" % params
    result = simplejson.load(urllib.urlopen(url))
    item = result['data']['items'][int(index)]
    video_json = simplejson.dumps({"id": item['id'], "title": item['title']})
    radio_utils.append(radio_utils.get_path(RADIO_ROOT, 'to_process_votes'), 
                          video_json)
    return simplejson.dumps(current_status)

@app.route('/vote_song', methods= ["POST"]) 
def vote_song():
    active_songs = get_applicant_songs()
    index = int(request.json["vote_index"])
    vote_type = request.json["vote_type"]
    applicant = active_songs[int(index)]
    if vote_type == "up":
        active_songs[index].up_votes += 1
    else:
        active_songs[index].down_votes += 1
    active_songs[index].balance = active_songs[index].up_votes - active_songs[index].down_votes
    active_songs.sort(key=lambda Song: Song.balance, reverse=True)
    update_file(active_songs)
    return simplejson.dumps("")

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
    active_songs = get_applicant_songs()
    active_songs.sort(key=lambda Song: Song.balance, reverse=True)
    update_file(active_songs)
    if (current_status['song'] != current_status['last_song']):
        current_status['last_song'] = current_status['song']
    token = request.cookies.get('token')
    return simplejson.dumps({"vote": get_vote(token), "current_song": current_status['song'], 
                             "satisfaction": current_status['satisfaction'], "applicant_songs": get_applicant_titles()})

@app.route('/like')
def like():
    token = request.cookies.get('token')
    
    if (not token in like_votes) :
        like_votes.append(token)
        update_satisfaction()
        
    return simplejson.dumps(current_status)

@app.route('/unlike')
def unlike():
    token = request.cookies.get('token')
    
    if (not token in unlike_votes) :
        unlike_votes.append(token)
        update_satisfaction()
        
    return simplejson.dumps(current_status)

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
    current_status['satisfaction'] = 0.5
    update_status()
    
def ice_status():
        status_xml = urllib.urlopen(STATUS_PAGE).read()
        xml_doc = minidom.parseString(status_xml)
        pre = xml_doc.getElementsByTagName('pre')[0]
        status_text = pre.firstChild.nodeValue
        status_list = status_text.split(',')
        
        return status_list

def ice_listeners():
    ice_listeners = []
    request = urllib2.Request("http://vermelho:8000/admin/listclients?mount=/ices")
    base64string = base64.encodestring('%s:%s' % ("admin", "hackmein")).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)
    status_xml = urllib2.urlopen(request).read()
    xml_doc = minidom.parseString(status_xml)
    stats = xml_doc.getElementsByTagName('icestats')[0]
    source = stats.getElementsByTagName('source')[0]
    listeners = source.getElementsByTagName('listener')

    for listener in listeners:
        LOGGER.info(listener.nodeValue)
        ice_listeners.append(listener.getElementsByTagName('ID')[0].firstChild.nodeValue)

    return ice_listeners

def update_status():    
    status_list = ice_status()
    if (len(status_list) <= PLAYING_IDX + 1):
        current_status['song'] = 'Sem musicas pra tocar'
        current_status['listeners'] = 1
        return

    LOGGER.info(status_list)
    current_song = open("current_song","r")
    current_status['song'] = current_song.read()
    current_song.close()
    current_status['listeners'] = int(status_list[LISTENERS_IDX])

def get_applicant_songs():
    songs = open(radio_utils.get_path(RADIO_ROOT, 'processed_votes'), "r")
    applicants = []
    for song in songs.readlines():
        unpickled = jsonpickle.decode(song)
        song = Song(unpickled["id"], unpickled["title"])
        song.up_votes = unpickled["up_votes"]
        song.down_votes = unpickled["down_votes"]
        song.balance = song.up_votes - song.down_votes
        song.path = unpickled["path"]
        applicants.append(song)
    songs.close()
    return applicants

def get_applicant_titles():
    list = []
    for applicant in get_applicant_songs():
        list.append(applicant.title)
    return list

def update_file(active_songs):
    songs = open(radio_utils.get_path(RADIO_ROOT, 'processed_votes'), "w")
    for song in active_songs:
        songs.write(jsonpickle.encode(song) + "\n")
    songs.close()

def check_newsong():    
    while (True):
        f = open(ICES_PIPE, 'r')
        f.read()
        f.close()
        
        time.sleep(2)
        update_song()

if __name__ == '__main__':   
    th=Thread(target=check_newsong)
    th.start()
    update_status()
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
    app.config["SECRET_KEY"] = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(host='0.0.0.0')
