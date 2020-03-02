# Boxer

Boxer is a HackTheBox alike panel for managing boxes (VMs).

More detailed instruction and gifs will be produced upon completing MVP (closing all issues), and most probably creating `Dockerfile` for this project as well as a detailed blog post on setup.

---

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
```

# Run

```bash
pipenv run python manage.py runserver
```

