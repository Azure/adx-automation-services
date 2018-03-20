import os
from typing import List, Tuple
from datetime import datetime, timedelta

import requests
from jinja2 import Environment, FunctionLoader
from lxml import html

GENERIC_TEMPLATE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generic.html')


def render(run: dict, tasks: List[dict], template: str) -> Tuple[str, str]:
    # update creation time to PST
    creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)
    run['creation'] = creation.strftime('%Y/%m/%d %H:%M PST')

    # generate mail body
    env = Environment(loader=FunctionLoader(load_func=_template_loader))
    template = env.get_template(template)
    content = template.render(run=run, tasks=tasks)

    # extract title
    try:
        title = html.fromstring(content).find('head/title')
        subject = title.text.strip('\n ')
    except AttributeError:
        subject = f'A01 Automation Report {run["id"]}'

    return content, subject


def _template_loader(template_uri: str) -> str:
    if template_uri:
        try:
            resp = requests.get(template_uri)
            resp.raise_for_status()
            return resp.text
        except requests.HTTPError:
            pass

    with open(GENERIC_TEMPLATE_PATH, 'r') as handler:
        return handler.read()
