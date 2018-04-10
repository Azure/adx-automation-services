FROM python:3.6-alpine3.7

COPY ./app/requirements.txt /app/requirements.txt
RUN pip install -U pip && pip install -r /app/requirements.txt

COPY ./app /app
CMD python /app/jobcleaner.py