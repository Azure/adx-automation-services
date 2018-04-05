FROM python:alpine3.6

RUN apk add --update --no-cache g++ gcc libxslt-dev

COPY ./app /app
RUN pip install -r /app/requirements.txt
