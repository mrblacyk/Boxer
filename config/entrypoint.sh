#!/bin/bash

cd /var/www/django_app
pipenv run ./manage.py migrate --noinput
pipenv run ./manage.py collectstatic --noinput
chown -R www-data:www-data /var/www/django_app
chmod 777 /var/run/libvirt/libvirt-sock
apache2ctl -D FOREGROUND & pipenv run celery worker --app=panel.tasks
