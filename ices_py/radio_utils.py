import os

def poll(file_name):
    
    output = []
    file_path = None
    
    f = open(file_name, 'r')
    first = True
    
    for line in f:
        if first :
            file_path = line.strip()
            first = False
        else :
            output.append(line)
    f.close()
    
    f = open(file_name, 'w')
    f.writelines(output)
    f.close()
    
    return file_path
    
def lines(file_name):
    f = open(file_name, 'r')
    lines = 0
    for line in f:
        lines += 1
    f.close()
    
    return lines
    
def append(file_path, line):
    f = open(file_path, "a")
    f.write("%s\n" % line.strip())
    f.close()

def get_path(root, path):
    return os.path.join(root, path)