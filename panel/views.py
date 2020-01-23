from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages

# Create your views here.


@login_required
def index(request):
    return render(request, "panel/index.html", {'username': 'h4wky'})


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
                return redirect('index')
            else:
                messages.error(request, "Invalid username or password")
                return redirect('login_view')
    return render(request, "panel/login.html", {})


def logout_view(request):
    logout(request)
    return render(request, "panel/login.html", {})
