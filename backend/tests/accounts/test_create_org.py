from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import Organization, User

pytestmark = pytest.mark.django_db


def run(*args: str) -> str:
    output = StringIO()
    call_command("create_org", *args, stdout=output)
    return output.getvalue()


def test_create_org_makes_the_organisation_and_its_admin() -> None:
    output = run("--name", "Holzwerk Brandt GmbH", "--admin-email", "Chef@Example.INVALID")
    organization = Organization.objects.get(slug="holzwerk-brandt-gmbh")
    admin = User.objects.get(email="chef@example.invalid")
    assert organization.kind == "standard"
    assert admin.role == "admin"
    password = output.strip().splitlines()[-1].removeprefix("One-time password: ")
    assert admin.check_password(password)


def test_create_org_refuses_a_taken_slug_or_email() -> None:
    run("--name", "Firma", "--admin-email", "a@example.invalid")
    with pytest.raises(CommandError, match="slug"):
        run("--name", "Firma", "--admin-email", "b@example.invalid")
    with pytest.raises(CommandError, match="email"):
        run("--name", "Andere Firma", "--admin-email", "A@example.invalid")
