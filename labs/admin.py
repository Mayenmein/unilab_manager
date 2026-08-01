# labs/admin.py

from django.contrib import admin
from .models import Lab, Workstation


@admin.action(description='Activate selected labs and make workstations available')
def activate_labs(modeladmin, request, queryset):
    for lab in queryset:
        lab.is_active = True
        lab.save()  # Triggers the automatic workstation status update in save()


@admin.action(description='Deactivate selected labs and set workstations to maintenance')
def deactivate_labs(modeladmin, request, queryset):
    for lab in queryset:
        lab.is_active = False
        lab.save()  # Triggers the automatic workstation status update in save()


class WorkstationInline(admin.TabularInline):
    model = Workstation
    extra = 0
    fields = ['seat_number', 'status']


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ['name', 'building_location', 'capacity', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'building_location']
    actions = [activate_labs, deactivate_labs]
    inlines = [WorkstationInline]


@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    list_display = ['lab', 'seat_number', 'status', 'is_available']
    list_filter = ['status', 'lab__is_active', 'lab']
    search_fields = ['lab__name', 'seat_number']