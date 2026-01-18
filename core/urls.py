from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.get_admin_urls() if hasattr(admin.site, 'get_admin_urls') else admin.site.urls),
    path('', include('plataforma.urls')), # Conecta as urls do jogo
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
