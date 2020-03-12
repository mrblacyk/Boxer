FROM ubuntu:19.10

ENV DJANGO_PRODUCTION DJANGO_PRODUCTION
ENV DJANGO_SECRET_KEY 'CHANGE_ME_FOR_PRODUCTION_USAGE!!!'

ADD django_app /var/www/django_app
COPY config/django-apache2.conf /etc/apache2/sites-available/boxer.conf
COPY config/entrypoint.sh /entrypoint.sh
WORKDIR "/var/www/django_app"

RUN apt-get update -y && \
 apt-get install -y --no-install-recommends python3 python3-pip python3-libvirt pipenv apache2 libapache2-mod-wsgi-py3 && \
 chmod +x /entrypoint.sh && \
 rm db.sqlite3 || true && \
 pip3 install setuptools && \
 pipenv --site-packages install --system && \
 sed -ie "s/PIPENV_VENV/$(pipenv --venv | sed 's/\//\\\//g')/g" /etc/apache2/sites-available/boxer.conf && \
 sed -ie "s/BOXER_PATH/$(pwd | sed 's/\//\\\//g')/g" /etc/apache2/sites-available/boxer.conf && \
 a2dissite default-ssl 000-default && \
 a2ensite boxer

# ENTRYPOINT /entrypoint.sh

