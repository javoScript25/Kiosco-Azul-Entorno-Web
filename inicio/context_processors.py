from django.conf import settings


def organizacion(request):
    return {"organizacion_nombre": settings.SITE_NAME}
