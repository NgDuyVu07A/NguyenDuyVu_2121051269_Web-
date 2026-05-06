from django.contrib import admin
from django.urls import path, include
from django.conf import settings               # <--- Mới
from django.conf.urls.static import static     # <--- Mới

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
]

# Thêm đoạn này để hiển thị ảnh upload trong môi trường Dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)