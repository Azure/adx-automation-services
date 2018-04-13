#!/usr/bin/env bash

root=`cd $(dirname $0); cd ..; pwd`

export A01_DATABASE_URI=`kubectl get secret store-secrets --template '{{ .data.dburi }}' | base64 -D`
export FLASK_APP=$root/app/app/main.py
export FLASK_DEBUG=1

flask run
