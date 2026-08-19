"""`seed_dev`: the local organisation, one user per role and the samples; idempotent."""

from io import StringIO

import pytest
from django.core.management import call_command

from accounts.models import Organization, User
from eingang import clock
from eingang.config import get_settings
from invoices.models import Check, Document
from sandbox.management.commands.seed_dev import LOCAL_SLUG
from sandbox.seed import manifest

pytestmark = pytest.mark.django_db


def seed() -> str:
    output = StringIO()
    call_command("seed_dev", stdout=output)
    return output.getvalue()


def test_seed_dev_twice_leaves_the_same_data(fixed_clock: clock.FixedClock) -> None:
    seed()
    assert "12 samples" in seed()
    organization = Organization.objects.get(slug=LOCAL_SLUG)
    assert Organization.objects.filter(slug=LOCAL_SLUG).count() == 1
    assert organization.name == "Holzwerk Brandt GmbH (local)"
    assert Document.objects.filter(organization=organization).count() == 12
    assert sorted(
        User.objects.filter(organization=organization).values_list("role", flat=True)
    ) == [
        "accountant",
        "admin",
        "approver",
        "viewer",
    ]


def test_seed_dev_users_sign_in_with_the_seed_password(fixed_clock: clock.FixedClock) -> None:
    seed()
    user = User.objects.get(email="accountant@example.invalid")
    assert user.check_password(get_settings().SEED_PASSWORD)
    assert user.is_active


def test_seed_dev_samples_match_the_manifest(fixed_clock: clock.FixedClock) -> None:
    seed()
    organization = Organization.objects.get(slug=LOCAL_SLUG)
    documents = {
        document.original_filename[:3]: document
        for document in Document.objects.filter(organization=organization)
    }
    for sample in manifest():
        document = documents[sample.id]
        found = sorted(Check.objects.filter(document=document).values_list("check_id", flat=True))
        assert (found, document.status) == (sorted(sample.expected_checks), sample.expected_status)
