from django.conf import settings


def demo_settings(request):
    return {"demo_mode": settings.DEMO_MODE}
