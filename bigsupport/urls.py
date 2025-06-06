from django.urls import path
from . import views # This imports from the current app 'bigsupport'

urlpatterns = [
    path('', views.index, name='index'),
]