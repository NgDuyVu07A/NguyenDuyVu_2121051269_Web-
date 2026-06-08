from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.contrib.auth.models import User

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Lục tìm trong CSDL xem có User nào xài email này chưa
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này chưa được đăng ký trong hệ thống!")
        return email