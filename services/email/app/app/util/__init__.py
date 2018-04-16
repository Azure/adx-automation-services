import os
import logging
from typing import Tuple, Optional

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP

import requests

INTERNAL_COMMUNICATION_KEY = os.environ['A01_INTERNAL_COMKEY']
SMTP_SERVER = os.environ['A01_REPORT_SMTP_SERVER']
SMTP_USER = os.environ['A01_REPORT_SENDER_ADDRESS']
SMTP_PASS = os.environ['A01_REPORT_SENDER_PASSWORD']

STORE_URL = os.environ.get('A01_STORE_NAME')
STORE_URL = f'http://{STORE_URL}' if not STORE_URL.startswith('http') else STORE_URL

logger = logging.getLogger('a01.svc.email')  # pylint: disable=invalid-name


class InternalAuth(object):  # pylint: disable=too-few-public-methods
    def __call__(self, req):
        req.headers['Authorization'] = INTERNAL_COMMUNICATION_KEY
        return req


session = requests.Session()  # pylint: disable=invalid-name
session.auth = InternalAuth()


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


def http_get(path: str) -> Optional[dict]:
    try:
        resp = session.get(f'{STORE_URL}/api/{path}')
        resp.raise_for_status()

        return resp.json()
    except (requests.HTTPError, ValueError, TypeError):
        return None


def send_email(receivers: str, subject: str, content: str) -> None:
    mail = MIMEMultipart()
    mail['Subject'] = subject
    mail['From'] = SMTP_USER
    mail['To'] = receivers
    mail.attach(MIMEText(content, 'html'))

    with SMTP(SMTP_SERVER) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(mail)
