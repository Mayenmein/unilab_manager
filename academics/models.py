import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_code = models.CharField(max_length=20, unique=True, help_text="e.g. CS101")
    course_name = models.CharField(max_length=150)
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='taught_courses',
        limit_choices_to={'role': 'LECTURER'}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course_code']

    def clean(self):
        super().clean()
        if self.lecturer and not self.lecturer.is_lecturer:
            raise ValidationError({'lecturer': 'Assigned user must have the LECTURER role.'})

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class CourseEnrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'STUDENT'}
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Enforce unique composite key (a student cannot enroll in the same course twice)
        unique_together = ('course', 'student')
        ordering = ['-enrolled_at']

    def clean(self):
        super().clean()
        if self.student and not self.student.is_student:
            raise ValidationError({'student': 'Enrolled user must have the STUDENT role.'})

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} enrolled in {self.course.course_code}"