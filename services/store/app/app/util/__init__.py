import os
import base64
import logging

from kubernetes.config import load_incluster_config, load_kube_config, ConfigException

logger = logging.getLogger('kubeutil')  # pylint: disable=invalid-name


def get_communication_key() -> str:
    """Returns the internal communication key.

    This method look for the key in following order:
    1. Environment variable A01_INTERNAL_COMKEY
    2. Select a random string and print to the log for testing purpose
    """
    result = os.environ.get('A01_INTERNAL_COMKEY', None)
    if result:
        logger.info(f'Communication key from environment. First 8 char: {result[:8]}')
    else:
        if os.path.exists('tempkey'):
            with open('tempkey', 'r') as temp_key_file:
                result = temp_key_file.read()
                logger.info(f'Communication key generated in random. {result}')
        else:
            with open('tempkey', 'w') as temp_key_file:
                result = base64.b64encode(os.urandom(24)).decode('utf-8')
                temp_key_file.write(result)
                logger.info(f'Communication key from random. {result}')

    return result


def get_current_namespace() -> str:
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", mode='r') as handler:
        return handler.readline()


def _load_config() -> bool:
    try:
        load_incluster_config()
    except ConfigException:
        try:
            load_kube_config()
        except ConfigException:
            logger.error('Fail to get kubernetes configuration.')
            return False

    return True
