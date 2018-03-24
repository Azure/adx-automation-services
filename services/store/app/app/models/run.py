from datetime import datetime

from .shared import db, str_to_json, json_to_str


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
            'details': str_to_json(self.details),
            'settings': str_to_json(self.settings)
        }

        return result

    def update(self, data):
        """Update this run. Settings, Creation, and ID are readonly."""
        if 'name' in data:
            self.name = data['name']
        if 'owner' in data:
            self.owner = data['owner']
        if 'details' in data:
            self.details = json_to_str(data['details'])
        if 'status' in data:
            self.status = data['status']

    @staticmethod
    def create(data: dict) -> 'Run':
        """Create a run data from a json object. This is used to parse user input."""
        result = Run()
        result.update(data)
        result.settings = json_to_str(data.get('settings', None))
        result.creation = datetime.utcnow()
        return result
