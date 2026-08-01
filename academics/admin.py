from django.contrib import admin
from .models import Course, CourseEnrollment


class CourseEnrollmentInline(admin.TabularInline):
    model = CourseEnrollment
    extra = 1
    raw_id_fields = ['student']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_name', 'lecturer', 'created_at']
    search_fields = ['course_code', 'course_name', 'lecturer__email', 'lecturer__username']
    inlines = [CourseEnrollmentInline]


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['course', 'student', 'enrolled_at']
    list_filter = ['course']
    search_fields = ['student__email', 'student__username', 'course__course_code']