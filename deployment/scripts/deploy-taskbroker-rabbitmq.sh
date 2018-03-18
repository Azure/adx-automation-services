#!/usr/bin/env bash

namespace=$1
if [ -z $namespace ]; then
    echo "Namespace is requred." >&2
    echo "Usage: $(basename $0) NAMESPACE" >&2
    exit 1
fi

root=`cd $(dirname $0); cd ../../;pwd`
helm install --name taskbroker \
             --namespace $namespace \
             -f $root/deployment/def/helm-rabbitmq-taskbroker.yml \
             stable/rabbitmq