"""
Email service

Accept request from other controllers in the cluster to send email. The service doesn't accept request originates
originates out of the cluster therefore authentication is no needed.
"""

import os
import logging
from datetime import datetime

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP

import requests
import coloredlogs
from flask import Flask, jsonify, request
import jinja2
import templates.email as template

app = Flask(__name__)  # pylint: disable=invalid-name

coloredlogs.install(level=logging.INFO)
logger = logging.getLogger('a01.svc.email')  # pylint: disable=invalid-name

INTERNAL_COMMUNICATION_KEY = os.environ['A01_INTERNAL_COMKEY']
SMTP_SERVER = os.environ['A01_REPORT_SMTP_SERVER']
SMTP_USER = os.environ['A01_REPORT_SENDER_ADDRESS']
SMTP_PASS = os.environ['A01_REPORT_SENDER_PASSWORD']
STORE_HOST = os.environ.get('A01_STORE_NAME', 'task-store-web-service-internal')


class InternalAuth(object):  # pylint: disable=too-few-public-methods
    def __call__(self, req):
        req.headers['Authorization'] = INTERNAL_COMMUNICATION_KEY
        return req


SESSION = requests.Session()
SESSION.auth = InternalAuth()


def get_task_store_uri(path: str) -> str:
    # in debug mode, the service is likely run out of a cluster, switch to https schema
    if app.debug:
        return f'https://{STORE_HOST}/api/{path}'
    return f'http://{STORE_HOST}/api/{path}'


@app.route('/health')
def healthy():
    status = 'healthy'
    remark = ''

    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASS:
        logger.error('missing environment variable to setup email service.')
        status = 'unhealthy'
        remark = 'missing SMTP settings'

    if not INTERNAL_COMMUNICATION_KEY:
        logger.error('missing internal communication key')
        status = 'unhealthy'
        remark = 'missing internal communication key'

    return jsonify({'status': status, 'time': datetime.utcnow(), 'remark': remark})


@app.route('/report', methods=['POST'])
def send_report():
    logger.info('requested to send email')
    run_id = request.json['run_id']
    receivers = request.json['receivers']
    logger.info(f'run: {run_id} | receivers: {receivers}')

    run = SESSION.get(get_task_store_uri(f'run/{run_id}')).json()
    tasks = sorted(SESSION.get(get_task_store_uri(f'run/{run_id}/tasks')).json(), key=lambda t: t['status'])

    logger.info(f'successfully read run {run_id}.')

    product = run['details'].get('a01.reserved.product', None)
    directory = f'{os.path.dirname(os.path.abspath(__file__))}/templates'

    if not os.path.exists(f'{directory}/{product}.html'):
        logger.error(f'there isn`t a template for product {product}')

    logging.info(f'begin composing report with template {product}')
    email_template = template.Email(product)

    content = jinja2.Environment(
        loader=jinja2.FileSystemLoader(directory)
    ).get_template(f'{product}.html').render(email_template.get_context(run, tasks))

    mail = MIMEMultipart()
    mail['Subject'] = email_template.get_subject(run, tasks)
    mail['From'] = SMTP_USER
    mail['To'] = receivers
    mail.attach(MIMEText(content, 'html'))

    logger.info('sending emails.')
    with SMTP(SMTP_SERVER) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(mail)

    return jsonify({'status': 'done'})
