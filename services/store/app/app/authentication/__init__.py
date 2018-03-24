import os
import base64
import json
import logging
from functools import wraps
from datetime import datetime, timedelta

import jwt
import requests
from flask import Response, request, jsonify

from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

INTERNAL_COMMUNICATION_KEY = os.environ.get('A01_INTERNAL_COMKEY', base64.b64encode(os.urandom(16)))


class AzureADPublicKeysManager(object):
    def __init__(self,
                 jwks_uri: str = 'https://login.microsoftonline.com/common/discovery/keys',
                 client_id: str = '00000002-0000-0000-c000-000000000000'):
        self._logger = logging.getLogger(__name__)
        self._last_update = datetime.min
        self._certs = {}
        self._jwks_uri = jwks_uri
        self._client_id = client_id

    def _refresh_certs(self) -> None:
        """Refresh the public certificates for every 12 hours."""
        if datetime.utcnow() - self._last_update >= timedelta(hours=12):
            self._logger.info('Refresh the certificates')
            self._update_certs()
            self._last_update = datetime.utcnow()
        else:
            self._logger.info('Skip refreshing the certificates')

    def _update_certs(self) -> None:
        self._certs.clear()
        response = requests.get(self._jwks_uri)
        for key in response.json()['keys']:
            cert_str = "-----BEGIN CERTIFICATE-----\n{}\n-----END CERTIFICATE-----\n".format(key['x5c'][0])
            cert_obj = load_pem_x509_certificate(cert_str.encode('utf-8'), default_backend())
            public_key = cert_obj.public_key()
            self._logger.info('Create public key for %s from cert: %s', key['kid'], cert_str)
            self._certs[key['kid']] = public_key

    def get_public_key(self, key_id: str):
        self._refresh_certs()
        return self._certs[key_id]

    def get_id_token_payload(self, id_token: str):
        header = json.loads(base64.b64decode(id_token.split('.')[0]).decode('utf-8'))
        key_id = header['kid']
        public_key = self.get_public_key(key_id)

        return jwt.decode(id_token, public_key, audience=self._client_id)


jwt_auth = AzureADPublicKeysManager()  # pylint: disable=invalid-name


def auth(fn):  # pylint: disable=invalid-name
    @wraps(fn)
    def _wrapper(*args, **kwargs):
        try:
            jwt_raw = request.environ['HTTP_AUTHORIZATION']
            if jwt_raw != INTERNAL_COMMUNICATION_KEY:
                jwt_auth.get_id_token_payload(jwt_raw)
        except KeyError:
            return Response(json.dumps({'error': 'Unauthorized', 'message': 'Missing authorization header.'}), 401)
        except jwt.ExpiredSignatureError:
            return Response(json.dumps({'error': 'Expired', 'message': 'The JWT token is expired.'}), 401)
        except UnicodeDecodeError:
            return jsonify({'error': 'Bad Request', 'message': 'Authorization header cannot be parsed'}), 400

        return fn(*args, **kwargs)

    return _wrapper
