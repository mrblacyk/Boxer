from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from time import sleep
from .models import Messages
from .forms import MailComposeForm
from datetime import datetime
import json

# Create your views here.


@login_required
def index(request):
    context = {}
    context.update({'username': request.user.username})

    return render(request, "panel/statistics.html", context)


@login_required
def news(request):
    context = {}
    context.update({'username': request.user.username})

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
