"""
Email service

Accept request from other controllers in the cluster to send email. The service doesn't accept request originates
originates out of the cluster therefore authentication is no needed.
"""

import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP

import requests
import coloredlogs
from tabulate import tabulate
from flask import Flask, jsonify, request

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

    statuses = defaultdict(lambda: 0)
    results = defaultdict(lambda: 0)

    failure = []

    logging.info('begin composing report')
    for task in tasks:
        status = task['status']
        result = task['result']

        statuses[status] = statuses[status] + 1
        results[result] = results[result] + 1

        if result != 'Passed':
            if run['details'].get('a01.reserved.product', None) == 'azurecli':
                test_name = task['settings']['classifier']['identifier']
                if test_name.startswith('azure.cli.command_modules'):
                    module_name = test_name.split('.')[3]
                else:
                    module_name = 'CORE'
            else:
                module_name = None

            failure.append(
                (task['id'],
                 task['name'].rsplit('.')[-1],
                 task['status'],
                 task['result'],
                 (task.get('result_details') or dict()).get('duration'),
                 module_name))

    status_summary = ' | '.join([f'{status_name}: {count}' for status_name, count in statuses.items()])
    result_summary = ' | '.join([f'{result or "Not run"}: {count}' for result, count in results.items()])

    creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)

    summaries = [('Id', run['id']),
                 ('Creation', str(creation) + ' PST'),
                 ('Creator', run['details'].get('a01.reserved.creator', 'N/A')),
                 ('Remark', run['settings'].get('a01.reserved.remark', 'N/A')),
                 ('Live', run['settings'].get('a01.reserved.livemode')),
                 ('Task', status_summary),
                 ('Image', run['settings'].get('a01.reserved.imagename', 'N/A')),
                 ('Result', result_summary)]

    content = f"""\
    <html>
        <body>
            <div>
                <h2>Summary</h2>
                {tabulate(summaries, tablefmt="html")}
            </div>
            <div>
                <h2>Failures</h2>
                {tabulate(failure, headers=("id", "name", "status", "result", "duration(ms)", "module"), tablefmt="html")}
            </div>
            <div>
                <h2>More details</h2>
                <p>Install the latest release of A01 client to download log and recordings.</p>
                <p>Instruction is here: https://github.com/azure/adx-automation-client</p>
                <code>
                $ a01 login<br>
                $ a01 get runs -l {run['id']}<br>
                </code>
                <p>Contact: trdai@microsoft.com</p>
            </div>
        </body>
    </html>"""

    mail = MIMEMultipart()
    mail['Subject'] = f'Azure CLI Automation Run {str(creation)} - {result_summary}.'
    mail['From'] = SMTP_USER
    mail['To'] = receivers
    mail.attach(MIMEText(content, 'html'))

    logger.info('sending emails.')
    with SMTP(SMTP_SERVER) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(mail)

    return jsonify({'status': 'done'})

