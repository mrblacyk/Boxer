from django import forms
from django_summernote.widgets import SummernoteWidget
from socket import if_nameindex
from netaddr import IPAddress, IPNetwork
from netaddr.core import AddrFormatError
from subprocess import PIPE, run as s_run
from re import search as search_regex
from random import randrange
from .models import VirtualMachine


def callCmd(command):
    """ Returns stdout, stderr and returncode"""
    if not isinstance(command, list):
        raise Exception("Command has to be a list")
    cmd = s_run(
        command, stdout=PIPE, stderr=PIPE
    )
    return cmd.stdout.decode(), cmd.stderr.decode(), cmd.returncode


class UploadFileForm(forms.Form):
    name = forms.CharField(max_length=255, label="VM Name")
    file = forms.FileField()

    def clean(self):
        self.cleaned_data["name"] = self.cleaned_data["name"].strip()
        if len(self.cleaned_data["name"].split()) > 1:
            self.add_error("name", "Machine name has to be one word")
        elif VirtualMachine.objects.filter(name=self.cleaned_data["name"]):
            self.add_error("name", "Machine name is already taken")


class MailComposeForm(forms.Form):
    receiver = forms.CharField(max_length=255)
    subject = forms.CharField(max_length=255)
    content = forms.CharField(widget=SummernoteWidget())


class NewsForm(forms.Form):
    subject = forms.CharField(max_length=255)
    content = forms.CharField(widget=SummernoteWidget())


class DeployVMForm(forms.Form):
    name = forms.CharField(
        max_length=255, label="VM Name",
        help_text="Has to be unique and one word"
    )
    level = forms.ChoiceField(
        label="VM Level",
        choices=[("Easy", "Easy"), ("Medium", "Medium"),
                 ("Hard", "Hard"), ("Insane", "Insane")]
    )
    disk_location = forms.CharField(
        max_length=255, label="Disk location",
        help_text="Do not escape spaces or any characters"
    )
    vcpu = forms.IntegerField(
        label="Number of vCPUs", initial=1, min_value=1, max_value=4
    )
    memory = forms.IntegerField(
        label="Memory in MiB", initial=512, min_value=128, max_value=4096
    )
    mac_address = forms.CharField(
        min_length=17, max_length=17, label="Overwrite mac address",
        help_text="Do <b>NOT</b> fill this field to assign random mac address",
        required=False
    )
    network = forms.ChoiceField(label="Virsh Network")

    user_flag = forms.CharField(
        min_length=32, max_length=32, label="User flag",
        help_text="32 characters long flag, for instance md5 hash"
    )

    root_flag = forms.CharField(
        min_length=32, max_length=32, label="Root flag",
        help_text="32 characters long flag, for instance md5 hash"
    )

    def __init__(self, *args, **kwargs):
        nonexist = ("non-exising", "Select..")
        if 'networks' in kwargs.keys():
            networks = []
            networks_tmp = [x for x in kwargs.pop('networks') if len(x) == 4]
            for a, b, c, d in networks_tmp:
                networks.append([a, " | ".join([
                    "Name: " + a,
                    b,
                    "Autostart: " + c,
                    "Running: " + d
                ])])
            networks.append(nonexist)
        else:
            networks = [nonexist, ]
        super().__init__(*args, **kwargs)
        self.fields["network"].choices = networks
        self.fields["network"].initial = nonexist

    def clean(self):
        self.cleaned_data = super().clean()

        cmd_stdout, cmd_stderr, cmd_code = callCmd(
            ["qemu-img", "info", self.cleaned_data["disk_location"]]
        )

        if cmd_code:
            self.add_error(
                'disk_location',
                "STDOUT: " + cmd_stdout + "\nSTDERR: " + cmd_stderr
            )
        else:
            self.cleaned_data["disk_type"] = search_regex(
                "(?<=file format:\s)(.*)", cmd_stdout).group(0)

        if not self.cleaned_data.get("mac_address", None):
            # Generate random mac address
            self.cleaned_data["mac_address"] = ":".join(
                ['%02x' % randrange(256) for _ in range(6)])
        elif not search_regex(
            '^([0-9a-fA-F][0-9a-fA-F]:){5}([0-9a-fA-F][0-9a-fA-F])$',
                self.cleaned_data["mac_address"]):
            self.add_error('mac_address', "Invalid mac address")

        if self.cleaned_data["network"] == "non-exising":
            self.add_error('network', "Invalid network")

        self.cleaned_data["name"] = self.cleaned_data["name"].strip()
        if len(self.cleaned_data["name"].split()) > 1:
            self.add_error("name", "Machine name has to be one word")
        elif VirtualMachine.objects.filter(name=self.cleaned_data["name"]):
            self.add_error("name", "Machine name is already taken")

        if self.cleaned_data["user_flag"] == self.cleaned_data["root_flag"]:
            self.add_error("user_flag", "Flags cannot be the same")
            self.add_error("root_flag", "Flags cannot be the same")


