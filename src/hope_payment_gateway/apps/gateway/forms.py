from django import forms
from django.core.validators import RegexValidator

from phonenumber_field.formfields import PhoneNumberField

iban_validator = RegexValidator("^[A-Z]{2}(?:[ ]?[0-9]){18,20}$", "Invalid IBAN")


class DeliveryMechanismForm(forms.Form):
    pass


class MobileMoneyForm(DeliveryMechanismForm):
    phone_no = PhoneNumberField(help_text="Telephone number")
    iban = forms.CharField(max_length=24, validators=[iban_validator], help_text="IBAN Address")


class IbanForm(DeliveryMechanismForm):
    iban = forms.CharField(max_length=24, validators=[iban_validator], help_text="IBAN Address")
