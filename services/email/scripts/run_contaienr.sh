#!/usr/bin/env bash

root=`cd $(dirname $0); cd ..; pwd`

version=`cat $root/version`
svc_name=`basename $root`

image_name="$svc_name:$version-local"
docker build -t $image_name $root

docker run --rm -it -p 8080:80 \
           --env A01_INTERNAL_COMKEY=`kubectl get secret store-secrets --template '{{ .data.comkey }}' | base64 -D` \
           --env A01_STORE_NAME='https://secondapi.azclitest.com' \
           --env A01_REPORT_SMTP_SERVER=`kubectl get secret email --template '{{ .data.server }}' | base64 -D` \
           --env A01_REPORT_SENDER_ADDRESS=`kubectl get secret email --template '{{ .data.username }}' | base64 -D` \
           --env A01_REPORT_SENDER_PASSWORD=`kubectl get secret email --template '{{ .data.password }}' | base64 -D` \
           $image_name
