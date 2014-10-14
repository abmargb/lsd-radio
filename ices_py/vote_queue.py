from threading import Thread
import os
import radio_utils
import logging
from radio_config import RADIO_ROOT, ICES_MODULE_ROOT
from pprint import pprint
from ices_logger import LOGGER

PROCESSING_BUFFER_SIZE = 5

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='/tmp/logs/ices.log',
                    filemode='a')

logger = logging.getLogger('radio-ices')

def real_path(path):
    return radio_utils.get_path(RADIO_ROOT, path)

def process(videos_no):
    os.system("python %s/process_vote_queue.py %s &" % (ICES_MODULE_ROOT, videos_no))

def get_next():
    file_path = radio_utils.poll(real_path('processed_votes'))

    lines_processed = radio_utils.lines(real_path('processed_votes'))
    lines_processing = radio_utils.lines(real_path('processing_votes'))

    to_process = 1
    process(to_process)

    return file_path
