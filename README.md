# Boxer

![Boxer Logo](boxer-logo.png)

Boxer is a HackTheBox alike panel for managing boxes (VMs).

Have you or your team wanted a private HackTheBox platform to host your own boxes? Boxer was created just to fulfill this need! Within the HTB team, we wanted a private platform with the ease of starting up, shutting down and reseting machines exactly like in HackTheBox. Many weeks later, here comes the Boxer!

---

# Technologies

* Virtualization hypervisor is QEMU-KVM
* Virtualization API is libvirt
* Docker for containers and docker-compose to manage them
* Redis used to handle delayed VM shutdowns / resets with the option to cancel them
* Python dependencies managed by `pipenv`
* Web panel built with Django

# Run & Build

Everything you need to do is to pull images and run the containers!

```bash
# Clone the repository
git clone https://github.com/mrblacyk/Boxer.git

# Enter the repo
cd Boxer

# To prepare the host (ubuntu/debian for now is only supported!)
bash prepare_host.sh

# If you want to use docker hub image
docker-compose -f docker-compose-nobuild.yml up -d

# If you want to build the image yourself
# docker-compuse up -d --build

# Good to issue to resolve potential problems
chown -R www-data:www-data db/ uploads/
```

# Docker Hub

Now, there is available a docker image available from Docker Hub. Check it out [here](https://hub.docker.com/r/mrbl4cyk/boxer).

# Contributions

You are more than welcomed to contribute! I am already aware that there are some mistakes like typos or a bit sketchy logic but I lack time to even fix them :(

If you want to develop and install the application directly on the host, for now you are dependant on your knowledge and common sense. I will create some instruction on how to contribute when I will have more time.


# Credits

* @sn0w0tter for a sticky name
