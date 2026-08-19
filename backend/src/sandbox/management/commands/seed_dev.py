"""`pnpm seed` (after `seed_rules`): the local organisation with one user per role and the samples.

Idempotent: an existing local organisation is deleted with its files and created again, so
running it twice leaves the same data. Development only; the password is `SEED_PASSWORD`.
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Organization, User
from eingang.config import get_settings
from eingang.maintenance_activities import delete_organization
from sandbox.seed import SamplePeople, seed_samples
from sandbox.services import sample_buyer

LOCAL_SLUG = "holzwerk-brandt-local"
ROLES = (User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.APPROVER, User.Role.VIEWER)


def seed_local_organization() -> Organization:
    existing = Organization.objects.filter(slug=LOCAL_SLUG).first()
    if existing is not None:
        delete_organization(existing)
    buyer = sample_buyer()
    password = get_settings().SEED_PASSWORD
    with transaction.atomic():
        organization = Organization.objects.create(
            name=f"{buyer.name} (local)", slug=LOCAL_SLUG, vat_id=buyer.vat_id
        )
        users = {
            role: User.objects.create_user(
                f"{role}@example.invalid",
                password,
                organization=organization,
                role=role,
                name=role.title(),
            )
            for role in ROLES
        }
        seed_samples(
            organization,
            SamplePeople(
                accountant=users[User.Role.ACCOUNTANT], approver=users[User.Role.APPROVER]
            ),
        )
    return organization


class Command(BaseCommand):
    help = "Create or reset the local organisation, its four users and the twelve samples."

    def handle(self, *args: Any, **options: Any) -> None:  # boundary: django command options
        organization = seed_local_organization()
        emails = ", ".join(f"{role}@example.invalid" for role in ROLES)
        self.stdout.write(f"Seeded '{organization.name}' with 12 samples. Users: {emails}.")
        self.stdout.write("Password: the SEED_PASSWORD setting (default eingang-dev).")
