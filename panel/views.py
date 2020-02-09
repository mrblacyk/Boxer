from django.shortcuts import redirect, render as render_django
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from time import sleep
from .models import *
from .forms import *
from datetime import datetime, timedelta
from socket import if_nameindex, if_indextoname
from netaddr import IPNetwork
from subprocess import PIPE, run as s_run
from tempfile import NamedTemporaryFile
from netaddr import IPAddress
from _thread import start_new_thread

import json
from os import path, getcwd

# Create your views here.


def render(*args, **kwargs):
    user = None
    for index, argument in enumerate(args):
        if index == 0:
            user = argument.user
            break

    unread_count = Messages.objects.filter(receiver=user, read=False).count()
    if unread_count:
        for index, argument in enumerate(args):
            if index == 2:
                argument.update({'unread': unread_count})
                break

    return render_django(*args, **kwargs)


def callCmd(command):
    """ Returns stdout, stderr and returncode"""
    if not isinstance(command, str):
        raise Exception("Command has to be a string")
    cmd = s_run(
        command.split(), stdout=PIPE, stderr=PIPE
    )
    return cmd.stdout.decode(), cmd.stderr.decode(), cmd.returncode


@login_required
def statistics(request):
    context = {}

    return render(request, "panel/statistics.html", context)


def handle_uploaded_file(f, fname):
    with open('uploads/' + fname, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def send_upload_email(req_user, fname, floc):
    new_mail = Messages()
    new_mail.sender = req_user
    new_mail.receiver = req_user
    new_mail.subject = f"File upload details - {fname}"
    today = datetime.now()
    new_mail.content = f"""Hey!<br>
<br>
On <b>{today}</b> you have uploaded a file <b>{fname}</b>. It is available under location of:<br>
<br>
<b>{floc}</b>
<br><br>
--<br>
<br>
Thanks,<br>
SYSTEM
"""
    new_mail.created_at = datetime.now()
    new_mail.save()
    return True

@login_required
def file_upload(request):
    context = {}
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        context = {'form': form}
        file_name = request.POST['name'].replace(" ", "_") + "_" + str(datetime.now().microsecond) + "_" + str(request.FILES['file'])
        file_loc = path.abspath(getcwd()) + '/uploads/' + file_name
        if form.is_valid():
            handle_uploaded_file(request.FILES['file'], file_name)
            messages.success(request, "Successfully uploaded %s!<br>Check your mailbox for details." % file_name)
            send_upload_email(request.user, str(request.FILES['file']), file_loc)
            return redirect("/upload/")
        else:
            messages.warning(request, "Upload was not valid")
            return redirect("/upload/")
    else:
        form = UploadFileForm()
    context = {'form': form}
    return render(request, "panel/upload.html", context)


@login_required
def news(request):
    context = {}

    delta = datetime.now() - timedelta(days=31)

    results = News.objects.filter(
        created_at__gte=delta).order_by('-created_at')

    context.update({'news': results})

    return render(request, "panel/news.html", context)


@login_required
def start_machine(request, machine_id):
    # sd
    sleep(1)
    if request.method == "GET":
        vm_to_handle = VirtualMachine.objects.get(id=machine_id)
        cmd_stdout, cmd_stderr, cmd_code = callCmd(
            "sudo virsh list --all --name"
        )

        if not cmd_code:
            all_vms = cmd_stdout.strip().split()
        else:
            all_vms = []
        if vm_to_handle.name not in all_vms:
            return HttpResponse(status=400)

        cmd_stdout, cmd_stderr, cmd_code = callCmd(
            "sudo virsh list --state-running --name"
        )

        if not cmd_code:
            running_vms = cmd_stdout.strip().split()
        else:
            running_vms = []
        if vm_to_handle.name in running_vms:
            # Already started
            return HttpResponse(status=242)
        elif vm_to_handle.name in all_vms:
            cmd_stdout, cmd_stderr, cmd_code = callCmd(
                f"sudo virsh start {vm_to_handle.name}"
            )

            if not cmd_code:
                # Started
                return HttpResponse(status=241)
            else:
                return HttpResponse(status=400)
        
    return HttpResponse(status=400)


@login_required
def stop_machine(request, machine_id):
    sleep(1)
    if request.method == "GET":
        vm_to_handle = VirtualMachine.objects.get(id=machine_id)
        cmd_stdout, cmd_stderr, cmd_code = callCmd(
            "sudo virsh list --all --name"
        )

        if not cmd_code:
            all_vms = cmd_stdout.strip().split()
        else:
            all_vms = []
        if vm_to_handle.name not in all_vms:
            return HttpResponse(status=400)

        cmd_stdout, cmd_stderr, cmd_code = callCmd(
            "sudo virsh list --state-shutoff --name"
        )

        if not cmd_code:
            shutoff_vms = cmd_stdout.strip().split()
        else:
            shutoff_vms = []
        if vm_to_handle.name in shutoff_vms:
            # Already stopped
            return HttpResponse(status=252)

        elif vm_to_handle.name in all_vms:
            cmd_stdout, cmd_stderr, cmd_code = callCmd(
                f"sudo virsh shutdown {vm_to_handle.name}"
            )

            if not cmd_code:
                # Stopped
                return HttpResponse(status=251)
            else:
                print(cmd_stdout)
                print(cmd_stderr)
                return HttpResponse(status=400)
        
    return HttpResponse(status=400)


@login_required
def reset_machine(request, machine_id):
    sleep(1)
    if request.method == "GET":
        # Reset scheduled
        return HttpResponse(status=261)
        # Already scheduled reset
        return HttpResponse(status=262)
    return HttpResponse(status=400)


@login_required
def cancel_reset_machine(request, machine_id):
    sleep(1)
    if request.method == "GET":
        # Canceled
        return HttpResponse(status=271)
        # Already canceled
        return HttpResponse(status=272)
    return HttpResponse(status=400)


@login_required
def send_flag(request, machine_id):
    sleep(1)
    if request.method == "POST" and request.POST.get("flag"):
        vm = VirtualMachine.objects.filter(id=machine_id)
        if vm:
            if request.POST.get("flag") == vm[0].user_flag:
                vm[0].user_owned.add(request.user)
                return HttpResponse(status=281)
            elif request.POST.get("flag") == vm[0].root_flag:
                vm[0].root_owned.add(request.user)
                return HttpResponse(status=282)
    return HttpResponse(status=400)


@login_required
def mailbox_inbox(request):
    mailbox_messages = Messages.objects.filter(
        receiver=request.user, trash=False
    ).order_by('-created_at')
    mailbox_unread_count = len(mailbox_messages.filter(read=False))
    return render(request, "panel/mailbox_inbox.html", {
        "mailbox_messages": mailbox_messages,
        "mailbox_unread_count": mailbox_unread_count,
        "folder": "Inbox",
    })


@login_required
def mailbox_trash(request):
    mailbox_messages = Messages.objects.filter(
        receiver=request.user, trash=True
    ).order_by('-created_at')
    mailbox_unread_count = len(mailbox_messages.filter(read=False))
    return render(request, "panel/mailbox_inbox.html", {
        "mailbox_messages": mailbox_messages,
        "mailbox_unread_count": mailbox_unread_count,
        "folder": "Trash",
    })


@login_required
def mailbox_sent(request):
    mailbox_messages = Messages.objects.filter(
        sender=request.user,
    ).order_by('-created_at')
    mailbox_unread_count = len(mailbox_messages.filter(read=False))
    return render(request, "panel/mailbox_inbox.html", {
        "mailbox_messages": mailbox_messages,
        "mailbox_unread_count": mailbox_unread_count,
        "folder": "Sent",
    })


@login_required
def mailbox_read(request, mail_id):
    mailbox_message = Messages.objects.filter(id=mail_id)
    if not mailbox_message:
        return redirect("/mailbox/")
    else:
        mailbox_message = mailbox_message[0]
    if request.user not in [mailbox_message.sender, mailbox_message.receiver]:
        return redirect("/mailbox/")
    if not mailbox_message.read:
        mailbox_message.read = True
        mailbox_message.save()
    mailbox_messages = Messages.objects.filter(
        receiver=request.user, trash=False
    )
    mailbox_unread_count = len(mailbox_messages.filter(read=False))
    return render(request, "panel/mailbox_read.html", {
        "mailbox_message": mailbox_message,
        "mailbox_unread_count": mailbox_unread_count
    })


@login_required
def mailbox_compose(request):
    mailbox_messages = Messages.objects.filter(
        sender=request.user,
    )
    if request.method == "POST":
        form = MailComposeForm(request.POST)
        if form.is_valid():
            new_mail = Messages()
            new_mail.sender = User.objects.get(username=request.user)
            new_mail.receiver = User.objects.get(
                username=request.POST.get('receiver')
            )
            new_mail.subject = request.POST.get('subject')
            new_mail.content = request.POST.get('content')
            new_mail.created_at = datetime.now()
            new_mail.save()
            messages.info(request, "Message sent!")
        return redirect("/mailbox/compose/")

    mailbox_unread_count = len(mailbox_messages.filter(read=False))
    form = MailComposeForm()
    return render(request, "panel/mailbox_compose.html", {
        "mailbox_unread_count": mailbox_unread_count,
        'form': form,
    })


@login_required
def mailbox_user_query(request):
    if request.method == "GET" and request.GET.get("q"):
        response_data = []
        query = str(request.GET.get("q"))
        results = User.objects.filter(username__startswith=query)[:5]
        for result in results:
            tmp = {}
            tmp["value"] = result.id
            tmp["text"] = result.username
            response_data.append(tmp)
            del tmp
        return HttpResponse(
            json.dumps(response_data), content_type="application/json"
        )
    else:
        return redirect("/")


@login_required
def machines(request):

    context = {}
    context.update({'machines-state': {}})
    context.update({'machines': []})

    user_name = request.user.username.replace(" ", "").upper()

    # Running state

    cmd_stdout, cmd_stderr, cmd_code = callCmd(
        "sudo virsh list --all --state-running --name"
    )

    if cmd_code:
        messages.error(request, "Failed to retrieve running VMs")
    else:
        cmd_stdout = cmd_stdout.strip().split("\n")

    for vm_name in cmd_stdout:
        context['machines-state'][vm_name] = "RUNNING"

    # Stopped state
    cmd_stdout, cmd_stderr, cmd_code = callCmd(
        "sudo virsh list --all --state-shutoff --name"
    )

    if cmd_code:
        messages.error(request, "Failed to retrieve stopped VMs")
    else:
        cmd_stdout = cmd_stdout.strip().split("\n")

    for vm_name in cmd_stdout:
        context['machines-state'][vm_name] = "STOPPED"

    
    # Paused state
    cmd_stdout, cmd_stderr, cmd_code = callCmd(
        "sudo virsh list --all --state-paused --name"
    )

    if cmd_code:
        messages.error(request, "Failed to retrieve paused VMs")
    else:
        cmd_stdout = cmd_stdout.strip().split("\n")

    for vm_name in cmd_stdout:
        context['machines-state'][vm_name] = "PAUSED"

 
    # Other state
    cmd_stdout, cmd_stderr, cmd_code = callCmd(
        "sudo virsh list --all --state-other --name"
    )

    if cmd_code:
        messages.error(request, "Failed to retrieve other-state VMs")
    else:
        cmd_stdout = cmd_stdout.strip().split("\n")

    for vm_name in cmd_stdout:
        context['machines-state'][vm_name] = "OTHER"

    for vm in VirtualMachine.objects.all():
        if request.user in vm.user_owned.all():
            user_flag = True
        else:
            user_flag = False

        if request.user in vm.root_owned.all():
            root_flag = True
        else:
            root_flag = False

        if not vm.deployed:
            status = "DEPLOYING.."
        else:
            status = context['machines-state'].get(vm.name, None) or "UNKNOWN"

        context['machines'].append({
                'name': vm.name,
                'level': vm.level,
                'status': status,
                'publish_date': vm.published,
                'user': user_flag, 'root': root_flag,
                'id': vm.id,
            })


    return render(request, "panel/machines.html", context)


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get("username", None)
        password = request.POST.get("password", None)

        if not username or not password:
            messages.error(request, "Username or password missing")
            return redirect('login_view')
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(
                    request, (
                        f"Welcome back <b>{username}</b>!"
                        " <i class='fas fa-crown'></i>"
                    )
                )
                return redirect('news')
            else:
                messages.error(request, "Invalid username or password")
                return redirect('login_view')
    return render(request, "panel/login.html", {})


def logout_view(request):
    logout(request)
    return render(request, "panel/login.html", {})

@login_required
def nat(request):
    if request.method == "POST" \
            and not GeneralSettings.objects.filter(key="NETWORK_CONFIGURED"):
        form = NatForm(request.POST, interfaces=if_nameindex())
        if form.is_valid():
            # if_indextoname(1) -> name of the network
            ip_network = form.cleaned_data.get('ip_network')
            interface_index = form.cleaned_data.get('interface')

            netmask = str(IPNetwork(ip_network).netmask)
            gateway_interface = if_indextoname(int(interface_index))
            network_name = form.cleaned_data.get('network_name')
            bridge_name = form.cleaned_data.get('bridge_name')
            host_ip = form.cleaned_data.get('host_ip')
            dhcp_start = form.cleaned_data.get('dhcp_start')
            dhcp_end = form.cleaned_data.get('dhcp_end')

            result_dict = {
                'netmask': netmask,
                'ifname': bridge_name,
                'net_name': network_name,
                'gateway': gateway_interface,
                'host_ip': host_ip,
                'dhcp_start': dhcp_start,
                'dhcp_end': dhcp_end,
            }

            # Copy template and fill it
            nat_virsh_file = render_to_string(
                "nat.xml",
                result_dict
            )
            with NamedTemporaryFile() as fp:
                fp.write(nat_virsh_file.encode())
                fp.flush()

                cmd_stdout, cmd_stderr, cmd_code = callCmd(
                    "sudo virsh net-define " + fp.name
                )

                if cmd_code and (
                        "defined" not in cmd_stdout or
                        "defined" not in cmd_stderr):
                    messages.error(
                        request,
                        "Error occured during network definition: <br/><br/>" +
                        fp.name + "<br/>STDOUT:<br/>" +
                        cmd_stdout.replace("\n", "<br/>") +
                        "<br/>STDERR:<br/>" +
                        cmd_stderr.replace("\n", "<br/>")
                    )
                    return redirect("/sys/nat/")

            cmd_stdout, cmd_stderr, cmd_code = callCmd(
                "sudo virsh net-start " + network_name
            )
            if cmd_code:
                messages.error(
                    request,
                    "Error occured during start of the network: <br/><br/>" +
                    "<br/>STDOUT:<br/>" +
                    cmd_stdout.replace("\n", "<br/>") +
                    "<br/>STDERR:<br/>" +
                    cmd_stderr.replace("\n", "<br/>")
                )
                return redirect("/sys/nat/")
            cmd_stdout, cmd_stderr, cmd_code = callCmd(
                "sudo virsh net-autostart " + network_name
            )
            if cmd_code:
                messages.error(
                    request,
                    "Error occured during setting autostart of " +
                    "the network: <br/><br/>" +
                    "<br/>STDOUT:<br/>" +
                    cmd_stdout.replace("\n", "<br/>") +
                    "<br/>STDERR:<br/>" +
                    cmd_stderr.replace("\n", "<br/>")
                )
                return redirect("/sys/nat/")

            for key, value in result_dict.items():
                full_key = 'NETWORK_CONFIGURATION_' + key.upper()
                if GeneralSettings.objects.filter(key=full_key):
                    tmp = GeneralSettings.objects.get(key=full_key)
                else:
                    tmp = GeneralSettings()
                    tmp.key = full_key
                tmp.value = value
                tmp.save()
                del tmp

            tmp = GeneralSettings()
            tmp.key = "NETWORK_CONFIGURED"
            tmp.value = True
            tmp.save()
            del tmp
            return redirect("/sys/nat/")

    elif GeneralSettings.objects.filter(key="NETWORK_CONFIGURED"):
        net_config_dict = {
            'netmask': None,
            'ifname': None,
            'net_name': None,
            'gateway': None,
            'host_ip': None,
            'dhcp_start': None,
            'dhcp_end': None,
        }
        if request.method == "POST":
            if request.POST.get('delete', '') == 'config':
                config_keys = [
                    'netmask',
                    'ifname',
                    'net_name',
                    'gateway',
                    'host_ip',
                    'dhcp_start',
                    'dhcp_end',
                ]
                for key in config_keys:
                    net_config_dict[key] = GeneralSettings.objects.get(
                        key="NETWORK_CONFIGURATION_" + key.upper()
                    ).delete()

                GeneralSettings.objects.get(
                    key="NETWORK_CONFIGURED").delete()
            return redirect("/sys/nat/")
        else:
            for key in net_config_dict.keys():
                net_config_dict[key] = GeneralSettings.objects.filter(
                    key="NETWORK_CONFIGURATION_" + key.upper()
                )[0].value

            return render(
                request,
                "panel/nat.html",
                {
                    'form': None,
                    'net_config': net_config_dict,
                }
            )
    form = NatForm(interfaces=if_nameindex())
    return render(request, "panel/nat.html", {'form': form})


def create_snapshot(vm_name):
        vm = VirtualMachine.objects.get(name=vm_name)

        # Lock to *try* preventing other code to modify VM
        vm.lock = True
        vm.save()
        snapshot_command = f'sudo virsh snapshot-create-as --disk-only {vm.name} INIT'

        cmd_stdout, cmd_stderr, cmd_code = callCmd(snapshot_command)
        if cmd_code:
            return False
        else:
            cmd_stdout, cmd_stderr, cmd_code = callCmd(
                f'sudo virsh start {vm.name}'
            )
            vm.lock = False
            vm.deployed = True
            vm.save()

        return redirect('/machines/')


@login_required
def deploy_vm(request):

    cmd_stdout, cmd_stderr, cmd_code = callCmd(
        "sudo virsh net-list --all"
    )

    if not cmd_code:
        virsh_networks = [x.split() for x in cmd_stdout.split("\n")[2:]]
    else:
        messages.error(request, "Could not retrieve virsh networks.")
        virsh_networks = []

    if request.method == "POST":
        form = DeployVMForm(request.POST, networks=virsh_networks)
        if form.is_valid():
            result_dict = {
                'vm_name': form.cleaned_data["name"],
                'vm_memory_in_mib': form.cleaned_data["memory"],
                'vm_vcpu_number': form.cleaned_data["vcpu"],
                'vm_disk_type': form.cleaned_data["disk_type"],
                'vm_disk_location': form.cleaned_data["disk_location"],
                'vm_mac_address': form.cleaned_data["mac_address"],
                'vm_network_name': form.cleaned_data["network"],
            }
            # Copy template and fill it
            vm_virsh_file = render_to_string(
                "vm.xml",
                result_dict
            )
            print("valid form")
            with NamedTemporaryFile() as fp:
                fp.write(vm_virsh_file.encode())
                fp.flush()
                vm_len = VirtualMachine.objects.count()
                end_dhcp = GeneralSettings.objects.get(key="NETWORK_CONFIGURATION_DHCP_END")
                start_dhcp = GeneralSettings.objects.get(key="NETWORK_CONFIGURATION_DHCP_START")
                end_dhcp = IPAddress(end_dhcp.value)
                start_dhcp = IPAddress(start_dhcp.value)
                available_pool = int(end_dhcp - start_dhcp)
                if vm_len >= available_pool:
                    request.error(request, "No IPs avaialble")
                    return redirect("/sys/deploy-vm/")
                ip_addr = str(start_dhcp + vm_len)
                mac_addr = form.cleaned_data["mac_address"]
                network_name = form.cleaned_data["network"]
                add_ip_cmd = "sudo virsh net-update %s add-last ip-dhcp-host --xml \"<host mac='%s' ip='%s'/>\" --live --config" % (network_name, mac_addr, ip_addr)
                print(add_ip_cmd)
                cmd_stdout, cmd_stderr, cmd_code = callCmd(add_ip_cmd)

                if cmd_code:
                    messages.warning(request, "Failed to assign static IP. Expect DHCP assigned IP.")

                cmd_stdout, cmd_stderr, cmd_code = callCmd(
                    "sudo virsh define " + fp.name
                )
                if not cmd_code:
                    vm = VirtualMachine()
                    vm.name = form.cleaned_data["name"]
                    vm.level = form.cleaned_data["level"]
                    vm.published = datetime.now()
                    vm.user_flag = form.cleaned_data["user_flag"]
                    vm.root_flag = form.cleaned_data["root_flag"]
                    vm.disk_location = form.cleaned_data["disk_location"]
                    vm.mac_address = form.cleaned_data["mac_address"]
                    vm.network_name = form.cleaned_data["network"]
                    vm.ip_addr = ip_addr
                    vm.save()

                    messages.success(
                        request,
                        "Successfully deployed VM!<br>Snapshoting in the background.")
                    start_new_thread(create_snapshot, (vm.name, ))
                    return redirect("/machines/")
                else:
                    messages.error(
                        request,
                        (
                            "Error during a deployment. <br/>"
                            "STDOUT: " + cmd_stdout + "<br/>"
                            "STDERR: " + cmd_stderr + "<br/>"
                        )
                    )
    else:
        form = DeployVMForm(networks=virsh_networks)
    return render(request, "panel/deploy_vm.html", {'form': form})
