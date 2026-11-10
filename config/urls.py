from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # auth має стояти раніше за shop: там є «лови-все» маршрут для 404.
    path("api/auth/", include("accounts.urls")),
    path("api/", include("shop.urls")),
]

handler500 = "shop.errors.server_error"
