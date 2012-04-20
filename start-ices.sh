#!/usr/bin

PWD=`dirname $0`
sudo ices -c /usr/local/etc/ices.conf.dist &
echo $! > $PWD/ices.pid
