from django.urls import path

from . import views


app_name = 'pages'

urlpatterns = [
    path('about/', views.AboutProject.as_view(), name='about'),
    path('rules/', views.RulesProject.as_view(), name='rules'),
]
