#!/usr/bin

cd `dirname $0`
sudo /etc/init.d/icecast2 start
sudo nohup bash start-ices.sh
sudo nohup bash start-server.sh
