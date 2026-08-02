from django.contrib import admin
from .models import Lab, Workstation
from .models import TimeSlot, ClassBooking, WorkstationReservation, MaintenanceTicket


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

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['label', 'start_time', 'end_time']


@admin.register(ClassBooking)
class ClassBookingAdmin(admin.ModelAdmin):
    list_display = ['course', 'lab', 'lecturer', 'date', 'time_slot']
    list_filter = ['date', 'lab', 'course']
    search_fields = ['course__course_code', 'lecturer__email', 'lab__name']


@admin.register(WorkstationReservation)
class WorkstationReservationAdmin(admin.ModelAdmin):
    list_display = ['workstation', 'student', 'date', 'time_slot', 'created_at']
    list_filter = ['date', 'workstation__lab']
    search_fields = ['student__email', 'student__username', 'workstation__lab__name']


@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    list_display = ['title', 'workstation', 'priority', 'status', 'reported_by', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'workstation__lab']
    search_fields = ['title', 'description', 'reported_by__email', 'workstation__lab__name']
    raw_id_fields = ['workstation', 'reported_by', 'assigned_to']