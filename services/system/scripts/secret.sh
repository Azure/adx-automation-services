#!/bin/bash

# Create a kubernetes secret definition for store service

namespace=$1
if [ -z $namespace ]; then
    echo "Usage: secret.sh NAMESPACE"
    echo "A namespace is required." >&2
    exit 1
fi

db_connect_str=`az keyvault secret show -n a01taskstore-db-connect-str --vault-name a01secret --query value -otsv | base64`
internal_comkey=`LC_CTYPE=C tr -dc A-Za-z0-9 < /dev/urandom | head -c 64 | base64`

echo "apiVersion: v1
kind: Secret
metadata:
  name: store-secrets
  namespace: $namespace
data:
  dburi: $db_connect_str
  comkey: $internal_comkey
" | kubectl apply -f -

baseacr='adxautomationbase'
baseacr_server=$(az acr show -n $baseacr --query loginServer --output tsv)
baseacr_id=$(az acr show -n $baseacr --query id --output tsv)
sp_username=`az ad sp show --id http://$baseacr-reader --query appId -otsv`
sp_password=`az ad sp reset-credentials -n http://$baseacr-reader --query password -otsv`

kubectl delete secret docker-registry $baseacr-registry \
    --namespace $namespace \
    --ignore-not-found

kubectl create secret docker-registry $baseacr-registry \
    --docker-server $baseacr_server \
    --docker-username $sp_username \
    --docker-password $sp_password \
    --docker-email adxsdk@microsofot.com \
    --namespace $namespace