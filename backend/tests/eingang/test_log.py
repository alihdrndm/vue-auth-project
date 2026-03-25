import logging

from django.conf import settings


def test_factur_x_never_logs_invoice_contents() -> None:
    # factur-x logs the whole embedded XML at DEBUG and INFO.
    assert settings.configured
    assert logging.getLogger("factur-x").getEffectiveLevel() >= logging.WARNING
