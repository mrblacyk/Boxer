from django.shortcuts import redirect, render as render_django
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, AnonymousUser, Group
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from time import sleep
from .models import *
from .forms import *
from datetime import datetime, timedelta
from socket import if_nameindex, if_indextoname
from netaddr import IPNetwork
from tempfile import NamedTemporaryFile
from netaddr import IPAddress
from _thread import start_new_thread
from os import path, getcwd
from libvirt import libvirtError
from django.views.generic.detail import DetailView
from paramiko import RSAKey
from io import StringIO
from celery.task.control import revoke as revoke_celery_task
from panel import tasks as celery_tasks
from django.views.decorators.cache import never_cache

import panel.aplibvirt as aplibvirt
import json

# Global vars

global virt_conn
try:
    if GeneralSettings.objects.filter(key="GS_QEMU_URL"):
        virt_conn = aplibvirt.connect(
            GeneralSettings.objects.get(key="GS_QEMU_URL").value
        )
    else:
        virt_conn = aplibvirt.connect()
except:
    virt_conn = aplibvirt.connect()


global INIT_SNAP_NAME
INIT_SNAP_NAME = "init_snapshot"

# Create your views here.


def render(*args, **kwargs):
    gs = {}
    if GeneralSettings.objects.filter(key__contains="GS"):
        gs['pagetitle'] = GeneralSettings.objects.get(
            key='GS_PAGETITLE_TEXT').value
        gs['htmltitle'] = GeneralSettings.objects.get(
            key='GS_HTMLTITLE_TEXT').value
        gs['footer'] = GeneralSettings.objects.get(
            key='GS_FOOTER_TEXT').value
        gs['contact_text'] = GeneralSettings.objects.get(
            key='GS_CONTACT_TEXT').value
        gs['contact_url'] = GeneralSettings.objects.get(
            key='GS_CONTACT_URL').value
        gs['contact_url_text'] = GeneralSettings.objects.get(
            key='GS_CONTACT_URL_TEXT').value
    user = None
    for index, argument in enumerate(args):
        if index == 0:
            user = argument.user
            break
    if not isinstance(user, AnonymousUser):
        unread_count = Messages.objects.filter(
            receiver=user, read=False).count()
    else:
        unread_count = False
    for index, argument in enumerate(args):
        if index == 2:
            if unread_count:
                argument.update({'unread': unread_count})
            argument.update({'gs': gs})
            break

    return render_django(*args, **kwargs)


@login_required
def statistics(request):
    context = {}

    return render(request, "panel/statistics.html", context)


