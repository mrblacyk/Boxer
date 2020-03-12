#!/bin/bash

cd /var/www/django_app
pipenv run ./manage.py migrate
apache2ctl -D FOREGROUND