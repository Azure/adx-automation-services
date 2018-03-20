from typing import List
from collections import defaultdict
from datetime import datetime, timedelta
from tabulate import tabulate

from app.templates.template import Template


class TemplateGeneric(Template):
    def get_context(self, run: dict, tasks: List[dict]) -> dict:
        statuses = defaultdict(lambda: 0)
        results = defaultdict(lambda: 0)

        failure = []

        for task in tasks:
            status = task['status']
            result = task['result']

            statuses[status] = statuses[status] + 1
            results[result] = results[result] + 1

            if result != 'Passed':
                failure.append(
                    (task['id'],
                     task['settings']['classifier']['identifier'],
                     task['status'],
                     task['result'],
                     (task.get('result_details') or dict()).get('duration')))

        status_summary = ' | '.join([f'{status_name}: {count}' for status_name, count in statuses.items()])
        result_summary = ' | '.join([f'{result or "Not run"}: {count}' for result, count in results.items()])

        creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)

        summaries = [('Product', run['details'].get('a01.reserved.product', 'N/A')),
                     ('Run ID', run['id']),
                     ('Creation', str(creation) + ' PST'),
                     ('Creator', run['details'].get('a01.reserved.creator', 'N/A')),
                     ('Remark', run['settings'].get('a01.reserved.remark', 'N/A')),
                     ('Live', run['settings'].get('a01.reserved.livemode')),
                     ('Mode', run['settings'].get('a01.reserved.testmode', 'N/A')),
                     ('Image', run['settings'].get('a01.reserved.imagename', 'N/A')),
                     ('Query', run['settings'].get('a01.reserved.testquery', 'N/A')),
                     ('Kubernetes secret', run['settings'].get('a01.reserved.secret', 'N/A')),
                     ('Based on other run failures', run['settings'].get('a01.reserved.fromrunfailure', 'N/A')),
                     ('A01 agent version', run['settings'].get('a01.reserved.agentver', 'N/A')),
                     ('A01 client version', run['details'].get('a01.reserved.client', 'N/A')),
                     ('Task', status_summary),
                     ('Result', result_summary)]

        return {
            'summaries': tabulate(summaries, tablefmt="html"),
            'failures': tabulate(failure,
                                 headers=("id", "name", "status", "result", "duration(ms)"), tablefmt="html"),
            'runID': run['id']
        }

    def get_subject(self, run: dict, tasks: List[dict]) -> str:
        creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)

        results = defaultdict(lambda: 0)

        for task in tasks:
            result = task['result']
            results[result] = results[result] + 1

        result_summary = ' | '.join([f'{result or "Not run"}: {count}' for result, count in results.items()])

        product = run['details'].get('a01.reserved.product', 'A01')

        return f'{product} Automation Run {str(creation)} - {result_summary}.'
