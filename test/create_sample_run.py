import sys
import json
import logging
import datetime

import requests

try:
    _, store_host, image_ver = sys.argv
except ValueError:
    print('Incorrect input. Expect inputs: create_sample_run.py <store host> <image ver>')
    sys.exit(1)

print('Store host: {}'.format(store_host))
logging.basicConfig(level=logging.DEBUG)

image = f'a01reg.azurecr.io/a01droid:{image_ver}-alpine-python3.6'
with open('manifest.json') as f:
    manifest = json.load(f)

print('Create a new test run')
run_id = requests.post(f'http://{store_host}/run', json={
    'name': f'Automation run sample: {datetime.datetime.now()}',
    'settings': {
        'image': image
    },
    'details': {
        'repo': 'https://www.github.com/Azure/azuer-cli',
        'branch': 'KnackFinal'
    }
}).json()['id']

print('Sample 2 tests to schedule individually')
for each in manifest[:2]:
    task = {
        'name': f'Automation task sample: {each["method"]}',
        'annotation': image,
        'settings': {
            'path': each['path'],
            'module': each['module'],
            'method': each['method'],
            'class': each['class'],
            'type': each['type'],
            'live': False
        }
    }
    resp = requests.post(f'http://{store_host}/run/{run_id}/task', json=task)
    resp.raise_for_status()

print('Sample next 18 tests to schedule in batch')

requests.post(f'http://{store_host}/run/{run_id}/tasks', json=[{
    'name': f'Automation task: {each["path"]}',
    'annotation': image,
    'settings': {
        'path': each['path'],
        'module': each['module'],
        'method': each['method'],
        'class': each['class'],
        'type': each['type'],
        'live': False
    }
} for each in manifest[2:64]]).raise_for_status()
