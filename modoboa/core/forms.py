# coding: utf-8

"""Core forms."""

from __future__ import unicode_literals

from django import forms
from django.db.models import Q
from django.utils.translation import ugettext as _, ugettext_lazy

from django.contrib.auth import forms as auth_forms
from django.contrib.auth import get_user_model

from django.contrib.auth import password_validation

from modoboa.core.models import User
from modoboa.parameters import tools as param_tools


class LoginForm(forms.Form):
    """User login form."""

    username = forms.CharField(
        label=ugettext_lazy("Username"),
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    password = forms.CharField(
        label=ugettext_lazy("Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    rememberme = forms.BooleanField(
        initial=False,
        required=False
    )


class ProfileForm(forms.ModelForm):
    """Form to update User profile."""

    oldpassword = forms.CharField(
        label=ugettext_lazy("Old password"), required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    newpassword = forms.CharField(
        label=ugettext_lazy("New password"), required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    confirmation = forms.CharField(
        label=ugettext_lazy("Confirmation"), required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    class Meta(object):
        model = User
        fields = ("first_name", "last_name", "language",
                  "phone_number", "secondary_email")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"})
        }

    def __init__(self, update_password, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        if not update_password:
            del self.fields["oldpassword"]
            del self.fields["newpassword"]
            del self.fields["confirmation"]

    def clean_oldpassword(self):
        if self.cleaned_data["oldpassword"] == "":
            return self.cleaned_data["oldpassword"]

        if param_tools.get_global_parameter("authentication_type") != "local":
            return self.cleaned_data["oldpassword"]

        if not self.instance.check_password(self.cleaned_data["oldpassword"]):
            raise forms.ValidationError(_("Old password mismatchs"))
        return self.cleaned_data["oldpassword"]

    def clean_confirmation(self):
        newpassword = self.cleaned_data["newpassword"]
        confirmation = self.cleaned_data["confirmation"]
        if newpassword != confirmation:
            raise forms.ValidationError(_("Passwords mismatch"))
        password_validation.validate_password(confirmation, self.instance)
        return confirmation

    def save(self, commit=True):
        user = super(ProfileForm, self).save(commit=False)
        if commit:
            if self.cleaned_data.get("confirmation", "") != "":
                user.set_password(
                    self.cleaned_data["confirmation"],
                    self.cleaned_data["oldpassword"]
                )
            user.save()
        return user


class APIAccessForm(forms.Form):
    """Form to control API access."""

    enable_api_access = forms.BooleanField(
        label=ugettext_lazy("Enable API access"), required=False)

    def __init__(self, *args, **kwargs):
        """Initialize form."""
        user = kwargs.pop("user")
        super(APIAccessForm, self).__init__(*args, **kwargs)
        self.fields["enable_api_access"].initial = hasattr(user, "auth_token")


class PasswordResetForm(auth_forms.PasswordResetForm):
    """Custom password reset form."""

    def get_users(self, email):
        """Return matching user(s) who should receive a reset."""
        return (
            get_user_model()._default_manager.filter(
                email__iexact=email, is_active=True)
            .exclude(Q(secondary_email__isnull=True) | Q(secondary_email=""))
        )

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email,
                  html_email_template_name=None):
        """Send message to secondary email instead."""
        to_email = context["user"].secondary_email
        super(PasswordResetForm, self).send_mail(
            subject_template_name, email_template_name,
            context, from_email, to_email, html_email_template_name)
