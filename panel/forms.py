from django import forms
from django_summernote.widgets import SummernoteWidget


class MailComposeForm(forms.Form):
    receiver = forms.CharField(max_length=255)
    subject = forms.CharField(max_length=255)
    content = forms.CharField(widget=SummernoteWidget())


class NewsForm(forms.Form):
    subject = forms.CharField(max_length=255)
    content = forms.CharField(widget=SummernoteWidget())
