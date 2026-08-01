from django.db import models

import uuid
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        LECTURER = 'LECTURER', 'Lecturer'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance Staff'
        ADMIN = 'ADMIN', 'System Administrator'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Designates the access control role for this user."
    )

    # Use email as the primary login identifier instead of standard username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_lecturer(self):
        return self.role == self.Role.LECTURER

    @property
    def is_maintenance(self):
        return self.role == self.Role.MAINTENANCE

    @property
    def is_system_admin(self):
        return self.role == self.Role.ADMIN