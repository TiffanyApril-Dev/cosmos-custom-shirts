import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import RegistrationForm, UserEditForm
from .models import UserBase
from .tokens import demo_password_reset_token


def account_register(request):

    if request.user.is_authenticated:
        return redirect('account:dashboard')

    if request.method == 'POST':
        registerForm = RegistrationForm(request.POST)
        if registerForm.is_valid():
            user = registerForm.save(commit=False)
            user.email = registerForm.cleaned_data['email']
            user.set_password(registerForm.cleaned_data['password'])

            if settings.DEMO_MODE:
                user.is_active = True
                user.activation_key = None
                user.activation_created_at = None
                user.save()
                login(request, user)
                return render(request, 'account/registration/demo_registration_success.html')

            user.is_active = False
            user.activation_key = str(uuid.uuid4())
            user.activation_created_at = timezone.now()
            user.save()
            current_site = get_current_site(request)
            subject = 'Activate your Cosmos Custom Shirts Account'
            message = render_to_string('account/registration/account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'user_id': user.pk,
                'activation_key': user.activation_key,
            })
            user.email_user(subject=subject, message=message)
            return render(request, 'account/registration/register_email_confirm.html', {'form': registerForm})
    else:
        registerForm = RegistrationForm()
    return render(request, 'account/registration/register.html', {'form': registerForm})


def account_activate(request, user_id, activation_key):
    try:
        user = UserBase.objects.get(pk=user_id)
    except UserBase.DoesNotExist:
        user = None

    activation_is_current = (
        user is not None
        and user.activation_created_at is not None
        and timezone.now() - user.activation_created_at
        <= timedelta(seconds=settings.ACCOUNT_ACTIVATION_TIMEOUT)
    )

    if activation_is_current and user.activation_key == activation_key:
        user.is_active = True
        user.activation_key = None
        user.activation_created_at = None
        user.save()
        login(request, user)
        return render(request, 'account/registration/activation_success.html')
    else:
        return render(request, 'account/registration/activation_invalid.html')


def password_reset(request):
    if settings.DEMO_MODE:
        return render(request, 'account/registration/password_reset_demo.html')

    view = auth_views.PasswordResetView.as_view(
        template_name='account/registration/password_reset_form.html',
        email_template_name='account/registration/password_reset_email.html',
        subject_template_name='account/registration/password_reset_subject.txt',
        token_generator=demo_password_reset_token,
        success_url='/account/password_reset/done/',
    )
    return view(request)


@login_required
def dashboard(request):
    return render(request, 'account/user/dashboard.html', {'section': 'profile'})


@login_required
def edit_details(request):
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)

        if user_form.is_valid():
            user_form.save()
            return redirect('account:dashboard')
    else:
        user_form = UserEditForm(instance=request.user)

    return render(request, 'account/user/edit_details.html', {'user_form': user_form})


@login_required
def delete_user_confirm(request):
    return render(request, 'account/user/delete_confirm.html')


@login_required
@require_POST
def delete_user(request):
    user = request.user
    user.is_active = False
    user.save()
    logout(request)
    return redirect('account:delete_confirmation')
