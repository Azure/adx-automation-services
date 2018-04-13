# Manadatory Micro-Service Structure

## Programming Language

A service can be implemented in either Python 3.6 or Go.

## Folder structure

```
$project_root/
    services/
        store/              <- Indivicual service
            app/            <- Source code (optional)
            docs/           <- Individual service documentation
            scripts/        <- Deployment scripts
            .dockerignore
            Dockerfile
            version
        email/
        ...
    scripts/            <- DO NOT put scripts related to individual service here
    docs/               <- Documents
    deployments/        <- Obsoleted. Will be removed soon.
```

## Files

Under the service folder, following files are expected.

### Required

- `scripts/deploy.sh`: executed while a deployment is triggered. The script should build the docker image, push it to the given
               registery, and apply changes to the Kubernetes cluster. The script should accept one parameter for the
               name of the Azure Container Registry.
- `version`: a file with the current service version.