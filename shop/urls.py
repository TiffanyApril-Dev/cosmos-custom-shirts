from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.all_designs, name='all_designs'),
    path('item/<slug:slug>/', views.design_detail, name='design_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
]
