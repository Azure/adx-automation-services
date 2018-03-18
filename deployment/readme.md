# Deployment steps

## Instal helm

Reference: https://docs.microsoft.com/en-us/azure/aks/kubernetes-helm

## Install Ngnix Ingress Controller

``` bash
helm install stable/ngnix-ingress
```

## Deploy Kube-LEGO

``` bash
helm install stable/kube-lego \
    --set config.LEGO_EMAIL=<email> \
    --set config.LEGO_URL=https://acme-v01.api.letsencrypt.org/directory`
```

## Create namespace

``` bash
kubectl create namespace <namespace>
```

## Reset basic secrets and configuration

``` bash
./deployment/scripts/secret.sh <namespace>

kubectl apply -f deployment/def/config.yml --namespace <namespace>
```

### Deploy Taskbroker

``` bash
./deployment/scripts/deploy-taskbroker-rabbitmq.sh <namespace>
```

Reference: https://github.com/kubernetes/charts/tree/master/stable/rabbitmq

### Deploy Ingress

``` bash
kubectl apply -f deployment/def/ingress.yml --namespace <namespace>
```

Afterwards:
- Wait till the public IP is created.
- Update the DNS record to bind a domain name to the IP at https://prod.msftdomains.com/

### Deploy other services

``` bash
kubectl apply -f deployment/def/deployment.yml --namespace <namespace>
```
