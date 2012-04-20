#!/usr/bin

if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

cd `dirname $0`
/etc/init.d/icecast2 start
nohup bash start-ices.sh
nohup bash start-server.sh
