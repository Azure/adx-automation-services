#!/usr/bin/env bash

if [ -z $1 ]; then
    echo "Usage: $(basename $0) CONTAINER_REGISTRY" >&2
    exit 1
fi

root=`cd $(dirname $0); cd ..; pwd`

version=`cat $root/version`
svc_name=`basename $root`

container_reg=$1
image_name="$container_reg.azurecr.io/$svc_name:$version"

az acr login -n $container_reg
docker build -t $image_name $root
docker push $image_name


echo "apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: jobcleaner
  labels:
    group: base
    system: a01
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - env:
            - name: A01_STORE_NAME
              value: store-internal-svc
            - name: A01_INTERNAL_COMKEY
              valueFrom:
                secretKeyRef:
                  key: comkey
                  name: store-secrets
            image: $image_name
            name: main
          imagePullSecrets:
          - name: $container_reg-registry
          restartPolicy: Never
  schedule: \"* 20 * * *\"
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 1
" | kubectl apply -f -