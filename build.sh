#!/usr/bin/env bash

version=$(cat ./version)
docker build -t a01store:$version .
