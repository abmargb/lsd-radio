import os
import sys
import random

from radio_config import SCRATCH_ROOT

def random_track(top_dir):

    def random_album(top_dir):
        (dirpath, dirnames, filenames) = os.walk(top_dir).next()
        while True:
            album = random.choice(dirnames)
            if tracks_in_dir(os.path.join(dirpath, album)):
               return os.path.join(dirpath, album)
        raise Exception("Mp3 files not found")

    def tracks_in_dir(_dir):
       all_tracks = []
       for (dirpath, dirnames, filenames) in os.walk(_dir):
           all_tracks.extend(tracks(filenames))
       return all_tracks

    def tracks(filenames):
        return [_file for _file in filenames if _file.endswith("mp3")]

    all_tracks = []
    for (dirpath, dirnames, filenames) in os.walk(random_album(top_dir)):
        all_tracks.extend([os.path.join(dirpath, track) for track in tracks(filenames)])
    return random.choice(all_tracks)


def get_next():
    try:
        return random_track(SCRATCH_ROOT)
    except: 
        return None