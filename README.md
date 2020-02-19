# AP-HTB

AlphaPwners HTB alike panel

Dependencies are managed by `pipenv`

# Dependencies

Install packages:

```bash
apt-get install pkg-config libvirt-dev
```

Install KVM:

```bash
apt-get install qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager
```

Install pipenv:

```bash
pipenv --site-packages install
```

# Configure Django

```bash
pipenv run python manage.py migrate
pipenv run python manage.py createsuperuser
```

# Run

```bash
pipenv run python manage.py runserver
```

