import os
import vote_queue, scratch_queue

def ices_get_next():
    
    file_path = vote_queue.get_next()
    if (not file_path) :
        file_path = scratch_queue.get_next()
    
    return file_path