def _handle_uploaded_file(f, fname):
    with open('uploads/' + fname, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def _send_upload_email(req_user, fname, floc):
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
            _handle_uploaded_file(request.FILES['file'], file_name)
            messages.success(request, "Successfully uploaded %s!<br>Check your mailbox for details." % file_name)
            _send_upload_email(request.user, str(request.FILES['file']), file_loc)
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
        vm_name = VirtualMachine.objects.get(id=machine_id).name
        try:
            vm_state, vm_already_running = aplibvirt.startMachine(
                virt_conn, vm_name)
        except (libvirtError, Exception):
            return HttpResponse(status=400)

        if vm_already_running:
            # Already started
            return HttpResponse(status=242)
        elif vm_state == aplibvirt.MACHINE_STATE_RUNNING:
            # Started
            return HttpResponse(status=241)

    return HttpResponse(status=400)


@login_required
def stop_machine(request, machine_id):
    sleep(1)
    if request.method == "GET":
        vm_object = VirtualMachine.objects.get(id=machine_id)
        vm_name = vm_object.name

        if SimpleQueue.objects.filter(vm__name=vm_name, type="reset"):
            # Machine already scheduled to reset
            return HttpResponse(status=254)

        if aplibvirt.machineStopped(virt_conn, vm_name):
            # Already stopped
            return HttpResponse(status=252)

        elif SimpleQueue.objects.filter(vm__name=vm_name, type="stop"):
            # Already scheduled to stop
            return HttpResponse(status=253)

        else:
            sq = SimpleQueue()
            sq.type = "stop"
            sq.vm = vm_object
            sq.task_id = celery_tasks.stop_machine.apply_async(
                (vm_name, True), countdown=150
            )
            sq.save()
            # Scheduled to stop
            return HttpResponse(status=251)

    return HttpResponse(status=400)


@login_required
def reset_machine(request, machine_id):
    sleep(1)
    if request.method == "GET":
        vm_object = VirtualMachine.objects.get(id=machine_id)
        vm_name = vm_object.name

        if SimpleQueue.objects.filter(vm__name=vm_name, type="stop"):
            # Machine already scheduled to stop
            return HttpResponse(status=264)

        if SimpleQueue.objects.filter(vm__name=vm_name, type="reset"):
            # Already scheduled to reset
            return HttpResponse(status=262)

        else:
            sq = SimpleQueue()
            sq.type = "reset"
            sq.vm = vm_object
            sq.task_id = celery_tasks.reset_machine.apply_async(
                (vm_name, True), countdown=150
            )
            sq.save()
            # Scheduled to reset
            return HttpResponse(status=261)

    return HttpResponse(status=400)


@login_required
def cancelreset_action(request, machine_id):
    sleep(1)
    if request.method == "GET":
        if SimpleQueue.objects.filter(vm__id=machine_id, type="reset"):
            # Reset canceled
            reset_task = SimpleQueue.objects.filter(
                vm__id=machine_id, type="reset"
            )[0]
            revoke_celery_task(reset_task.task_id, terminate=True)
            reset_task.delete()
            return HttpResponse(status=271)
        else:
            # Already cancelled
            return HttpResponse(status=272)
    return HttpResponse(status=400)


@login_required
def cancelstop_action(request, machine_id):
    sleep(1)
    if request.method == "GET":
        if SimpleQueue.objects.filter(vm__id=machine_id, type="stop"):
            # Stop canceled
            reset_task = SimpleQueue.objects.filter(
                vm__id=machine_id, type="stop"
            )[0]
            revoke_celery_task(reset_task.task_id, terminate=True)
            reset_task.delete()
            return HttpResponse(status=291)
        else:
            return HttpResponse(status=292)
    return HttpResponse(status=400)


@login_required
def send_flag(request, machine_id):
    sleep(1)
    if request.method == "POST" and request.POST.get("flag"):
        vm = VirtualMachine.objects.filter(id=machine_id)
        if vm:
            if request.POST.get("flag") == vm[0].user_flag:
                if vm[0].user_owned.count() == 0:
                    vm[0].user_fb = request.user
                    vm[0].save()
                vm[0].user_owned.add(request.user)
                return HttpResponse(status=281)
            elif request.POST.get("flag") == vm[0].root_flag:
                if vm[0].root_owned.count() == 0:
                    vm[0].root_fb = request.user
                    vm[0].save()
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
@never_cache
def machines(request):

    context = {}
    context.update({'machines': []})

    all_domains = aplibvirt.listMachines(virt_conn)

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
        elif SimpleQueue.objects.filter(vm__id=vm.id, type="stop"):
            status = "SCHEDULED TO STOP"
        elif SimpleQueue.objects.filter(vm__id=vm.id, type="reset"):
            status = "SCHEDULED TO RESET"
        else:
            if vm.name in all_domains:
                status = aplibvirt.translateMachineState(
                    all_domains[vm.name]
                )
            else:
                status = "UNKNOWN"



        user_count = vm.user_owned.count()
        root_count = vm.root_owned.count()

        context['machines'].append({
            'name': vm.name,
            'level': vm.level,
            'status': status,
            'publish_date': vm.published,
            'user': user_flag, 'root': root_flag,
            'user_count': user_count, 'root_count': root_count,
            'id': vm.id,
        })

    return render(request, "panel/machines.html", context)


def login_view(request):
    if User.objects.all().count() == 0:
        if request.method == 'POST':
            username = request.POST.get("username", None)
            password = request.POST.get("password", None)
            if not username or not password:
                messages.error(request, "Username or password missing")
                return redirect('login_view')
            if not Group.objects.filter(name="sysadmin"):
                group = Group()
                group.name = "sysadmin"
                group.save()
            admin = User()
            admin.username = username
            admin.set_password(password)
            admin.save()
            admin.groups.add(Group.objects.get(name="sysadmin"))
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            news = News()
            news.author = admin
            news.title = "Fresh install!"
            news.created_at = datetime.now()
            news.content = "This is your private HTB-like platform. Thank you for installing it!"
            news.save()
            gs = GeneralSettings()
            gs.key = "GS_FOOTER_TEXT"
            gs.value = "Your <b>Footer</b> - 2020"
            gs.save()
            gs = GeneralSettings()
            gs.key = "GS_CONTACT_TEXT"
            gs.value = "Please see github issues first before creating a new one!"
            gs.save()
            gs = GeneralSettings()
            gs.key = "GS_CONTACT_URL"
            gs.value = None
            gs.save()
            gs = GeneralSettings()
            gs.key = "GS_CONTACT_URL_TEXT"
            gs.value = "Button Value"
            gs.save()
            gs = GeneralSettings()
            gs.key = "GS_HTMLTITLE_TEXT"
            gs.value = "YourPlatformName - Lab Platform"
            gs.save()
            gs = GeneralSettings()
            gs.key = "GS_PAGETITLE_TEXT"
            gs.value = "YourPlatformName"
            gs.save()
            gs = GeneralSettings()
            gs.key = "GS_HOST_UPLOAD_LOC"
            gs.value = ""
            gs.save()

            return redirect('login_view')

        return render(request, "panel/setup.html", {})
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

            if aplibvirt.checkIfNetworkExists(virt_conn, network_name):

                messages.error(
                    request, "Network with that name already exists!"
                )
                return redirect("/sys/nat/")

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

            if aplibvirt.createNetwork(virt_conn, nat_virsh_file):
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
            else:
                messages.error(
                    request,
                    "Fatal error occured during network definition."
                )
        else:
            form = NatForm(request.POST, interfaces=if_nameindex())
            return render(request, "panel/nat.html", {'form': form})

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
                net_name = GeneralSettings.objects.get(
                    key="NETWORK_CONFIGURATION_NET_NAME"
                ).value

                aplibvirt.deleteNetwork(virt_conn, net_name)

                for key in net_config_dict.keys():
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

        aplibvirt.createSnapshot(virt_conn, vm_name, INIT_SNAP_NAME)

        # Success
        vm.lock = False
        vm.deployed = True
        vm.save()

        return redirect('/machines/')


@login_required
def deploy_vm(request):

    virsh_networks = [[
        net.name(),
        "active" if net.isActive() else "inactive",
        str(net.autostart()),
        str(net.isPersistent()),
    ] for net in aplibvirt.listNetworks(virt_conn)]

    if not virsh_networks:
        messages.error(request, "Could not retrieve virsh networks.")

    if request.method == "POST":
        form = DeployVMForm(request.POST, networks=virsh_networks)
        if form.is_valid():
            result_dict = {
                'vm_name': form.cleaned_data["name"],
                'vm_memory_in_mib': form.cleaned_data["memory"],
                'vm_vcpu_number': form.cleaned_data["vcpu"],
                'vm_disk_type': form.cleaned_data["disk_type"],
                'vm_disk_location': GeneralSettings.objects.get(
                    key="GS_HOST_UPLOAD_LOC"
                ).value + form.cleaned_data["disk_location"],
                'vm_mac_address': form.cleaned_data["mac_address"],
                'vm_network_name': form.cleaned_data["network"],
            }
            # Copy template and fill it
            vm_virsh_file = render_to_string(
                "vm.xml",
                result_dict
            )

            vm_len = VirtualMachine.objects.count()
            end_dhcp = GeneralSettings.objects.get(
                key="NETWORK_CONFIGURATION_DHCP_END"
            )
            start_dhcp = GeneralSettings.objects.get(
                key="NETWORK_CONFIGURATION_DHCP_START"
            )
            end_dhcp = IPAddress(end_dhcp.value)
            start_dhcp = IPAddress(start_dhcp.value)
            available_pool = int(end_dhcp - start_dhcp)
            if vm_len >= available_pool:
                request.error(request, "No IPs avaialble")
                return redirect("/sys/deploy-vm/")
            ip_addr = str(start_dhcp + vm_len)
            mac_addr = form.cleaned_data["mac_address"]
            network_name = form.cleaned_data["network"]

            add_mac_result = aplibvirt.addOrUpdateHost(
                virt_conn, network_name, mac_addr, ip_addr
            )

            if not add_mac_result:
                messages.warning(
                    request,
                    "Failed to assign static IP. Expect DHCP assigned IP."
                )
            else:
                messages.success(
                    request,
                    f"IP Address assigned: {ip_addr}"
                )

            vm_created = aplibvirt.createMachine(virt_conn, vm_virsh_file)

            if vm_created:
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
                    "Successfully deployed VM!<br>" +
                    "Snapshoting in the background."
                )
                start_new_thread(create_snapshot, (vm.name, ))
                return redirect("/machines/")
            else:
                messages.error(
                    request,
                    (
                        "Error during a deployment."
                    )
                )
    else:
        net_def = GeneralSettings.objects.filter(key="NETWORK_CONFIGURATION_NET_NAME")
        if net_def:
            net_def = net_def[0].value
        else:
            net_def = None
        form = DeployVMForm(networks=virsh_networks, network_default=net_def)
    return render(request, "panel/deploy_vm.html", {'form': form})


