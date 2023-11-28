#!/usr/bin/env python
"""
Listens for messages from ingest to create a staging area, post back the credentials for uploading
files to the staging area
"""
from http import HTTPStatus

from ingest.api.ingestapi import IngestApi
from ingest.api.stagingapi import StagingApi

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

from ingest.utils.s2s_token_client import ServiceCredential, S2STokenClient
from ingest.utils.token_manager import TokenManager
from requests import HTTPError

from listener import Listener

DEFAULT_RABBIT_URL = os.path.expandvars(os.environ.get('RABBIT_URL', 'amqp://localhost:5672'))


class StagingManager:
    def __init__(self):
        log_format = ' %(asctime)s  - %(name)s - %(levelname)s in %(filename)s:%(lineno)s %(funcName)s(): %(message)s'
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)

        self.logger = logging.getLogger(__name__)
        token_manager = self.init_token_manager()
        self.ingest_api = IngestApi(token_manager=token_manager)
        self.staging_api = StagingApi()

    def create_upload_area(self, body):
        message = json.loads(body)

        if "documentId" in message:
            submission_id = message["documentId"]
            submission_url = self.ingest_api.get_submission_url(submission_id)

            uuid = self.ingest_api.get_object_uuid(submission_url)
            self.logger.info("Creating upload area for submission " + uuid)

            upload_area_credentials = self.staging_api.createStagingArea(uuid)
            self.logger.info(
                "Upload area created! patching creds to subs envelope " + json.dumps(upload_area_credentials))
            self.ingest_api.update_staging_details(submission_url, uuid, upload_area_credentials["uri"])

    def delete_upload_area(self, body):
        message = json.loads(body)

        if "documentId" in message:
            submission_id = message["documentId"]
            submission_uuid = message["documentUuid"]
            self.logger.info("Trying to delete the upload area for submission_uuid: " + submission_uuid)
            if self.staging_api.hasStagingArea(submission_uuid):
                self.staging_api.deleteStagingArea(submission_uuid)
                self.logger.info("Upload area deleted!")
            else:
                self.logger.warning("There is no upload area found.")

            if self._get_submission(submission_uuid):
                self.set_submission_to_complete(submission_id)

    def _get_submission(self, submission_uuid):
        try:
            submission = self.ingest_api.get_submission_by_uuid(submission_uuid)
        except HTTPError as httpError:
            if httpError.response.status_code == HTTPStatus.NOT_FOUND:
                submission = None
        return submission

    def set_submission_to_complete(self, submission_id):
        for i in range(1, 5):
            try:
                self.ingest_api.update_submission_state(submission_id, 'complete')
                self.logger.info('Submission status is set to COMPLETE')
            except Exception:
                self.logger.info("failed to set state of submission {0} to Complete, retrying...".format(submission_id))
                time.sleep(1)
    @staticmethod
    def init_token_manager():
        gcp_credentials_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        credential = ServiceCredential.from_file(gcp_credentials_file)
        audience = os.environ.get('INGEST_API_JWT_AUDIENCE')
        s2s_token_client = S2STokenClient(credential, audience)
        token_manager = TokenManager(s2s_token_client)
        return token_manager


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
