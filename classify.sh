#!/bin/bash
sudo systemctl stop leroy.service
sleep 1
python3 classify.py --dir=storage/detected
sleep 1
#if aws --profile project-leroy s3 cp storage s3://birds91149-dev --recursive  --acl bucket-owner-full-control --exclude "detected/*" ; then
    #rm -rf storage/detected
    #rm -rf storage/classified
    #rm -rf storage/video
#fi

DATE=$(date +'%Y-%m-%d')
make generate_daily_report DATE=$DATE
mv visitations.json /var/www/html/visitations.json
cp -a /web/. /var/www/html/

sudo systemctl start leroy.service