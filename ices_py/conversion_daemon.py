#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import os
import radio_utils
import simplejson
from radio_config import RADIO_ROOT, MP3CACHE_ROOT, ICES_MODULE_ROOT

def real_path(path):
    return radio_utils.get_path(RADIO_ROOT, path)

while True:
	print "Buscando arquivo para conversao"
	vote_json_str = radio_utils.poll(real_path('to_process_votes'))
	if vote_json_str:
		print 'python %s/conversion_script.py %s "%s" %s &' % (ICES_MODULE_ROOT, simplejson.loads(vote_json_str)["id"], simplejson.loads(vote_json_str)["title"].encode("UTF-8"),simplejson.loads(vote_json_str)["user"].encode("UTF-8"))
		os.system('python %s/conversion_script.py %s "%s" %s &' % (ICES_MODULE_ROOT, simplejson.loads(vote_json_str)["id"], simplejson.loads(vote_json_str)["title"].encode("UTF-8"),simplejson.loads(vote_json_str)["user"].encode("UTF-8")))
	time.sleep(5)