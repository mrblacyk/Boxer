from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Messages(models.Model):
    sender = models.ForeignKey(
        User, related_name="sender", on_delete=models.SET_NULL, null=True
    )
    receiver = models.ForeignKey(
        User, related_name="receiver", on_delete=models.SET_NULL, null=True
    )
    content = models.TextField()
    created_at = models.DateField()
    read = models.BooleanField(default=False)
