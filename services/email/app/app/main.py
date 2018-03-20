"""
Email service

Accept request from other controllers in the cluster to send email. The service doesn't accept request originates
originates out of the cluster therefore authentication is no needed.
"""

import os
import logging
from datetime import datetime
from typing import Tuple

import requests
import coloredlogs
import jinja2
from flask import Flask, jsonify, request

from app.templates import create_template
from app.util import is_healthy, send_email, http_get

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
    product = run['details'].get('a01.reserved.product', 'generic')
    logger.info(f'successfully read run {run_id} for product {product}.')

    # select the template
    template_dir, template_file, actual_product = download_template(template_url, product)
    logging.info(f'composing report with template {template_file} as {actual_product} ...')
    email_template = create_template(actual_product)

    content = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir)
    ).get_template(template_file).render(email_template.get_context(run, tasks))
    subject = email_template.get_subject(run, tasks)

    # send email
    send_email(receivers, subject, content)

    return jsonify({'status': 'done'})


def download_template(uri: str, product: str) -> Tuple[str, str, str]:
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if uri:
        template_local_path = os.path.join(template_dir, f'{product}.html')
        try:
            resp = requests.get(uri)
            resp.raise_for_status()
            with open(template_local_path, 'w') as handler:
                handler.write(resp.text)
            return template_dir, f'{product}.html', product
        except requests.HTTPError:
            logger.exception('Fail to request template file.')
        except IOError:
            logger.exception('Fail to write template file.')
    else:
        logger.warning("Template URI is empty")

    return template_dir, 'generic.html', 'generic'
