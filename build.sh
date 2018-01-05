#!/usr/bin/env bash

registry=azureclidev
server=`az acr show -n $registry --query 'loginServer' -otsv`
version=$(cat ./version)
image=$server/a01store:$version


az acr login -n $registry
docker build -t $image .
docker push $image

