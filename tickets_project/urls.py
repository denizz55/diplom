from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

# Simple view that ensures the CSRF cookie is set
@ensure_csrf_cookie
def set_csrf_token(request):
    return JsonResponse({"success": "CSRF cookie set"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('concerts.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='concerts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('set-csrf/', set_csrf_token, name='set_csrf'),  # Add this URL to set CSRF token
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