@login_required
def news_compose(request):
    if request.method == "POST":
        form = NewsForm(request.POST)
        if form.is_valid():
            new_news = News()
            new_news.author = User.objects.get(username=request.user)
            new_news.created_at = datetime.now()
            new_news.title = request.POST.get('title')
            new_news.content = request.POST.get('content')
            new_news.save()
            messages.info(request, "News added!")
        return redirect("/")
    form = NewsForm()
    return render(request, "panel/news_compose.html", {
        'form': form,
    })


@login_required
def convert_disk(request):
    if request.method == "POST":
        form = ConvertDiskForm(request.POST)
        if form.is_valid():

            messages.success(
                request,
                "Disk scheduled to be converted. " +
                "You will receive a message upon completion."
            )
            start_new_thread(
                aplibvirt.convertDisk, (request, request.POST["disk_location"])
            )
            return redirect("/sys/convert/")
    if 'form' not in locals():
        form = ConvertDiskForm()
    return render(request, "panel/convert_disk.html", {
        'form': form,
    })


@login_required
def vm_details(request, machine_id):
    context = {}
    if VirtualMachine.objects.filter(id=machine_id):
        context.update({"object": VirtualMachine.objects.get(id=machine_id)})
    return render(request, "panel/virtualmachine_detail.html", context)


