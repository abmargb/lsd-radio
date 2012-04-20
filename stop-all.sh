#!/usr/bin

cd `dirname $0`
sudo /etc/init.d/icecast2 stop
sudo bash stop-ices.sh
sudo bash stop-server.sh
