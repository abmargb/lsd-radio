#!/usr/bin

if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

PWD=`dirname $0`
pid=`cat "$PWD"/server.pid`
kill -KILL $pid