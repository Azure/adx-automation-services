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

The property `template` is optional. If given the URI must points to a template resource for rendering report.

## Template

This service renders the report email using a [Jinja2](http://jinja.pocoo.org/docs/2.10/templates/) template. By default, a generic template is used. However, if a template URI is given in the request, the service will try to use that resource instead.

Here are two examples:

- [Azure CLI](templates/azurecli.html)
- [Go SDK](templates/gosdk.html)

The email's subject line will be extracted from the `title` tagged element from the report content.

## Deployment

- Build the service to a docker image with the [Dockerfile](../Dockerfile).
- Deploy the service using the [Kubernetes definition](../../../deployment/def/deployment.yml)
