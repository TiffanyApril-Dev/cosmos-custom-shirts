from django import forms
from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import UserBase


class UserAdminCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = UserBase
        fields = ("email", "user_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two passwords do not match.")
        password_validation.validate_password(password2, self.instance)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        help_text=(
            "Passwords are stored securely and cannot be viewed. "
            "Use the password-change form to replace this password."
        )
    )

    class Meta:
        model = UserBase
        fields = "__all__"

    def clean_password(self):
        return self.initial.get("password")


@admin.register(UserBase)
class UserBaseAdmin(UserAdmin):
    add_form = UserAdminCreationForm
    form = UserAdminChangeForm
    model = UserBase

    list_display = (
        "email",
        "user_name",
        "first_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "created",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "created")
    search_fields = ("email", "user_name", "first_name")
    ordering = ("email",)
    readonly_fields = ("created", "updated", "last_login")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("user_name", "first_name", "about")}),
        (
            "Demo delivery details",
            {
                "classes": ("collapse",),
                "fields": (
                    "country",
                    "phone_number",
                    "postcode",
                    "address_line_1",
                    "address_line_2",
                    "town_city",
                ),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Activation",
            {
                "classes": ("collapse",),
                "fields": ("activation_key", "activation_created_at"),
            },
        ),
        ("Dates", {"fields": ("last_login", "created", "updated")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "user_name",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields.extend(("is_staff", "is_superuser", "groups", "user_permissions"))
        return tuple(dict.fromkeys(fields))

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and obj != request.user

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
