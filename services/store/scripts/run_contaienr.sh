#!/usr/bin/env bash

# Run the job cleaner script locally for testing in a container

root=`cd $(dirname $0); cd ..; pwd`

version=`cat $root/version`
svc_name=`basename $root`

image_name="$svc_name:$version-local"
docker build -t $image_name $root

docker run --rm -it -p 8080:80 \
           --env A01_INTERNAL_COMKEY=`kubectl get secret store-secrets --template '{{ .data.comkey }}' | base64 -D` \
           --env A01_DATABASE_URI=`kubectl get secret store-secrets --template '{{ .data.dburi }}' | base64 -D` \
           $image_name
