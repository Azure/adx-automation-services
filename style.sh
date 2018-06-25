#!/usr/bin/env bash

# Check the code style

echo ""
echo "Check store service"
pipenv run pylint services/store/app/app

echo ""
echo "Check email service"
pipenv run pylint services/email/app/app

echo ""
echo "Check job cleaner service"
find services/jobcleaner/app -name '*.py' | xargs pipenv run pylint
