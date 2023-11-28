# ingest-staging-manager
Client for handling the creation of staging areas triggered by the ingest service

### Authenticated Access to Ingest API
The staging manager needs authenticated access to API. It therefore needs to acquire the token from the service account
similarly to the system tests and graph validation.

TODO: add instructions or link
```
mkdir _local
```
* The GCP credentials are stored in AWS Secrets Manager; To download GCP credentials and save it into a file, the AWS CLI can be used:

```bash
read -p "enter environment [dev,prod]" DEPLOYMENT_ENV
mkdir -p ~/.secrets
chmod 700 ~/.secrets
aws secretsmanager get-secret-value \
  --profile embl-ebi \
  --region us-east-1 \
  --secret-id ingest/${DEPLOYMENT_ENV}/gcp-credentials.json | jq -r .SecretString > ~/.secrets/gcp-credentials-${DEPLOYMENT_ENV}.json
# replace /Users with the home directory location in your env
export GOOGLE_APPLICATION_CREDENTIALS=/Users/$USER/.secrets/gcp-credentials-${DEPLOYMENT_ENV}.json
export INGEST_API_JWT_AUDIENCE=https://dev.data.humancellatlas.org/
```

This behaviour was introduced as part of the Managed Access effort. See ebi-ait/dcp-ingest-central#967
