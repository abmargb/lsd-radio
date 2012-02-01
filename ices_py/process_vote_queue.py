import utils
import os
from config import RADIO_ROOT, MP3CACHE_ROOT, ICES_MODULE_ROOT
import sys

FFMPEG_LINE = "python %s/youtube-dl http://www.youtube.com/watch?v=%s -q -o /dev/stdout | ffmpeg -i pipe: -acodec libmp3lame -vn -ab 128000 -ar 44100 %s/%s.mp3"

def real_path(path):
    return utils.get_path(RADIO_ROOT, path)

def process_audio(vote_id):
    utils.append(real_path('processing_votes'), vote_id)
    os.system(FFMPEG_LINE % (ICES_MODULE_ROOT, vote_id, MP3CACHE_ROOT, vote_id))
    vote_id = utils.poll(real_path('processing_votes'))
    utils.append(real_path('processed_votes'), 
                 os.path.join(MP3CACHE_ROOT, "%s.mp3" % vote_id))

if __name__ == "__main__":
    
    to_process = int(sys.argv[1])
    for i in range(0, to_process) :
        vote_id = utils.poll(real_path('to_process_votes'))
        if (vote_id) :
            process_audio(FFMPEG_LINE, vote_id, utils, real_path)