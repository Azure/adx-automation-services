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


echo "apiVersion: apps/v1beta1
kind: Deployment
metadata:
  name: email-deployment
  labels:
    system: a01
    group: base
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: email
    spec:
      containers:
      - name: email-flask-svc
        image: $image_name
        ports:
        - containerPort: 80
        env:
        - name: A01_STORE_NAME
          value: store-internal-svc
        - name: A01_INTERNAL_COMKEY
          valueFrom:
            secretKeyRef:
              name: store-secrets
              key: comkey
        - name: A01_REPORT_SMTP_SERVER
          valueFrom:
            secretKeyRef:
              name: email
              key: server
        - name: A01_REPORT_SENDER_ADDRESS
          valueFrom:
            secretKeyRef:
              name: email
              key: username
        - name: A01_REPORT_SENDER_PASSWORD
          valueFrom:
            secretKeyRef:
              name: email
              key: password
      imagePullSecrets:
      - name: $container_reg-registry
---
apiVersion: v1
kind: Service
metadata:
  name: email-internal-svc
  labels:
    system: a01
    group: base
spec:
  ports:
  - port: 80
  selector:
    app: email" | kubectl apply -f -