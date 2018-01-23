#!/usr/bin/env bash

set -e

registry=azureclidev
server=$registry.azurecr.io
version=$(cat ./version)
image=$server/a01store:$version

docker pull $image >/dev/null 2>&1 && (echo The tag $version already exist for image a01store on $server >&2; exit 1)

docker build -t $image .
docker push $image

image_latest=$server/a01store:latest 
docker tag $image $image_latest
docker push $image_latest
docker rmi $image_latest
