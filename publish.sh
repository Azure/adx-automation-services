#!/usr/bin/env bash

set -e

registry=azureclidev
server=$registry.azurecr.io
version=$(cat ./version)
image=$server/a01store:$version

count=$(az acr repository show-tags -n $registry --repository a01store -otsv | grep $version -c)
if [ "$count" != "0" ]; then
    echo The tag $version already exist for image a01store on $server
    exit 1
fi

docker build -t $image .
docker push $image

image_latest=$server/a01store:latest 
docker tag $image $image_latest
docker push $image_latest
docker rmi $image_latest
