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
  name: store-deployment
  labels:
    system: a01
    group: base
spec:
  replicas: 2
  template:
    metadata:
      labels:
        app: store
    spec:
      containers:
      - name: store-flask-svc
        image: $image_name
        ports:
        - containerPort: 80
        env:
        - name: A01_DATABASE_URI
          valueFrom:
            secretKeyRef:
              name: store-secrets
              key: dburi
        - name: A01_INTERNAL_COMKEY
          valueFrom:
            secretKeyRef:
              name: store-secrets
              key: comkey
      imagePullSecrets:
      - name: $container_reg-registry
---
apiVersion: v1
kind: Service
metadata:
  name: store-internal-svc
  labels:
    system: a01
    group: base
spec:
  ports:
  - port: 80
  selector:
    app: store
" | kubectl apply -f -