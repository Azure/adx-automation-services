"""
A01Store service accept automation tests scheduled by the Control (or user)
and store it in a database. The test tasks are available to the automation
droids. The A01Store plays a passive role in the producer-consumer
relationship meaning the driver is the consumer (A01Droid).
"""
from datetime import datetime, timedelta
import base64
import logging
import os
import json
from functools import wraps
from packaging import version

import coloredlogs
from flask import Flask, jsonify, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import jwt
import requests
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

from kubernetes import config as kube_config
from kubernetes import client as kube_client
from kubernetes.client import V1ObjectFieldSelector
from kubernetes.client.models.v1_delete_options import V1DeleteOptions
from kubernetes.client.models.v1_job import V1Job
from kubernetes.client.models.v1_job_spec import V1JobSpec
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_container import V1Container
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes.client.models.v1_local_object_reference import V1LocalObjectReference
from kubernetes.client.models.v1_env_var import V1EnvVar
from kubernetes.client.models.v1_env_var_source import V1EnvVarSource
from kubernetes.client.models.v1_secret_key_selector import V1SecretKeySelector
from kubernetes.client.models.v1_volume_mount import V1VolumeMount
from kubernetes.client.models.v1_volume import V1Volume
from kubernetes.client.models.v1_azure_file_volume_source import V1AzureFileVolumeSource

coloredlogs.install(level=logging.INFO)

app = Flask(__name__)  # pylint: disable=invalid-name
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['A01_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)  # pylint: disable=invalid-name
migrate = Migrate(app, db)  # pylint: disable=invalid-name
INTERNAL_COMMUNICATION_KEY = os.environ['A01_INTERNAL_COMKEY']


def _unify_json_input(data):
    if data is None:
        return None

    if isinstance(data, dict):
        return json.dumps(data)

    return str(data)


def _unify_json_output(data):
    if data is None:
        return None

    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return data


class Run(db.Model):
    # unique id
    id = db.Column(db.Integer, primary_key=True)

    # display name for the test run
    name = db.Column(db.String)

    # the owner who creates this run. it is the user id for a human and service principal name for a service principal
    # this column was added in later version, for legacy data, the a01.reserved.creator or creator in the settings or
    # details column will be copied here.
    owner = db.Column(db.String)

    # The test run settings is a immutable value. It is expected to be a JSON, however, it can be in any other form as
    # long as it can be represented in a string. The settings must not contain any secrets such as password or database
    # connection string. Those value should be sent to the test droid through Kubernete secret. And the values in the
    # settings can help the test droid locating to the correct secret value.
    settings = db.Column(db.String)

    # The details of the test run is mutable. It is expected to be a value bag allows the test system to store
    # information for analysis and presentation. The exact meaning and form of the value is decided by the application.
    # By default it is treated as a JSON object.
    details = db.Column(db.String)

    # The creation time of the run
    creation = db.Column(db.DateTime)

    # The status of this run. It defines the stage of execution. It includes: Initialized, Scheduling, Running, and
    # Completed.
    status = db.Column(db.String)

    def digest(self):
        """Return an serializable object for REST API"""
        result = {
            'id': self.id,
            'name': self.name,
            'owner': self.owner,
            'status': self.status,
            'creation': self.creation.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'details': _unify_json_output(self.details),
            'settings': _unify_json_output(self.settings)
        }

        return result

    def update(self, data):
        """Update this run. Settings, Creation, and ID are readonly."""
        if 'name' in data:
            self.name = data['name']
        if 'owner' in data:
            self.owner = data['owner']
        if 'details' in data:
            self.details = _unify_json_input(data['details'])
        if 'status' in data:
            self.status = data['status']

    @staticmethod
    def create(data: dict) -> 'Run':
        """Create a run data from a json object. This is used to parse user input."""
        result = Run()
        result.update(data)
        result.settings = _unify_json_input(data.get('settings', None))
        result.creation = datetime.utcnow()
        return result


class Task(db.Model):
    # unique id
    id = db.Column(db.Integer, primary_key=True)
    # display name for the test task
    name = db.Column(db.String)
    # annotation of the task, used to fast query tasks under a run. its form is defined by the application.
    annotation = db.Column(db.String)
    # settings of the task. the settings can be saved in JSON or any other format defined by the application. settings
    # are immutable
    settings = db.Column(db.String)
    # status of the task: initialized, scheduled, completed, and ignored
    status = db.Column(db.String)
    # details of the task result. the value can be saved in JSON or any other format defined by the application. the
    # result details are mutable
    result_details = db.Column(db.String)
    # result of the test: passed, failed, and error
    result = db.Column(db.String)
    # the duration of the test run in milliseconds
    duration = db.Column(db.Integer)

    # relationship
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), nullable=False)
    run = db.relationship('Run', backref=db.backref('tasks', cascade='all, delete-orphan', lazy=True))

    immutable_properties = {'name', 'id', 'annotation', 'run_id'}

    def digest(self) -> dict:
        result = {
            'id': self.id,
            'name': self.name,
            'settings': _unify_json_output(self.settings),
            'annotation': self.annotation,
            'status': self.status,
            'duration': self.duration,
            'result': self.result,
            'result_details': _unify_json_output(self.result_details),
            'run_id': self.run_id
        }

        return result

    def load(self, data):
        """Load data from a json object. This is used to parse user input."""
        self.name = data['name']
        self.settings = _unify_json_input(data.get('settings', None))
        self.annotation = data.get('annotation', None)
        self.status = data.get('status', 'initialized')
        self.duration = data.get('duration', None)
        self.result = data.get('result', None)
        self.result_details = _unify_json_input(data.get('result_details', None))

    def update(self, data):
        """Update this task."""
        if 'name' in data:
            self.name = data['name']
        if 'settings' in data:
            self.settings = _unify_json_input(data['settings'])
        if 'annotation' in data:
            self.annotation = data['annotation']
        if 'status' in data:
            self.status = data['status']
        if 'duration' in data:
            self.duration = data['duration']
        if 'result' in data:
            self.result = data['result']
        if 'result_details' in data:
            self.result_details = _unify_json_input(data['result_details'])


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
            return jsonify({'error': 'Bad Request', 'message': 'Authorization header cannot be parsed.'}), 400

        return fn(*args, **kwargs)

    return _wrapper


