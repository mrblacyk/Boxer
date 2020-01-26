from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from time import sleep
from .models import Messages, News, GeneralSettings
from .forms import MailComposeForm, NewsForm, NatForm
from datetime import datetime, timedelta
import json
from socket import if_nameindex, if_indextoname
from netaddr import IPNetwork

# Create your views here.


@login_required
def index(request):
    context = {}

    return render(request, "panel/statistics.html", context)


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
        # Started
        return HttpResponse(status=241)
        # Already started
        return HttpResponse(status=242)
    return HttpResponse(status=400)


@login_required
def stop_machine(request, machine_id):
    sleep(1)
    if request.method == "GET":
        # Stopped
        return HttpResponse(status=251)
        # Already stopped
        return HttpResponse(status=252)
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
        if request.POST.get("flag") == "281":
            # User
            return HttpResponse(status=281)
        elif request.POST.get("flag") == "282":
            # Root
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
    mailbox_message = Messages.objects.get(id=mail_id)
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
    context.update({'machines': []})
    context['machines'].append({
        'name': 'First',
        'level': 'Easy',
        'status': 'RUNNING',
        'publish_date': '01.01.2020',
        'user': False, 'root': False,
        'id': 1,
    })
    context['machines'].append({
        'name': 'Second',
        'level': 'Medium',
        'status': 'STOPPED',
        'publish_date': '01.01.2020',
        'user': True, 'root': False,
        'id': 2,
    })
    context['machines'].append({
        'name': 'Third',
        'level': 'Easy',
        'status': 'STOPPED',
        'publish_date': '01.01.2020',
        'user': True, 'root': True,
        'id': 3,
    })
    context['machines'].append({
        'name': 'Fourth',
        'level': 'Hard',
        'status': 'RUNNING',
        'publish_date': '01.01.2020',
        'user': False, 'root': True,
        'id': 4,
    })
    context['machines'].append({
        'name': 'Fifth',
        'level': 'Easy',
        'status': 'SCHEDULED FOR A RESET',
        'publish_date': '01.01.2020',
        'user': False, 'root': False,
        'id': 5,
    })
    context['machines'].append({
        'name': 'Sixth',
        'level': 'Medium',
        'status': 'BROKEN BY KURASKOV',
        'publish_date': '01.01.2020',
        'user': True, 'root': False,
        'id': 6,
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
                return redirect('index')
            else:
                messages.error(request, "Invalid username or password")
                return redirect('login_view')
    return render(request, "panel/login.html", {})


def logout_view(request):
    logout(request)
    return render(request, "panel/login.html", {})


def nat(request):
    if request.method == "POST" \
            and not GeneralSettings.objects.filter(key="NETWORK_CONFIGURED"):
        form = NatForm(request.POST, interfaces=if_nameindex())
        if form.is_valid():
            # if_indextoname(1) -> name of the network
            ip_network = form.cleaned_data.get('ip_network')
            interface_index = form.cleaned_data.get('interface')

            netmask = str(IPNetwork(ip_network).netmask)
            interface_name = if_indextoname(int(interface_index))
            network_name = form.cleaned_data.get('network_name')
            bridge_name = form.cleaned_data.get('bridge_name')
            host_ip = form.cleaned_data.get('host_ip')
            dhcp_start = form.cleaned_data.get('dhcp_start')
            dhcp_end = form.cleaned_data.get('dhcp_end')

            result_dict = {
                'netmask': netmask,
                'ifname': interface_name,
                'net_name': network_name,
                'gateway': bridge_name,
                'host_ip': host_ip,
                'dhcp_start': dhcp_start,
                'dhcp_end': dhcp_end,
            }

            # Copy template and fill it
            nat_virsh_file = render_to_string(
                "nat.xml",
                result_dict
            )

            print(nat_virsh_file)

            # with open("/tmp/test.xml", "w") as f:
            #     f.write(nat_virsh_file)

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
