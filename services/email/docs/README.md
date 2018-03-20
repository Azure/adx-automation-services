# Email Service

The email service is a microserivce designed to run in a Kuberntes cluster. It operates as a web service accepting email requests from other components of the A01 system.

## Usage

To requests an email, POST a request to `/report` with following JSON body:

```json
{
    "run_id": 428,
    "receivers": "user@example.com",
    "template": "https://example.blob.core.windows.net/templates/example.html"
}
```

The property `template` is optional. If missing the service will use a default generic template to render reporting email. If given the uri must points a [Jinja2 Tempalte](http://jinja.pocoo.org/docs/2.10/templates/). To the template `run` and `tasks` instances are passed in.

Here are two examples:
- [Azure CLI](templates/azurecli.html)
- [Go SDK](templates/gosdk.html)

## Deployment

- Build the service to a docker image with the [Dockerfile](../Dockerfile).
- Deploy the service using the [Kubernetes definition](../../../deployment/def/deployment.yml)
