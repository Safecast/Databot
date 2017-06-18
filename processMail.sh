#!/bin/bash
export PATH="/root/miniconda2/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/usr/local/go/bin"

cd /home/rob/Databot 
python process_email.py >> /var/www/databot/$(date +"%Y%m%d")_databot.txt 2>&1
mkdir -p archives
mv ./logs/* ./archives/. > /dev/null 2>&1
rm -rf ./archives/*.kml > /dev/null 2>&1
