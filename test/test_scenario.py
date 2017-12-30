import json
import logging
import requests

logging.basicConfig(level=logging.DEBUG)

host = 'http://localhost:5000'
image = 'a01reg.azurecr.io/az-droid:001'
with open('manifest.json') as f:
    manifest = json.load(f)

print('Create a new test run')
run_id = requests.post(f'{host}/run', json={
    'name': 'Automation run example',
    'settings': {
        'image': image,
        'live': False,
        'repo': 'https://www.github.com/Azure/azuer-cli',
        'branch': 'KnackFinal'
    },
    'details': {
        'repo': 'https://www.github.com/Azure/azuer-cli',
        'branch': 'KnackFinal'
    }
}).json()['id']

print('Sample 10 tests to schedule individually')
for each in manifest[:10]:
    task = {
        'name': f'Automation task: {each["path"]}',
        'annotation': image,
        'settings': {
            'path': each['path'],
            'module': each['module'],
            'live': False
        }
    }
    resp = requests.post(f'{host}/run/{run_id}/task', json=task)
    resp.raise_for_status()

print('Sample next 10 tests to schedule in batch')

requests.post(f'{host}/run/{run_id}/tasks', json=[{
    'name': f'Automation task: {each["path"]}',
    'annotation': image,
    'settings': {
        'path': each['path'],
        'module': each['module'],
        'live': False
    }
} for each in manifest[10:20]]).raise_for_status()
