A01Store
--------

A01Store service accept automation tests scheduled by the Control (or user) and store it in a database. The test tasks are available to the automation droids. The A01Store plays a passive role in the producer-consumer releationship meaning the driver is the consumer (A01Droid).

# Basic
- Python 3 (3.6)
- Container based
- Flask

# Deployments note
- Set up namespace.
- Set up context.
- Set up secret. The vault is a0secret
- Set up private docker registry secret using sp azureclidev-contributor

# Database Migration Guid

When the data model is changed the database scheme needs to be upgraded as well. This application relies 
on the Flask-Migrate package to handle the data migrations.

## Steps

- Execute `. script/set_connection_str.sh` to set connection string. You need to have the access to
  the a01store key vault.
- Execute `export FLASK_APP=app/main`
- Execute `flask db migrate`. Validate the migration
- Execute `flask db upgrade`.
