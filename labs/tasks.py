import time

from celery import shared_task


@shared_task
def send_confirmation_email(subscriber_id):
    time.sleep(2)
    return subscriber_id