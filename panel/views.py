from django.shortcuts import render

# Create your views here.


def index(request):
    return render(request, "panel/index.html", {'username': 'h4wky'})


def login(request):
    return render(request, "panel/login.html", {})
