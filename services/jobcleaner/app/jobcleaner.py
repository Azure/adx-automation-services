import os
import logging
import functools

from kubernetes.config import load_incluster_config, load_kube_config, ConfigException, list_kube_config_contexts
from kubernetes.client import BatchV1Api
from kubernetes.client.models import V1DeleteOptions

import requests


class InternalAuth(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        self._comkey = os.environ['A01_INTERNAL_COMKEY']

    def __call__(self, req):
        req.headers['Authorization'] = self._comkey
        return req


STORE_URL = os.environ.get('A01_STORE_NAME')
STORE_URL = f'http://{STORE_URL}' if not STORE_URL.startswith('http') else STORE_URL

logger = logging.getLogger("A01.JobCleaner")  # pylint: disable=invalid-name
logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(name)s %(levelname)s -> %(message)s')


session = requests.Session()  # pylint: disable=invalid-name
session.auth = InternalAuth()


def main() -> None:
    load_config()
    batch_api = BatchV1Api()
    delete_opt = V1DeleteOptions(propagation_policy='Foreground')

    ns = current_namespace()  # pylint: disable=invalid-name
    for j in batch_api.list_namespaced_job(ns).items:
        job_name = j.metadata.name
        run_id = j.metadata.labels.get('run_id', None)
        if not run_id:
            continue
        is_completed = is_run_completed(run_id)

        logger.info(f'{job_name} -> {run_id} -> {is_completed}')
        if is_completed:
            logger.info(batch_api.delete_namespaced_job(job_name, ns, delete_opt))
        else:
            logger.info('skip deleting')


@functools.lru_cache()
def is_run_completed(run_id: str) -> bool:
    try:
        resp = session.get(f'{STORE_URL}/api/run/{run_id}')
        resp.raise_for_status()

        return resp.json()['status'] == 'Completed'

    except requests.HTTPError:
        return False


@functools.lru_cache()
def current_namespace() -> str:
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", mode='r') as handler:
            return handler.readline()
    except IOError:
        try:
            return list_kube_config_contexts()[1]['context']['namespace']
        except (IndexError, KeyError):
            logger.error('Fail to get current namespace.')


def load_config() -> None:
    try:
        load_incluster_config()
    except ConfigException:
        try:
            load_kube_config()
        except ConfigException:
            logger.error('Fail to get kubernete configuration.')


if __name__ == '__main__':
    main()
