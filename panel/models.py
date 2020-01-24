from django.db import models
from django.contrib.auth.models import User
from uuid import uuid4

# Create your models here.


class Messages(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    sender = models.ForeignKey(
        User, related_name="sender", on_delete=models.SET_NULL, null=True
    )
    receiver = models.ForeignKey(
        User, related_name="receiver", on_delete=models.SET_NULL, null=True
    )
    content = models.TextField()
    subject = models.CharField(max_length=255)
    created_at = models.DateField()
    read = models.BooleanField(default=False)
    trash = models.BooleanField(default=False)
