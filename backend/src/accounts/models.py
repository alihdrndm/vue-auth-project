"""Organisations and their users (HANDOFF "Database")."""

from typing import ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from eingang.db import BaseModel, new_id


class Organization(BaseModel):
    class Kind(models.TextChoices):
        STANDARD = "standard"
        SANDBOX = "sandbox"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.STANDARD)
    expires_at = models.DateTimeField(null=True, blank=True)
    vat_id = models.CharField(max_length=32, null=True, blank=True)
    four_eyes = models.BooleanField(default=True)
    duplicate_window_days = models.PositiveIntegerField(default=30)
    reminder_after_days = models.PositiveIntegerField(default=3)
    llm_calls_used = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "organizations"
        indexes: ClassVar = [models.Index(fields=["expires_at"], name="organizations_expires_idx")]

    def __str__(self) -> str:
        return self.slug

    @property
    def is_sandbox(self) -> bool:
        return self.kind == self.Kind.SANDBOX


class UserManager(BaseUserManager["User"]):
    def create_user(
        self,
        email: str,
        password: str | None,
        *,
        organization: Organization,
        role: str,
        name: str = "",
        is_active: bool = True,
    ) -> "User":
        user = self.model(
            email=self.normalize_email(email).lower(),
            organization=organization,
            role=role,
            name=name,
            is_active=is_active,
        )
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    class Role(models.TextChoices):
        ADMIN = "admin"
        ACCOUNTANT = "accountant"
        APPROVER = "approver"
        VIEWER = "viewer"

    id = models.UUIDField(primary_key=True, default=new_id, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="users")
    role = models.CharField(max_length=16, choices=Role.choices)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return str(self.id)
