from collections import defaultdict
from datetime import datetime, timedelta
from tabulate import tabulate

from templates.template import Template

class TemplateCLI(Template):
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
                if run['details'].get('a01.reserved.product', None) == 'azurecli':
                    test_name = task['settings']['classifier']['identifier']
                    if test_name.startswith('azure.cli.command_modules'):
                        module_name = test_name.split('.')[3]
                    else:
                        module_name = 'CORE'
                else:
                    module_name = None

                failure.append(
                    (task['id'],
                     task['name'].rsplit('.')[-1],
                     task['status'],
                     task['result'],
                     (task.get('result_details') or dict()).get('duration'),
                     module_name))

        status_summary = ' | '.join([f'{status_name}: {count}' for status_name, count in statuses.items()])
        result_summary = ' | '.join([f'{result or "Not run"}: {count}' for result, count in results.items()])

        creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)

        summaries = [('Id', run['id']),
                     ('Creation', str(creation) + ' PST'),
                     ('Creator', run['details'].get('a01.reserved.creator', 'N/A')),
                     ('Remark', run['settings'].get('a01.reserved.remark', 'N/A')),
                     ('Live', run['settings'].get('a01.reserved.livemode')),
                     ('Task', status_summary),
                     ('Image', run['settings'].get('a01.reserved.imagename', 'N/A')),
                     ('Result', result_summary)]

        return {
            'summaries': tabulate(summaries, tablefmt="html"),
            'failures': tabulate(failure,
                                 headers=("id", "name", "status", "result", "duration(ms)", "module"), tablefmt="html"),
            'runID': run['id']
        }

    def get_subject(self, run: dict, tasks: dict) -> str:
        creation = datetime.strptime(run['creation'], '%Y-%m-%dT%H:%M:%SZ') - timedelta(hours=8)

        results = defaultdict(lambda: 0)

        for task in tasks:
            result = task['result']
            results[result] = results[result] + 1

        result_summary = ' | '.join([f'{result or "Not run"}: {count}' for result, count in results.items()])

        return f'Azure CLI Automation Run {str(creation)} - {result_summary}.'
