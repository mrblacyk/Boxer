from django.db import models
from django.contrib.auth import User

# Create your models here.


class Messages(models.Model):
    sender = models.ForeignKey(User, related_name="sender")
    receiver = models.ForeignKey(User, related_name="receiver")
    content = models.TextField()
    created_at = models.DateField()
    read = models.BooleanField(default=False)
