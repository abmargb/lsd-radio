import radio_utils
import os
from radio_config import RADIO_ROOT, MP3CACHE_ROOT, ICES_MODULE_ROOT
import sys
import simplejson
from mutagen.id3 import ID3, TIT2
from ices_logger import LOGGER

FFMPEG_LINE = "youtube-dl http://www.youtube.com/watch?v=%s -q -o /dev/stdout | ffmpeg -i pipe: -acodec libmp3lame -vn -ab 128000 -ar 44100 %s/%s.mp3"

def real_path(path):
    return radio_utils.get_path(RADIO_ROOT, path)

def process_audio(vote_json_str):
    LOGGER.info("Processamento!")
    vote_json = simplejson.loads(vote_json_str.split("|")[0])
    vote_id = vote_json['id']
    
    radio_utils.append(real_path('processing_votes'), vote_json_str)

    LOGGER.info("FFMPEG Conversion: %s" % (FFMPEG_LINE % (vote_id, MP3CACHE_ROOT, vote_id)))
    os.system(FFMPEG_LINE % (vote_id, MP3CACHE_ROOT, vote_id))
    
    audio = ID3("%s/%s.mp3" % (MP3CACHE_ROOT, vote_id))
    audio.add(TIT2(encoding=3, text=vote_json['title']))
    audio.save()
    
    vote_json_polled = radio_utils.poll(real_path('processing_votes'))
    
    if (vote_json_polled != vote_json_str) :
        print "There is a concurrency error."
    
    LOGGER.info("End of Process for %s" % (vote_json['title']))
    radio_utils.append(real_path('processed_votes'), 
                 os.path.join(MP3CACHE_ROOT, "%s.mp3" % vote_id))

if __name__ == "__main__":
    vote_json_str = radio_utils.poll(real_path('to_process_votes'))
    if (vote_json_str) :
        process_audio(vote_json_str)
    #to_process = int(sys.argv[1])
    #for i in range(0, to_process) :
        #vote_json_str = radio_utils.poll(real_path('to_process_votes'))
        #if (vote_json_str) :
            #process_audio(vote_json_str)