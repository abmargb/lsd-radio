#!/usr/bin/python
# -*- coding: UTF-8 -*-

from radio_config import RADIO_ROOT, MP3CACHE_ROOT, ICES_MODULE_ROOT
from mutagen.id3 import ID3, TIT2
import radio_utils
import os
import sys
import json
from song import Song
import jsonpickle

class Tree(object):
    def __init__(self, name, childTrees=None):
        self.name = name
        if childTrees is None:
            childTrees = []
        self.childTrees = childTrees

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, Tree):
            return super(MyEncoder, self).default(obj)

        return obj.__dict__

FFMPEG_LINE = 'youtube-dl http://www.youtube.com/watch?v=%s -q -o /dev/stdout | ffmpeg -i pipe: -acodec libmp3lame -vn -ab 128000 -ar 44100 %s/"%s".mp3'

def real_path(path):
    return radio_utils.get_path(RADIO_ROOT, path)

def convert_video(vote_id, vote_name, vote_user):
	print "FFMPEG Conversion: %s" % (FFMPEG_LINE % (vote_id, MP3CACHE_ROOT, vote_id))
	os.system(FFMPEG_LINE % (vote_id, MP3CACHE_ROOT, vote_id))
	song = Song(vote_id, vote_name, vote_user)
	song.path = os.path.join(MP3CACHE_ROOT, "%s.mp3" % (vote_id))
	unpickled = jsonpickle.encode(song)
	radio_utils.append(real_path('processed_votes'), unpickled)


vote_id = sys.argv[1]
vote_name = sys.argv[2]
vote_user = sys.argv[3]
convert_video(vote_id, vote_name, vote_user)