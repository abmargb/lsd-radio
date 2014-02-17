#!/usr/bin
# Instalador da Radio LSD

if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

cd `dirname $0`
radio_root=`pwd`
hostname=`hostname`

sed -i "s,%RADIO_ROOT%,$radio_root,g" radio_config.py
sed -i "s,%HOSTNAME%,$hostname,g" radio_config.py

pkg_dir=`python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())"`
sed -i "s,%RADIO_ROOT%,$radio_root,g" resources/radio_modules.pth
cp resources/radio_modules.pth $pkg_dir/radio_modules.pth

mkfifo ices_pipe
touch processed_votes processing_votes to_process_votes current_song
mkdir cache

# Instalando o Flask

apt-get -y install python-setuptools
easy_install Flask
easy_install mutagen

# Instalando o ffmpeg e o lame

apt-get -y install ffmpeg
apt-get -y install lame
apt-get -y install ffmpeg libavcodec-extra-52 libavcodec-extra-53

# Instalando o icecast2 e o ices

apt-get -y install icecast2
apt-get -y install libshout3-dev
apt-get -y install libxml2-dev
apt-get -y install libmp3lame-dev
apt-get -y install python-dev
wget http://downloads.us.xiph.org/releases/ices/ices-0.4.tar.gz
tar -xvf ices-0.4.tar.gz
cd ices-0.4
./configure
make
make install
cd ..

# Copiando extensao python e arquivos de configuracao

cp ices_py/* /usr/local/etc/modules/
cp conf/ices.conf.dist /usr/local/etc/
cp conf/icecast.xml /etc/icecast2/
