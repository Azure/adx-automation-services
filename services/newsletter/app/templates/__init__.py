import os
from typing import List, Tuple
import requests
from jinja2 import Environment, FunctionLoader
from lxml import html

GENERIC_TEMPLATE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generic.html')

def render(template_uri: str, runs: List[dict], tasks: List[dict],
           after: str, before: str) -> Tuple[str, str]:
    # generate mail body
    env = Environment(
        loader=FunctionLoader(load_func=_template_loader),
        extensions=['jinja2.ext.do'],
        )
    template = env.get_template(template_uri)
    content = template.render(runs=runs, tasks=tasks, after=after, before=before)

    # extract title
    try:
        title = html.fromstring(content).find('head/title')
        subject = title.text.strip('\n ')
    except AttributeError:
        subject = f'A01 Automation Weekly Report: {after} - {before}'

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
