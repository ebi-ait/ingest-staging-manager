#!/usr/bin/env python
"""
Listens for messages from ingest to create a staging area, post back the credentials for uploading
files to the staging area
"""
__author__ = "jupp"
__license__ = "Apache 2.0"
__date__ = "15/09/2017"


import json
import logging
import os
import sys
import threading
import time
from optparse import OptionParser

from ingest.api.ingestapi import IngestApi
from ingest.api.stagingapi import StagingApi

from listener import Listener

DEFAULT_RABBIT_URL = os.path.expandvars(os.environ.get('RABBIT_URL', 'amqp://localhost:5672'))


class StagingManager:
    def __init__(self):
        log_format = ' %(asctime)s  - %(name)s - %(levelname)s in %(filename)s:%(lineno)s %(funcName)s(): %(message)s'
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)

        self.logger = logging.getLogger(__name__)
        self.ingest_api = IngestApi()
        self.staging_api = StagingApi()

    def create_upload_area(self, body):
        message = json.loads(body)

        if "documentId" in message:
            submission_id = message["documentId"]
            submission_url = self.ingest_api.getSubmissionUri(submission_id)

            uuid = self.ingest_api.getObjectUuid(submission_url)
            self.logger.info("Creating upload area for submission " + uuid)

            upload_area_credentials = self.staging_api.createStagingArea(uuid)
            self.logger.info(
                "Upload area created! patching creds to subs envelope " + json.dumps(upload_area_credentials))
            self.ingest_api.updateSubmissionWithStagingCredentials(submission_url, uuid, upload_area_credentials["urn"])

    def delete_upload_area(self, body):
        message = json.loads(body)

        if "documentId" in message:
            submission_id = message["documentId"]
            submission_url = self.ingest_api.getSubmissionUri(submission_id)
            submission_uuid = self.ingest_api.getObjectUuid(submission_url)

            if self.staging_api.hasStagingArea(submission_uuid):
                self.staging_api.deleteStagingArea(submission_uuid)
                self.logger.info("Upload area deleted!")
                self.set_submission_to_complete(submission_id)
            else:
                self.logger.error("There is no upload area found.")

    def set_submission_to_complete(self, submission_id):
        for i in range(1, 5):
            try:
                self.ingest_api.updateSubmissionState(submission_id, 'complete')
                self.logger.info('Submission status is set to COMPLETE')
            except Exception:
                self.logger.info("failed to set state of submission {0} to Complete, retrying...".format(submission_id))
                time.sleep(1)


if __name__ == '__main__':
    log_format = ' %(asctime)s  - %(name)s - %(levelname)s in %(filename)s:%(lineno)s %(funcName)s(): %(message)s'
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)

    parser = OptionParser()
    parser.add_option("-q", "--queue", help="name of the ingest queues to listen for submission")
    parser.add_option("-r", "--rabbit", help="the URL to the Rabbit MQ messaging server")
    parser.add_option("-l", "--log", help="the logging level", default='INFO')

    (options, args) = parser.parse_args()

    staging_manager = StagingManager()
    # start a listener for creating new upload are
    create_listener = Listener({
        'rabbit': DEFAULT_RABBIT_URL,
        'on_message_callback': staging_manager.create_upload_area,
        'exchange': 'ingest.upload.area.exchange',
        'exchange_type': 'topic',
        'queue': 'ingest.upload.area.create.queue',
        'routing_key': 'ingest.upload.area.create'
    })
    t = threading.Thread(target=create_listener.run)
    t.start()

    # start a listener for deleting upload area
    delete_listener = Listener({
        'rabbit': DEFAULT_RABBIT_URL,
        'on_message_callback': staging_manager.delete_upload_area,
        'exchange': 'ingest.upload.area.exchange',
        'exchange_type': 'topic',
        'queue': 'ingest.upload.area.cleanup.queue',
        'routing_key': 'ingest.upload.area.cleanup'
    })

    t = threading.Thread(target=delete_listener.run)
    t.start()
