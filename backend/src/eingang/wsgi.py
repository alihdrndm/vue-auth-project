import os

from django.core.wsgi import get_wsgi_application

# The process entry point names its settings module; this is not configuration.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eingang.settings")

application = get_wsgi_application()
