#!/usr/bin

PWD=`dirname $0`
pid=`cat "$PWD"/server.pid`
kill -KILL $pid