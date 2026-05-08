"""What every Eingang table shares: a UUID v7 primary key and two timestamps."""

import uuid

from django.db import models
from uuid_utils.compat import uuid7


def new_id() -> uuid.UUID:
    # UUID v7 sorts by creation time, so primary-key order follows insertion order.
    return uuid7()


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=new_id, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
