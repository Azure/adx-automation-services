import os
from typing import Tuple

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP

import requests

INTERNAL_COMMUNICATION_KEY = os.environ['A01_INTERNAL_COMKEY']
SMTP_SERVER = os.environ['A01_REPORT_SMTP_SERVER']
SMTP_USER = os.environ['A01_REPORT_SENDER_ADDRESS']
SMTP_PASS = os.environ['A01_REPORT_SENDER_PASSWORD']


def is_healthy() -> Tuple[str, str]:
    """Returns the health status in the form of (status, remark)"""
    status = 'healthy'
    remark = 'no issue'

    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASS:
        status = 'unhealthy'
        remark = 'missing SMTP settings'

    if not INTERNAL_COMMUNICATION_KEY:
        status = 'unhealthy'
        remark = 'missing internal communication key'

    return status, remark


def get_task_store_uri(path: str) -> str:
    # in debug mode, the service is likely run out of a cluster, switch to https schema
    store_host = os.environ.get('A01_STORE_NAME', 'task-store-web-service-internal')
    return f'https://{store_host}/api/{path}' if 'FLASK_DEBUG' in os.environ else f'http://{store_host}/api/{path}'


def http_get(path: str):
    class InternalAuth(object):  # pylint: disable=too-few-public-methods
        def __call__(self, req):
            req.headers['Authorization'] = INTERNAL_COMMUNICATION_KEY
            return req

    session = requests.Session()
    session.auth = InternalAuth()

    try:
        return session.get(get_task_store_uri(path)).json()
    except (requests.HTTPError, ValueError, TypeError):
        return None


def send_email(receivers: str, subject: str, content: str):
    mail = MIMEMultipart()
    mail['Subject'] = subject
    mail['From'] = SMTP_USER
    mail['To'] = receivers
    mail.attach(MIMEText(content, 'html'))

    with SMTP(SMTP_SERVER) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(mail)
