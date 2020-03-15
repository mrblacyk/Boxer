from __future__ import absolute_import, unicode_literals
from django.conf import settings
from alphapwners.celery import app

import logging

logger = logging.getLogger("celery")


@app.task
def show_hello_world():
    logger.info("-" * 25)
    logger.info("Printing Hello from Celery")
    logger.info("-" * 25)

    return None
