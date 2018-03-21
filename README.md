# Services for the ADX Automation System

## The email service

See details [here](services/email/docs/README.md)

## The task store service

A01Store service accept automation tests scheduled by the Control (or user) and store it in a database. The test tasks are available to the automation droids. The A01Store plays a passive role in the producer-consumer releationship meaning the driver is the consumer (A01Droid).

### Basic

- Python 3 (3.6)
- Container based
- Flask

### Deployments note

- Set up namespace.
- Set up context.
- Set up secret. The vault is a0secret
- Set up private docker registry secret using sp azureclidev-contributor

### Database Migration Guid

When the data model is changed the database scheme needs to be upgraded as well. This application relies 
on the Flask-Migrate package to handle the data migrations.

### Steps

- Execute `. script/set_connection_str.sh` to set connection string. You need to have the access to
  the a01store key vault.
- Execute `export FLASK_APP=app/main`
- Execute `flask db migrate`. Validate the migration
- Execute `flask db upgrade`.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
