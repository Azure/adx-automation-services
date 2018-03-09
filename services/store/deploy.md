# Deployment steps

- Install helm
- Run `helm install stable/ngnix-ingress`
- Wait till the public IP is created, ensure the nameserver is set up correctly.
- Deploy kube-lego `helm install stable/kube-lego --set config.LEGO_EMAIL=<email> --set config.LEGO_URL=https://acme-v01.api.letsencrypt.org/directory`
- Run `secret.sh`. The script will reset passwords.
- Run `kubectl apply -f def/deployment.yml`
- Run `kubectl apply -f def/ingress.yml`
