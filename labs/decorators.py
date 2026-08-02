from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def student_required(function):
    def check_role(user):
        if user.is_authenticated and (getattr(user, 'role', '') == 'STUDENT' or not user.is_staff):
            return True
        raise PermissionDenied("Access restricted to students.")
    return user_passes_test(check_role)(function)

def lecturer_required(function):
    def check_role(user):
        if user.is_authenticated and getattr(user, 'role', '') == 'LECTURER':
            return True
        raise PermissionDenied("Access restricted to lecturers.")
    return user_passes_test(check_role)(function)