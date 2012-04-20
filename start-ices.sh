#!/usr/bin

if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

PWD=`dirname $0`
ices -c /usr/local/etc/ices.conf.dist &
echo $! > $PWD/ices.pid
