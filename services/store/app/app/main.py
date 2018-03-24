"""
A01Store service accept automation tests scheduled by the Control (or user)
and store it in a database. The test tasks are available to the automation
droids. The A01Store plays a passive role in the producer-consumer
relationship meaning the driver is the consumer (A01Droid).
"""
from datetime import datetime
import logging
import os
from packaging import version

import coloredlogs
from flask import Flask, jsonify, request
from flask_migrate import Migrate

from .models import Run, Task, db, str_to_json
from .cluster import clean_up_jobs, create_controller_job, get_current_namespace
from .authentication import auth

coloredlogs.install(level=logging.INFO)

app = Flask(__name__)  # pylint: disable=invalid-name
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['A01_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)  # pylint: disable=invalid-name


@app.route('/api/health')
@app.route('/api/healthy')
def get_healthy():
    """Healthy status endpoint"""
    return jsonify({'status': 'healthy', 'time': datetime.utcnow()})


@app.route('/api/metadata')
def get_metadata():
    return jsonify({'kubernete': {'namespace': get_current_namespace()}})


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

    settings = str_to_json(run.settings)
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
        details = str_to_json(run.details)
        job_name = details.get('a01.reserved.jobname', None) if details else None
        clean_up_jobs(run_id=str(run.id), job_name=job_name)

        settings = str_to_json(run.settings)
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
        details = str_to_json(run.details)
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
