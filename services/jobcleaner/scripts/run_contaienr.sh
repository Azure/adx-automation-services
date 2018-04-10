#!/usr/bin/env bash

# Run the job cleaner script locally for testing in a container

root=`cd $(dirname $0); cd ..; pwd`

version=`cat $root/version`
svc_name=`basename $root`

image_name="$svc_name:$version-local"
docker build -t $image_name $root

docker run --rm \
           --env A01_INTERNAL_COMKEY=`kubectl get secret store-secrets --template '{{ .data.comkey }}' | base64 -D` \
           --env A01_STORE_NAME='https://secondapi.azclitest.com' \
           $image_name
