from django.urls import path

from . import views

app_name = "basket"

urlpatterns = [
    path("", views.cart_summary, name="basket_summary"),
    path("add/", views.cart_add, name="basket_add"),
    path("update/", views.cart_update, name="basket_update"),
    path("delete/", views.cart_delete, name="basket_delete"),
]
