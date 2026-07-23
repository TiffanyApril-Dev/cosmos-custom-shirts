from django.contrib.auth.tokens import PasswordResetTokenGenerator


class DemoPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom token generator for the demo/learning project.
    Excludes last_login from the hash so that logging in does not
    immediately invalidate a pending password reset link.
    """

    def _make_hash_value(self, user, timestamp):
        # Only hash user pk, active status, password, and timestamp.
        # Omitting last_login prevents login events from invalidating tokens.
        return f"{user.pk}{user.password}{user.is_active}{timestamp}"


demo_password_reset_token = DemoPasswordResetTokenGenerator()
