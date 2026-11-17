from django.urls import path, re_path

from . import views

urlpatterns = [
    path("categories", views.CategoryListView.as_view()),
    path("categories/<int:pk>", views.CategoryDetailView.as_view()),
    path("categories/<int:pk>/products", views.CategoryProductsView.as_view()),
    path("brands", views.BrandListView.as_view()),
    path("brands/<int:pk>", views.BrandDetailView.as_view()),
    path("brands/<int:pk>/products", views.BrandProductsView.as_view()),
    path("products", views.ProductListView.as_view()),
    path("products/<int:pk>", views.ProductDetailView.as_view()),
    re_path(r"^.*$", views.UnknownEndpointView.as_view()),
]
