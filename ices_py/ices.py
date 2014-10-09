import os
import vote_queue, scratch_queue
import time
import logging
import radio_utils
from radio_config import RADIO_ROOT, MP3CACHE_ROOT, ICES_MODULE_ROOT
from radio_config import ICES_PIPE
from ices_logger import LOGGER
import jsonpickle

def real_path(path):
    return radio_utils.get_path(RADIO_ROOT, path)

def ices_get_next():
    while (True) :
        pipe = open(ICES_PIPE, 'w')
        pipe.write('1')
        pipe.close()
        json_obj = radio_utils.poll(real_path('processed_votes'))
        LOGGER.info(json_obj)
        if json_obj:
            obj = jsonpickle.decode(json_obj)
            current_song = open("current_song", "w")
            current_song.write('{"song":"%s", "author":"%s"}' % (obj["title"].encode("UTF-8"),obj["user"].encode("UTF-8")))
            current_song.close()
            return obj["path"]
        time.sleep(2)