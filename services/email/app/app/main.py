"""
Email service

Accept request from other controllers in the cluster to send email. The service doesn't accept request originates
originates out of the cluster therefore authentication is no needed.
"""

import logging
from datetime import datetime

import coloredlogs
from flask import Flask, jsonify, request

from .templates import render
from .util import is_healthy, send_email, http_get

app = Flask(__name__)  # pylint: disable=invalid-name

coloredlogs.install(level=logging.INFO)
logger = logging.getLogger('a01.svc.email')  # pylint: disable=invalid-name


@app.route('/health')
def health():
    status, remark = is_healthy()
    return jsonify({'status': status, 'time': datetime.utcnow(), 'remark': remark})


@app.route('/report', methods=['POST'])
def send_report():
    logger.info('requested to send email')

    # parse input
    run_id = request.json['run_id']
    receivers = request.json['receivers']
    template_url = request.json.get('template', None)
    logger.info(f'run: {run_id} | receivers: {receivers} | template: {template_url or "None"}')

    # retrieve run and tasks
    run = http_get(f'run/{run_id}')
    tasks = sorted(http_get(f'run/{run_id}/tasks'), key=lambda t: t['status'])
    logger.info(f'successfully read run {run_id}.')
    logger.info(f'using template {template_url or "unknown"}.')

    # send email
    content, subject = render(run, tasks, template_url)
    send_email(receivers, subject, content)

    return jsonify({'status': 'done'})
