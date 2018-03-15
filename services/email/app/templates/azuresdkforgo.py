from collections import defaultdict
from datetime import datetime, timedelta
from tabulate import tabulate
from templates.template import Template

class TemplateGo(Template):
    def get_context(self, run: dict, tasks: dict) -> dict:
        statuses = defaultdict(lambda: 0)
        results = defaultdict(lambda: 0)

        failure = []

        for task in tasks:
            status = task['status']
            result = task['result']

            statuses[status] = statuses[status] + 1
            results[result] = results[result] + 1

            if result != 'Passed':
                identifier = task['settings']['classifier']['identifier'].split('/')
                service = identifier[0]
                test = identifier[1]

                failure.append(
                    (task['id'],
                     service,
                     test,
                     task['status'],
                     task['result'],
                     (task.get('result_details') or dict()).get('duration')))

        status_summary = ' | '.join([f'{status_name}: {count}' for status_name, count in statuses.items()])
        result_summary = ' | '.join([f'{result or "Not run"}: {count}' for result, count in results.items()])

        creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)

        location = run['settings'].get('a01.reserved.testmode', 'Prod')
        if location == 'centraluseuap':
            location = 'Canary'

        summaries = [('Run ID', run['id']),
                     ('Creation', str(creation) + ' PST'),
                     ('Owner', run['details'].get('a01.reserved.creator', 'N/A')),
                     ('Remark', run['settings'].get('a01.reserved.remark', 'N/A')),
                     ('Azure location', location),
                     ('Tasks', status_summary),
                     ('Docker image', run['settings'].get('a01.reserved.imagename', 'N/A')),
                     ('Tests results', result_summary)]

        return {
            'summaries': tabulate(summaries, tablefmt="html"),
            'failures': tabulate(failure, headers=(
                "Task ID", "Service", "Test", "Status", "Result", "Duration (ms)"), tablefmt="html"),
            'runID': run['id']
        }

    def get_subject(self, run: dict, tasks: dict) -> str:
        creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)

        results = defaultdict(lambda: 0)

        for task in tasks:
            result = task['result']
            results[result] = results[result] + 1

        result_summary = ' | '.join([f'{result or "Not run"}: {count}' for result, count in results.items()])

        return f'Azure SDK for Go Samples Automation Run {str(creation)} - {result_summary}.'
