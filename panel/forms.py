from django import forms
from django.contrib.auth.models import User
from django_summernote.widgets import SummernoteWidget


class MailComposeForm(forms.Form):
    receiver = forms.ModelChoiceField(
        queryset=User.objects.all(), empty_label=None
    )
    subject = forms.CharField(max_length=255)
    content = forms.CharField(widget=SummernoteWidget())
