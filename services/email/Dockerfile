FROM tiangolo/uwsgi-nginx-flask:python3.6-alpine3.7

RUN apk add --update --no-cache g++ gcc libxslt-dev

COPY ./app /app
RUN pip install -r /app/requirements.txt
