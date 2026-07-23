from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="member@example.com",
            user_name="member",
            password="StrongPass123",
            is_active=True,
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("account:dashboard"))

        self.assertRedirects(
            response,
            f'{reverse("account:login")}?next={reverse("account:dashboard")}',
        )

    @override_settings(DEMO_MODE=False)
    def test_registration_creates_inactive_user_and_sends_activation_email(self):
        response = self.client.post(
            reverse("account:register"),
            {
                "user_name": "newmember",
                "email": "newmember@example.com",
                "password": "AnotherPass123",
                "password2": "AnotherPass123",
            },
        )

        registered_user = get_user_model().objects.get(email="newmember@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(registered_user.is_active)
        self.assertTrue(registered_user.activation_key)
        self.assertIsNotNone(registered_user.activation_created_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(registered_user.activation_key, mail.outbox[0].body)

    @override_settings(DEMO_MODE=True)
    def test_demo_registration_activates_and_logs_in_without_email(self):
        response = self.client.post(
            reverse("account:register"),
            {
                "user_name": "demomember",
                "email": "fictional@example.test",
                "password": "AnotherPass123",
                "password2": "AnotherPass123",
            },
        )

        registered_user = get_user_model().objects.get(email="fictional@example.test")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your demo account is ready")
        self.assertTrue(registered_user.is_active)
        self.assertIsNone(registered_user.activation_key)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(int(self.client.session["_auth_user_id"]), registered_user.pk)

    def test_activation_enables_user_and_logs_them_in(self):
        self.user.is_active = False
        self.user.activation_key = "valid-activation-key"
        self.user.activation_created_at = timezone.now()
        self.user.save(
            update_fields=["is_active", "activation_key", "activation_created_at"]
        )

        response = self.client.get(
            reverse(
                "account:activate",
                args=[self.user.pk, self.user.activation_key],
            )
        )

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.activation_key)
        self.assertIsNone(self.user.activation_created_at)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    @override_settings(DEMO_MODE=True)
    def test_password_reset_explains_that_email_is_disabled_in_demo(self):
        response = self.client.get(reverse("account:password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password reset is disabled in demo mode")

    def test_account_deactivation_rejects_get(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("account:delete_user"))

        self.assertEqual(response.status_code, 405)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_account_deactivation_requires_csrf_protected_post(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(reverse("account:delete_user"))

        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_account_deactivation_post_disables_user_and_logs_out(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("account:delete_user"))

        self.assertRedirects(response, reverse("account:delete_confirmation"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)
