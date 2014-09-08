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
import time
from datetime import datetime

from song import Song
from radio_config import RADIO_ROOT, SERVER_URL, ICES_PID, STATUS_PAGE, ICES_PIPE
from xml.dom import minidom
from logger import setup_logger

app = Flask(__name__)

unlike_votes = []
like_votes = []
current_status = {'satisfaction' : 0.5, 'song': '', 'last_song':'', 'listeners': 0, "positive_votes":0, "negative_votes":0}

LISTENERS_IDX = 14
PLAYING_IDX = 16

setup_logger('feedback-logger', 'logs/feedback.log')
setup_logger('vote-logger', 'logs/vote.log')
setup_logger('interpose-logger', 'logs/interpose.log')
setup_logger('suggestion-logger', 'logs/suggestion.log')
setup_logger('satisfaction-logger', 'logs/satisfaction.log')

FEEDBACK_LOGGER = logging.getLogger('feedback-logger')
VOTE_LOGGER = logging.getLogger('vote-logger')
INTERPOSE_LOGGER = logging.getLogger('interpose-logger')
SUGGESTION_LOGGER = logging.getLogger('suggestion-logger')
SATISFACTION_LOGGER = logging.getLogger('satisfaction-logger')

def get_online_users():
    current = int(time.time()) // 60
    minutes = xrange(5)
    redis = Redis()
    return redis.sunion(['online-users/%d' % (current - x)
                         for x in minutes])

@app.route('/define_name', methods=["POST"])
def define_name():
    update_user_file(request.remote_addr,request.json["username"])
    return simplejson.dumps("")

def update_user_file(addr, username):
    users_file = open("users","r")
    users = users_file.readlines()
    new_users = []
    updated = False
    for entry in users:
        if len(entry) > 1:
            if entry.split(" ")[0] == addr:
                updated = True
                new_users.append("%s %s" % (addr,username))
            else:
                new_users.append(entry)
    if not updated:
        new_users.append("%s %s" % (addr, username))

    users_file.close()
    users_file = open("users","w")
    for user in new_users:
        users_file.write(user + "\n")
    users_file.close()

def normalize_users_file():
    pings = [ping.rstrip() for ping in open("ping","r").readlines()]
    old_users = open("users","r").readlines()

    updated_users = []

    for user in old_users:
        if len(user) > 1 and user.split(" ")[0] in pings:
            updated_users.append(user)

    new_users = open("users","w")
    for user in updated_users:
        new_users.write(user)
    new_users.close()

@app.route('/busca_resultados', methods=["POST"])
def busca_resultados():
    vote = request.form["vote"]
    session['vote'] = vote
    params = urllib.urlencode({'q': vote.encode('utf-8'), 'max-results': '30', 'v': '2', 'alt': 'jsonc',"orderby":"viewCount"})
    url = "http://gdata.youtube.com/feeds/api/videos?%s" % params
    global current_results
    current_results = simplejson.load(urllib.urlopen(url))
    for song in current_results["data"]["items"]:
        if int(song["duration"]) > 480:
            current_results["data"]["items"].remove(song)

    return simplejson.dumps(current_results)

@app.route('/perform_vote', methods= ["POST"])
def perform_vote():
    # Quem sugeriu, o que sugeriu, quando sugeriu
    index = request.json["index"]
    item = current_results['data']['items'][int(index)]
    video_json = simplejson.dumps({"id": item['id'], "title": item['title']})
    radio_utils.append(radio_utils.get_path(RADIO_ROOT, 'to_process_votes'),
                          video_json)
    SUGGESTION_LOGGER.info("%s | %s" % (get_user(request).rstrip(), item['title'].rstrip()))
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
    VOTE_LOGGER.info("%s | %s" % (get_user(request).rstrip(), vote_type.rstrip()))
    return simplejson.dumps({"applicant_songs": get_applicant_titles()})

@app.route('/feedback', methods= ["POST"])
def feedback():
    feedback_type = request.json["feedback_type"]
    if feedback_type == "woot":
        current_status["positive_votes"] += 1
    else:
        current_status["negative_votes"] += 1
    # Quem deu feedback, como deu, quando deu
    FEEDBACK_LOGGER.info("%s | %s" % (get_user(request).rstrip(), feedback_type.rstrip()))

    update_satisfaction()
    return simplejson.dumps(current_status)

@app.route('/satisfaction', methods= ["POST"])
def satisfaction():
    satisfaction = request.json["satisfaction"]
    SATISFACTION_LOGGER.info("%s | %s" % (get_user(request).rstrip(), satisfaction))
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

    satisfaction = float(current_status["positive_votes"] - current_status["negative_votes"]) / float(max(len(get_online_users()),1))
    satisfaction = (satisfaction + 1) / 2

    if (satisfaction < 0.25):
        # Quem foi vetado, Quando foi vetado (Extrair quantas vezes foi vetado)
        skip_song()

@app.route('/status')
def status():
    update_ping_file(request.remote_addr)
    active_songs = get_applicant_songs()
    active_songs.sort(key=lambda Song: Song.balance, reverse=True)
    update_file(active_songs)
    if (current_status['song'] != current_status['last_song']):
        current_status['last_song'] = current_status['song']
        current_status["positive_votes"] = 0
        current_status["negative_votes"] = 0
        changed_song_this_round = True
    else:
        changed_song_this_round = False
    token = request.cookies.get('token')
    return simplejson.dumps({"vote": get_vote(token), "current_song": current_status['song'],
                             "satisfaction": current_status['satisfaction'], "applicant_songs": get_applicant_titles(), "online_users": get_online_users(),
                             "positive_votes": current_status["positive_votes"], "negative_votes": current_status["negative_votes"],
                             "changed_song_this_round":changed_song_this_round})

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

def update_status():
    status_list = ice_status()
    if (len(status_list) <= PLAYING_IDX + 1):
        current_status['song'] = 'Sem musicas pra tocar'
        current_status['listeners'] = 1
        return

    current_song = open("current_song","r")
    current_status['song'] = current_song.read()
    current_song.close()
    current_status['listeners'] = int(status_list[LISTENERS_IDX])

def update_ping_file(address):
    users_file = open("ping","a")
    users_file.write("%s\n" % (address))
    users_file.close()

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

def get_online_users():
    users_file = open("users","r")
    users = []
    for user in users_file.readlines():
        if len(user) > 1:
            users.append(user.split(" ")[1])
    return users

def get_user(request):
    ip = request.remote_addr
    users_file = open("users","r")
    for user in users_file.readlines():
        if len(user) > 0 and user.split(" ")[0] == ip:
            return user.split(" ")[1]
    users_file.close()
    return None

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

def reset_ping_file():
    while (True):
        normalize_users_file()
        users_file = open("ping","w").close()
        time.sleep(30)

if __name__ == '__main__':
    th=Thread(target=check_newsong)
    th.start()
    update_status()

    th2=Thread(target=reset_ping_file)
    th2.start()

    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
    app.config["SECRET_KEY"] = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(host='0.0.0.0')