def get_current_namespace() -> str:
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", mode='r') as handler:
        return handler.readline()


def clean_up_jobs(run_id: str, job_name: str) -> None:
    kube_config.load_incluster_config()
    ns = get_current_namespace()  # pylint: disable=invalid-name

    controller_jobs = kube_client.BatchV1Api().list_namespaced_job(namespace=ns, label_selector=f"run_id={run_id}")

    for job in controller_jobs.items:
        kube_client.BatchV1Api().delete_namespaced_job(name=job.metadata.name,
                                                       namespace=ns,
                                                       body=V1DeleteOptions(propagation_policy='Background'))

    if not job_name:
        return

    test_jobs = kube_client.BatchV1Api().list_namespaced_job(namespace=ns, label_selector=f"job-name={job_name}")
    for job in test_jobs.items:
        kube_client.BatchV1Api().delete_namespaced_job(name=job.metadata.name,
                                                       namespace=ns,
                                                       body=V1DeleteOptions(propagation_policy='Background'))


def create_controller_job(run_id: str, live: bool, image: str, agentver: str) -> V1Job:
    print(f'Create new controller job for run {run_id} ...')

    random_tag = base64.b32encode(os.urandom(4)).decode("utf-8").lower().rstrip('=')
    ctrl_job_name = f'ctrl-{run_id}-{random_tag}'
    labels = {'run_id': str(run_id), 'run_live': str(live)}

    kube_config.load_incluster_config()
    api = kube_client.BatchV1Api()

    return api.create_namespaced_job(
        namespace=get_current_namespace(),
        body=V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=V1ObjectMeta(name=ctrl_job_name, labels=labels),
            spec=V1JobSpec(
                backoff_limit=3,
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(name=ctrl_job_name, labels=labels),
                    spec=V1PodSpec(
                        containers=[V1Container(
                            name='main',
                            image=image,
                            command=['/mnt/agents/a01dispatcher', '-run', str(run_id)],
                            env=[
                                V1EnvVar(name='A01_INTERNAL_COMKEY', value_from=V1EnvVarSource(
                                    secret_key_ref=V1SecretKeySelector(name='store-secrets', key='comkey'))),
                                V1EnvVar(name='ENV_POD_NAME', value_from=V1EnvVarSource(
                                    field_ref=V1ObjectFieldSelector(field_path='metadata.name')))
                            ],
                            volume_mounts=[
                                V1VolumeMount(mount_path='/mnt/agents', name='agents-storage', read_only=True)
                            ]
                        )],
                        image_pull_secrets=[V1LocalObjectReference(name='azureclidev-registry')],
                        volumes=[V1Volume(name='agents-storage',
                                          azure_file=V1AzureFileVolumeSource(read_only=True,
                                                                             secret_name='agent-secrets',
                                                                             share_name=f'linux-{agentver}'))],
                        restart_policy='Never')
                )
            )))


@app.route('/api/health')
@app.route('/api/healthy')
def get_healthy():
    """Healthy status endpoint"""
    return jsonify({'status': 'healthy', 'time': datetime.utcnow()})