class NatForm(forms.Form):

    network_name = forms.CharField(max_length=255, label="Network name")
    bridge_name = forms.CharField(max_length=255, label="Bridge name")
    ip_network = forms.CharField(max_length=255, label="Network CIDR")
    host_ip = forms.CharField(
        max_length=255, label="Host assigned IP in new network"
    )
    dhcp_start = forms.CharField(max_length=255, label="DHCP starting IP")
    dhcp_end = forms.CharField(max_length=255, label="DHCP ending IP")
    interface = forms.ChoiceField(label="Gateway interface")

    def __init__(self, *args, **kwargs):
        nonexist = ("non-exising", "Select..")
        if 'interfaces' in kwargs.keys():
            interfaces = kwargs.pop('interfaces')
            interfaces.append(nonexist)
        else:
            interfaces = []
        super().__init__(*args, **kwargs)
        self.fields['interface'].choices = interfaces
        self.fields['interface'].initial = nonexist
        self.fields['network_name'].initial = "alpha-nat"
        self.fields['bridge_name'].initial = "vibr1000"
        self.fields['ip_network'].initial = "10.10.10.10/24"
        self.fields['host_ip'].initial = "10.10.10.1"
        self.fields['dhcp_start'].initial = "10.10.10.10"
        self.fields['dhcp_end'].initial = "10.10.10.254"

    def clean(self):
        self.cleaned_data = super().clean()

        interface = self.cleaned_data.get("interface")

        ip_network = self.cleaned_data.get("ip_network")
        host_ip = self.cleaned_data.get("host_ip")
        dhcp_start = self.cleaned_data.get("dhcp_start")
        dhcp_end = self.cleaned_data.get("dhcp_end")

        int_check = False

        try:
            if int(interface):
                int_check = True
        except ValueError:
            self.add_error(
                'interface', "Interface does not seem to exist in the OS."
            )

        if int_check \
                and int(interface) not in range(1, len(if_nameindex()) + 1):
            self.add_error(
                'interface', "Interface does not seem to exist in the OS."
            )

        try:
            ip_network_clean = IPNetwork(ip_network)
        except AddrFormatError:
            self.add_error(
                'ip_network', "This is not a valid IP network range."
            )

        try:
            host_ip_clean = IPAddress(host_ip)
        except AddrFormatError:
            self.add_error('host_ip', "This is not a valid IP address.")

        try:
            dhcp_start_clean = IPAddress(dhcp_start)
        except AddrFormatError:
            self.add_error('dhcp_start', "This is not a valid IP address.")

        try:
            dhcp_end_clean = IPAddress(dhcp_end)
        except AddrFormatError:
            self.add_error('dhcp_end', "This is not a valid IP address.")

        if dhcp_start_clean not in ip_network_clean:
            self.add_error(
                'dhcp_start', "This IP does not belong to given network."
            )

        if dhcp_end_clean not in ip_network_clean:
            self.add_error(
                'dhcp_end', "This IP does not belong to given network."
            )

        if dhcp_end_clean <= dhcp_start_clean:
            self.add_error(
                'dhcp_end', "This IP cannot be below the starting one."
            )

        if dhcp_start_clean in [
                ip_network_clean.network, ip_network_clean.broadcast,
                host_ip_clean]:
            self.add_error(
                'dhcp_start',
                (
                    "This IP cannot be a network or "
                    "broadcast address of the network "
                    "as well as host assigned IP."
                )
            )

        if dhcp_end_clean in [
                ip_network_clean.network, ip_network_clean.broadcast,
                host_ip_clean]:
            self.add_error(
                'dhcp_end',
                (
                    "This IP cannot be a network or "
                    "broadcast address of the network "
                    "as well as host assigned IP."
                )
            )
