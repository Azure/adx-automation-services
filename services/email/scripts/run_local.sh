#!/usr/bin/env bash

root=`cd $(dirname $0); cd ..; pwd`

export A01_INTERNAL_COMKEY=`kubectl get secret store-secrets --template '{{ .data.comkey }}' | base64 -D`
export A01_STORE_NAME='https://secondapi.azclitest.com'

export A01_REPORT_SMTP_SERVER=`kubectl get secret email --template '{{ .data.server }}' | base64 -D`
export A01_REPORT_SENDER_ADDRESS=`kubectl get secret email --template '{{ .data.username }}' | base64 -D`
export A01_REPORT_SENDER_PASSWORD=`kubectl get secret email --template '{{ .data.password }}' | base64 -D`

export FLASK_APP=$root/app/app/main.py
export FLASK_DEBUG=1

flask run