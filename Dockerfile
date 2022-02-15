FROM quay.io/ebi-ait/ingest-base-images:python_3.8.5-alpine

# added for dependency healthchecks
RUN apk update && \
    apk add curl && \
    apk add build-base && \
    apk add openssl-dev && \
    apk add libffi-dev && \
    apk add git

RUN mkdir /app
WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY stagingmanager.py listener.py start_up.sh ./
RUN chmod +x start_up.sh

ENV INGEST_API=https://api.ingest.dev.archive.data.humancellatlas.org/
ENV RABBIT_URL=amqp://localhost:5672
ENV SUBMISSION_QUEUE_NAME=ingest.envelope.created.queue
ENV STAGING_API=https://upload.dev.archive.data.humancellatlas.org
ENV STAGING_API_VERSION=v1
ENV INGEST_API_KEY=key_not_set

ENTRYPOINT ["./start_up.sh"]
