from threading import Thread
import os
import utils
from config import RADIO_ROOT, ICES_MODULE_ROOT

PROCESSING_BUFFER_SIZE = 5

def real_path(path):
    return utils.get_path(RADIO_ROOT, path)

def process(videos_no):
    os.system("python %s/process_vote_queue.py %s &" % (ICES_MODULE_ROOT, videos_no))    

def get_next():
    
    file_path = utils.poll(real_path('processed_votes'))
    
    lines_processed = utils.lines(real_path('processed_votes'))
    lines_processing = utils.lines(real_path('processing_votes'))
    
    to_process = PROCESSING_BUFFER_SIZE - lines_processed - lines_processing
    process(to_process)
    
    return file_path
