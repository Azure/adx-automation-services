#!/usr/bin/env bash

# Run the job cleaner script locally for testing

export A01_INTERNAL_COMKEY=`kubectl get secret store-secrets --template '{{ .data.comkey }}' | base64 -D`
export A01_STORE_NAME='https://secondapi.azclitest.com'

root=`cd $(dirname $0); cd ..; pwd`
python $root/app/jobcleaner.py