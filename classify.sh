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
sudo systemctl start leroy.service