@app.route('/api/runs')
@auth
def get_runs():
    """List all the runs"""
    query = Run.query.order_by(Run.creation.desc())
    if 'owner' in request.args:
        query = query.filter_by(owner=request.args['owner'])
    if 'last' in request.args:
        query = query.limit(request.args['last'])
    if 'skip' in request.args:
        query = query.offset(request.args['skip'])
    if 'product' in request.args:
        query = query.filter(Run.details.contains(request.args['product']))
    if 'before' in request.args:
        query = query.filter(Run.creation <= request.args['before'])
    if 'after' in request.args:
        query = query.filter(Run.creation >= request.args['after'])

    return jsonify([r.digest() for r in query.all()])

@app.route('/api/run', methods=['POST'])
@auth
def post_run():
    data = request.json
    if 'details' not in data:
        return jsonify({'error': 'The body of the request misses "details" dictionary'}), 400
    if 'a01.reserved.creator' not in data['details']:
        return jsonify({'error': 'The "a01.reserved.creator" property is missing from the "details". The request was '
                                 'sent from an older version of client. Please upgrade your client.'}), 400
    if 'a01.reserved.client' not in data['details']:
        return jsonify({'error': 'The "a01.reserved.client" property is missing from the "details". The request was '
                                 'sent from an older version of client. Please upgrade your client.'}), 400
    else:
        client_version = version.parse(data['details']['a01.reserved.client'].split(' ')[1])
        if client_version < version.parse('0.15.0'):
            return jsonify({'error': 'Minimal client requirement is "0.15.0". Please upgrade your client'}), 400

    run = Run.create(data)

    db.session.add(run)
    db.session.commit()

    settings = _unify_json_output(run.settings)
    create_controller_job(run_id=str(run.id),
                          live=settings['a01.reserved.livemode'] == str(True),
                          image=settings['a01.reserved.imagename'],
                          agentver=settings['a01.reserved.agentver'])

    return jsonify(run.digest())


@app.route('/api/run/<run_id>', methods=['POST'])
@auth
def update_run(run_id):
    run = Run.query.filter_by(id=run_id).first_or_404()
    try:
        run.update(request.json)
    except ValueError as error:
        return jsonify({'error': error}), 500

    db.session.commit()
    return jsonify(run.digest())


@app.route('/api/run/<run_id>/restart', methods=['POST'])
@auth
def restart_run(run_id):
    run = Run.query.filter_by(id=run_id).first_or_404()
    try:
        details = _unify_json_output(run.details)
        job_name = details.get('a01.reserved.jobname', None) if details else None
        clean_up_jobs(run_id=str(run.id), job_name=job_name)

        settings = _unify_json_output(run.settings)
        create_controller_job(run_id=str(run.id),
                              live=settings['a01.reserved.livemode'] == str(True),
                              image=settings['a01.reserved.imagename'],
                              agentver=settings['a01.reserved.agentver'])

    except (ValueError, KeyError) as error:
        return jsonify({'error', error})

    return jsonify(run.digest())


@app.route('/api/run/<run_id>')
@auth
def get_run(run_id):
    run = Run.query.filter_by(id=run_id).first_or_404()
    return jsonify(run.digest())


@app.route('/api/run/<run_id>', methods=['DELETE'])
@auth
def delete_run(run_id):
    run = Run.query.filter_by(id=run_id).first()
    if run:
        details = _unify_json_output(run.details)
        job_name = details.get('a01.reserved.jobname', None) if details else None
        clean_up_jobs(run_id=str(run.id), job_name=job_name)

        db.session.delete(run)
        db.session.commit()
        return jsonify({'status': 'removed'})

    return jsonify({'status': 'no action'})


@app.route('/api/run/<run_id>/tasks')
@auth
def get_tasks(run_id):
    run = Run.query.filter_by(id=run_id).first()
    if not run:
        return jsonify({'error': f'run <{run_id}> is not found'}), 404

    return jsonify([t.digest() for t in run.tasks])

@app.route('/api/run/<run_id>/task', methods=['POST'])
@auth
def post_task(run_id):
    run = Run.query.filter_by(id=run_id).first()
    if not run:
        return jsonify({'error': f'run <{run_id}> is not found'}), 404

    task = Task()
    task.load(request.json)
    run.tasks.append(task)
    db.session.add(task)
    db.session.commit()

    return jsonify(task.digest())


@app.route('/api/task/<task_id>', methods=['POST'])
@auth
def update_task(task_id):
    task = Task.query.filter_by(id=task_id).first_or_404()
    try:
        task.update(request.json)
    except ValueError as error:
        return jsonify({'error': error}), 500

    db.session.commit()
    return jsonify(task.digest())


@app.route('/api/task/<task_id>', methods=['GET'])
@auth
def get_task(task_id):
    task = Task.query.filter_by(id=task_id).first()
    if not task:
        return jsonify({'error': f'task <{task_id}> is not found'}), 404

    return jsonify(task.digest())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
