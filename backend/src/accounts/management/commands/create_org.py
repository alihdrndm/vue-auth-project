"""`uv run poe create-org --name "…" --admin-email …`: a real organisation and its admin."""

import secrets
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from accounts.models import Organization, User


class Command(BaseCommand):
    help = "Create an organisation with one admin and print the admin's one-time password."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--name", required=True)
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--admin-name", default="")
        parser.add_argument("--vat-id", default=None)

    def handle(self, *args: Any, **options: Any) -> None:  # boundary: django command options
        name: str = options["name"].strip()
        email: str = options["admin_email"].strip().lower()
        slug = slugify(name)[:80]
        if not name or not slug:
            raise CommandError("The name must contain letters or digits.")
        if Organization.objects.filter(slug=slug).exists():
            raise CommandError(f"An organisation with the slug '{slug}' already exists.")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("A user with this email address already exists.")
        password = secrets.token_urlsafe(18)
        with transaction.atomic():
            organization = Organization.objects.create(
                name=name, slug=slug, vat_id=options["vat_id"] or None
            )
            User.objects.create_user(
                email,
                password,
                organization=organization,
                role=User.Role.ADMIN,
                name=options["admin_name"],
            )
        self.stdout.write(f"Created organisation '{name}' ({slug}) with admin {email}.")
        # Shown once, for the person running the command; it is never stored in clear text.
        self.stdout.write(f"One-time password: {password}")
