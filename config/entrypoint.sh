#!/bin/bash

cd /var/www/django_app
pipenv run ./manage.py migrate --noinput
pipenv run ./manage.py collectstatic --noinput
chown -R www-data:www-data /var/www/django_app
apache2ctl -D FOREGROUND
