
import os
import logging
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
import coloredlogs
import requests
from kubernetes import client as kube_client
from kubernetes import config as kube_config

coloredlogs.install(level=logging.INFO)
logger = logging.getLogger('a01.svc.email.newsletter')  # pylint: disable=invalid-name

INTERNAL_COMMUNICATION_KEY = os.environ['A01_INTERNAL_COMKEY']
SMTP_SERVER = os.environ['A01_REPORT_SMTP_SERVER']
SMTP_USER = os.environ['A01_REPORT_SENDER_ADDRESS']
SMTP_PASS = os.environ['A01_REPORT_SENDER_PASSWORD']

DEV = os.environ['DEV']
PRODUCTS = os.environ['PRODUCTS'] # products that requirte a runs newsletter

def get_task_store_uri(path: str) -> str:
    # in debug mode, the service is likely run out of a cluster, switch to https schema
    store_host = os.environ.get('A01_STORE_NAME', 'task-store-web-service-internal')
    if not DEV:
        return f'https://{store_host}/api/{path}'
    return f'http://{store_host}/api/{path}'

def http_get(path: str, params: dict = None):
    class InternalAuth(object):  # pylint: disable=too-few-public-methods
        def __call__(self, req):
            req.headers['Authorization'] = INTERNAL_COMMUNICATION_KEY
            return req

    session = requests.Session()
    session.auth = InternalAuth()

    try:
        return session.get(get_task_store_uri(path), params=params).json()
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

def get_receivers(product: str) -> str:
    receivers = get_secret_data(product, 'owners.weekly')
    logger.info(f'receivers for email are {receivers}')
    return receivers

def get_template(product: str) -> str:
    template_uri = get_secret_data(product, 'email.path.template.weekly')
    logger.info(f'template for email is {template_uri}')
    return template_uri

def get_secret_data(product: str, data: str) -> str:
    if DEV:
        kube_config.load_kube_config()
    else:
        kube_config.load_incluster_config()

    api = kube_client.CoreV1Api()
    namespace = os.environ.get('A01_NAMESPACE', 'a01-prod')
    secret = api.read_namespaced_secret(name=product, namespace=namespace)

    if data not in secret.data:
        return None

    secret_data = base64.standard_b64decode(secret.data[data]).decode("utf-8")
    return secret_data
