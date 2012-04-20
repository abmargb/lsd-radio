#!/usr/bin

PWD=`dirname $0`
pid=`cat "$PWD"/ices.pid`
kill -KILL $pid