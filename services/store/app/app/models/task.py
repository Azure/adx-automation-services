from .shared import db, str_to_json, json_to_str


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

    def digest(self) -> dict:
        result = {
            'id': self.id,
            'name': self.name,
            'settings': str_to_json(self.settings),
            'annotation': self.annotation,
            'status': self.status,
            'duration': self.duration,
            'result': self.result,
            'result_details': str_to_json(self.result_details),
            'run_id': self.run_id
        }

        return result

    def load(self, data):
        """Load data from a json object. This is used to parse user input."""
        self.name = data['name']
        self.settings = json_to_str(data.get('settings', None))
        self.annotation = data.get('annotation', None)
        self.status = data.get('status', 'initialized')
        self.duration = data.get('duration', None)
        self.result = data.get('result', None)
        self.result_details = json_to_str(data.get('result_details', None))

    def update(self, data):
        """Update this task."""
        if 'name' in data:
            self.name = data['name']
        if 'settings' in data:
            self.settings = json_to_str(data['settings'])
        if 'annotation' in data:
            self.annotation = data['annotation']
        if 'status' in data:
            self.status = data['status']
        if 'duration' in data:
            self.duration = data['duration']
        if 'result' in data:
            self.result = data['result']
        if 'result_details' in data:
            self.result_details = json_to_str(data['result_details'])
