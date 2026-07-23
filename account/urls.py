from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from . import views
from .forms import UserLoginForm
from .tokens import demo_password_reset_token

app_name = 'account'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='account/registration/login.html',
        form_class=UserLoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/account/login/'), name='logout'),
    path('register/', views.account_register, name='register'),
    path('activate/<int:user_id>/<str:activation_key>/', views.account_activate, name='activate'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/edit/', views.edit_details, name='edit_details'),
    path('profile/delete/', views.delete_user_confirm, name='delete_user_confirm'),
    path('profile/delete_user/', views.delete_user, name='delete_user'),
    path('profile/deleted/', TemplateView.as_view(template_name='account/user/deleted.html'), name='delete_confirmation'),

    # Normal email reset flow is available when demo mode is disabled.
    path('password_reset/', views.password_reset, name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='account/registration/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('password_reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='account/registration/password_reset_confirm.html',
             token_generator=demo_password_reset_token,
             success_url='/account/password_reset/complete/',
         ),
         name='password_reset_confirm'),
    path('password_reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='account/registration/password_reset_complete.html',
         ),
         name='password_reset_complete'),
]
