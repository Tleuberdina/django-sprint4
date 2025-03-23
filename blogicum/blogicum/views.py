from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


def custom_logout(request):
    logout(request)
    return redirect(reverse('blog:index'))
