from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('calendar')
    return redirect('login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect),          # редирект с / 
    path('', include('tasks.urls')),  # все урлы приложения
]