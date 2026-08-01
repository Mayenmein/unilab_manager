from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class StudentLecturerSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=[
            (User.Role.STUDENT, 'Student'),
            (User.Role.LECTURER, 'Lecturer'),
            (User.Role.MAINTENANCE, 'Maintenance Staff'),
        ],
        required=True,
        help_text="Select your primary institutional role."
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'role']

    def save(self, commit=True):
        user = super().save(commit=False)
        # Force the account to be inactive until Admin approves it
        user.is_active = False
        if commit:
            user.save()
        return user 