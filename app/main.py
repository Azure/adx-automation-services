"""
A01Store service accept automation tests scheduled by the Control (or user)
and store it in a database. The test tasks are available to the automation
droids. The A01Store plays a passive role in the producer-consumer
relationship meaning the driver is the consumer (A01Droid).
"""
import os
import datetime
import json

from sqlalchemy.exc import IntegrityError, DBAPIError
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)  # pylint: disable=invalid-name
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['A01_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)  # pylint: disable=invalid-name
migrate = Migrate(app, db)


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

    def digest(self):
        """Return an serializable object for REST API"""
        result = {
            'id': self.id,
            'name': self.name,
            'creation': self.creation.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'details': _unify_json_output(self.details),
            'settings': _unify_json_output(self.settings)
        }

        return result

    def load(self, data):
        """Load data from a json object. This is used to parse user input."""
        self.name = data['name']
        self.details = _unify_json_input(data.get('details', None))
        self.settings = _unify_json_input(data.get('settings', None))

        if not self.creation:
            self.creation = datetime.datetime.utcnow()


class Task(db.Model):
    # unique id
    id = db.Column(db.Integer, primary_key=True)
    # display name for the test task
    name = db.Column(db.String)
    # settings of the task. the settings can be saved in JSON or any other format defined by the application
    settings = db.Column(db.String)
    # annotation of the task, used to fast query tasks under a run. its form is defined by the application.
    annotation = db.Column(db.String)
    # status of the task: initialized, scheduled, completed, and ignored
    status = db.Column(db.String)
    # the duration of the test run in milliseconds
    duration = db.Column(db.Integer)
    # result of the test: passed, failed, and error
    result = db.Column(db.String)
    # logging data of the test run
    log = db.Column(db.String)
    # details of the task result. the value can be saved in JSON or any other format defined by the application
    result_details = db.Column(db.String)

    # relationship
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), nullable=False)
    run = db.relationship('Run', backref=db.backref('tasks', cascade='all, delete-orphan', lazy=True))

    def digest(self):
        result = {
            'id': self.id,
            'name': self.name,
            'settings': _unify_json_output(self.settings),
            'annotation': self.annotation,
            'status': self.status,
            'duration': self.duration,
            'result': self.result,
            'result_details': _unify_json_output(self.result_details)
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

    def patch(self, data):
        for key, value in data.items():
            if key == 'name' or key == 'id' or key == 'annotation':
                raise ValueError('Property name, id, and annotation are immutable.')
            if hasattr(self, key):
                if key == 'settings' or key == 'result_details':
                    setattr(self, key, _unify_json_input(value))
                else:
                    setattr(self, key, value)


@app.route('/healthy')
def get_healthy():
    """Healthy status endpoint"""
    return jsonify({'status': 'healthy', 'time': datetime.datetime.utcnow()})


@app.route('/runs')
def get_runs():
    """List all the runs"""
    return jsonify([r.digest() for r in Run.query.all()])


@app.route('/run', methods=['POST'])
def post_run():
    run = Run()
    run.load(request.json)

    db.session.add(run)
    db.session.commit()

    return jsonify(run.digest())


@app.route('/run/<run_id>')
def get_run(run_id):
    run = Run.query.filter_by(id=run_id).first_or_404()
    return jsonify(run.digest())


@app.route('/run/<run_id>', methods=['DELETE'])
def delete_run(run_id):
    run = Run.query.filter_by(id=run_id).first()
    if run:
        db.session.delete(run)
        db.session.commit()
        return jsonify({'status': 'removed'})

    return jsonify({'status': 'no action'})


@app.route('/run/<run_id>/tasks')
def get_tasks(run_id):
    run = Run.query.filter_by(id=run_id).first()
    if not run:
        return jsonify({'error': f'run <{run_id}> is not found'}), 404

    return jsonify([t.digest() for t in run.tasks])


@app.route('/run/<run_id>/task', methods=['POST'])
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


@app.route('/run/<run_id>/tasks', methods=['POST'])
def post_tasks(run_id):
    run = Run.query.filter_by(id=run_id).first()
    if not run:
        return jsonify({'error': f'run <{run_id}> is not found'}), 404

    for each in request.json:
        task = Task()
        task.load(each)
        run.tasks.append(task)
        db.session.add(task)

    db.session.commit()
    return jsonify({'status': 'success', 'added': len(request.json)})


@app.route('/task/<task_id>')
def get_task(task_id):
    task = Task.query.filter_by(id=task_id).first()
    if not task:
        return jsonify({'error': f'task <{task_id}> is not found'}), 404

    return jsonify(task.digest())


@app.route('/task/<task_id>', methods=['PATCH'])
def patch_task(task_id):
    task = Task.query.filter_by(id=task_id).first()
    if not task:
        return jsonify({'error': f'task <{task_id}> is not found'}), 404

    try:
        task.patch(request.json)
    except ValueError as error:
        return jsonify({'error': error})

    db.session.commit()
    return jsonify(task.digest())


@app.route('/run/<run_id>/checkout', methods=['POST'])
def checkout_task(run_id):
    run = Run.query.filter_by(id=run_id).first()
    if not run:
        return jsonify({'error': f'run <{run_id}> is not found'}), 404

    task = Task.query.filter_by(run_id=run.id, status='initialized').with_for_update(nowait=True).first()
    if not task:
        return jsonify({'message': 'all tasks are scheduled'}), 204

    task.status = 'scheduled'
    try:
        db.session.commit()
    except (IntegrityError, DBAPIError):
        return jsonify({'error': f'failed to update a task due to row lock. please retry.'}), 500

    return jsonify(task.digest())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