@login_required
def config_site(request):
    if request.method == "POST":
        form = ConfigForm(request.POST)
        if form.is_valid():
            gs_field = GeneralSettings.objects.filter(key="GS_FOOTER_TEXT")
            if gs_field:
                gs_field[0].value = request.POST.get('footer')
                gs_field[0].save()

            gs_field = GeneralSettings.objects.filter(key="GS_HTMLTITLE_TEXT")
            if gs_field:
                gs_field[0].value = request.POST.get('html_title')
                gs_field[0].save()

            gs_field = GeneralSettings.objects.filter(key="GS_PAGETITLE_TEXT")
            if gs_field:
                gs_field[0].value = request.POST.get('page_title')
                gs_field[0].save()

            gs_field = GeneralSettings.objects.filter(key="GS_CONTACT_URL")
            if gs_field:
                gs_field[0].value = request.POST.get('contact_url')
                gs_field[0].save()

            gs_field = GeneralSettings.objects.filter(
                key="GS_CONTACT_URL_TEXT"
            )
            if gs_field:
                gs_field[0].value = request.POST.get('contact_url_text')
                gs_field[0].save()

            gs_field = GeneralSettings.objects.filter(key="GS_CONTACT_TEXT")
            if gs_field:
                gs_field[0].value = request.POST.get('contact_text')
                gs_field[0].save()

            gs_field = GeneralSettings.objects.filter(key="GS_HOST_UPLOAD_LOC")
            if gs_field:
                gs_field[0].value = request.POST.get('host_loc')
                gs_field[0].save()
            messages.success(request, "Successfully saved a config!")
            return redirect("/sys/config/")
    if 'form' not in locals():
        form = ConfigForm()
    return render(request, "panel/config.html", {
        'form': form,
    })
