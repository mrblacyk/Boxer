from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponse
from time import sleep

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
    sleep(1)
    return HttpResponse(status=400)


@login_required
def stop_machine(request, machine_id):
    sleep(1)
    return HttpResponse(status=204)


@login_required
def reset_machine(request, machine_id):
    sleep(1)
    return HttpResponse(status=400)


@login_required
def send_flag(request, machine_id):
    sleep(1)
    return HttpResponse(status=400)


@login_required
def machines(request):
    context = {}
    context.update({'username': request.user.username})
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
                messages.success(request, "Logged in!")
                messages.warning(request, "Warning!")
                messages.warning(request, "Warning!")
                messages.warning(request, "Warning!")
                messages.error(request, "Error!")
                messages.warning(request, "Warning!")
                messages.success(request, "Logged in!")
                messages.success(request, "Logged in!")
                return redirect('index')
            else:
                messages.error(request, "Invalid username or password")
                return redirect('login_view')
    return render(request, "panel/login.html", {})


def logout_view(request):
    logout(request)
    return render(request, "panel/login.html", {})
