from django import forms

from .models import App
from .services import requestable_apps


class AccessRequestForm(forms.Form):
    app = forms.ModelChoiceField(queryset=App.objects.none(), empty_label="Select an agent…", label="Agent")
    reason = forms.CharField(
        required=False,
        max_length=500,
        label="Why do you need access? (optional)",
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["app"].queryset = requestable_apps(user)