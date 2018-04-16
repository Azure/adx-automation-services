import os
from typing import List, Tuple
from datetime import datetime, timedelta

import requests
from jinja2 import Environment, FunctionLoader
from lxml import html


def render(run: dict, tasks: List[dict], template: str) -> Tuple[str, str]:
    """
    Render a report email body using the Jinja template. Returns a tuple of <Content, Subject>.

    The subject line is the title element under head element in the HTML.
    """

    # update creation time to PST
    creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)
    run['creation'] = creation.strftime('%Y/%m/%d %H:%M PST')

    # generate mail body
    env = Environment(loader=FunctionLoader(load_func=_http_template_loader))
    template = env.get_template(template)
    content = template.render(run=run, tasks=tasks)

    # extract title
    try:
        title = html.fromstring(content).find('head/title')
        subject = title.text.strip('\n ')
    except AttributeError:
        subject = f'A01 Automation Report {run["id"]}'

    return content, subject


def _http_template_loader(template_uri: str) -> str:
    """Load the template from a HTTP resource and returns the content."""
    if template_uri:
        try:
            resp = requests.get(template_uri)
            resp.raise_for_status()
            return resp.text
        except requests.HTTPError:
            pass

    generic_template_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generic.html')
    with open(generic_template_path, 'r') as handler:
        return handler.read()
