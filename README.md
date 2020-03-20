# Boxer

![Boxer Logo](boxer-logo.png)

Boxer is a HackTheBox alike panel for managing boxes (VMs).

More detailed instruction and gifs will be produced upon completing MVP (closing all issues), and most probably creating `Dockerfile` for this project as well as a detailed blog post on setup.

---

Dependencies are managed by `pipenv`

# Run & Build

Everything is you need to do is to build the image and run the containers.

```bash
git clone https://github.com/mrblacyk/Boxer.git
cd Boxer
# apt install docker.io docker docker-compose  # if you don't have already
docker-compuse up -d --build
```

Known "bug" is that you have to add user `www-data` to `libvirt` group. Otherwise, there is permission issue.

# Docker Hub (outdated a bit)

Now, there is available a docker image available from Docker Hub. Check it out [here](https://hub.docker.com/r/mrbl4cyk/boxer).

If you want to develop or install the application directly on the host, use the instructions below.


# Credits

* @sn0w0tter for a sticky name
