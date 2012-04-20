#!/usr/bin

PWD=`dirname $0`
sudo python server/server.py &
echo $! > $PWD/server.pid