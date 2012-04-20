#!/usr/bin

if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

PWD=`dirname $0`
python server/server.py &
echo $! > $PWD/server.pid