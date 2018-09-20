FROM python:3-alpine
MAINTAINER Simon Jupp "jupp@ebi.ac.uk"

# added for dependency healthchecks
RUN apk update && \
    apk add curl && \
    apk add build-base && \
    apk add openssl-dev && \
    apk add libffi-dev && \
    apk add git

RUN mkdir /app
WORKDIR /app
COPY stagingmanager.py listener.py requirements.txt ./

COPY start_up.sh ./
RUN chmod +x start_up.sh

RUN pip install -r requirements.txt

ENV INGEST_API=http://localhost:8080
ENV RABBIT_URL=amqp://localhost:5672
ENV SUBMISSION_QUEUE_NAME=ingest.envelope.created.queue
ENV STAGING_API=https://staging.staging.data.humancellatlas.org
ENV STAGING_API_VERSION=v1
ENV INGEST_API_KEY=key_not_set

ENTRYPOINT ["./start_up.sh"]
