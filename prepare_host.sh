#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

echo "This script only works on ubuntu/debian. Starting in 10 seconds.."
sleep 5
echo "5 seconds left.."
sleep 5

# Update sources
apt-get update -y

# Install libvirt and required components
apt-get install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils

# Install docker and docker-compose
apt-get install -y docker.io docker-compose

# Add www-data to libvirt
usermod -a -G libvirt www-data
