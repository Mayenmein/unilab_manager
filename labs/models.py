import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from academics.models import Course, CourseEnrollment



class Lab(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Lab A - Computer Science Building")
    building_location = models.CharField(max_length=150, help_text="e.g. Block B, Floor 2")
    capacity = models.PositiveIntegerField(help_text="Maximum total workstations in this lab")
    is_active = models.BooleanField(default=True, help_text="Designates whether the lab facility is currently operational")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Check whether this object already exists in the database
        is_new = not (self.pk and Lab.objects.filter(pk=self.pk).exists())
        old_active_state = None

        # Fetch the previous state from the DB if updating
        if not is_new:
            old_instance = Lab.objects.get(pk=self.pk)
            old_active_state = old_instance.is_active

        # Save the Lab instance first to ensure PK exists in DB
        super().save(*args, **kwargs)

        # 1. AUTO-CREATE WORKSTATIONS ON NEW LAB CREATION
        if is_new:
            initial_status = (
                Workstation.Status.AVAILABLE
                if self.is_active
                else Workstation.Status.MAINTENANCE
            )
            workstations_to_create = [
                Workstation(lab=self, seat_number=seat_num, status=initial_status)
                for seat_num in range(1, self.capacity + 1)
            ]
            # Use bulk_create for high performance
            Workstation.objects.bulk_create(workstations_to_create)

        # 2. AUTO-SYNC STATUS WHEN LAB ACTIVE TOGGLE CHANGES
        elif old_active_state is not None and old_active_state != self.is_active:
            new_status = (
                Workstation.Status.AVAILABLE
                if self.is_active
                else Workstation.Status.MAINTENANCE
            )
            self.workstations.update(status=new_status)

    def __str__(self):
        status_str = "Active" if self.is_active else "Inactive/Closed"
        return f"{self.name} ({status_str} - Cap: {self.capacity})"


class Workstation(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab = models.ForeignKey(
        Lab,
        on_delete=models.CASCADE,
        related_name='workstations'
    )
    seat_number = models.PositiveIntegerField(help_text="Unique seat index within the lab, e.g. 1, 2, 3...")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        help_text="Operational state of the workstation"
    )

    class Meta:
        unique_together = ('lab', 'seat_number')
        ordering = ['lab', 'seat_number']

    @property
    def is_available(self):
        return self.lab.is_active and (self.status == self.Status.AVAILABLE)

    def clean(self):
        super().clean()

        # 1. Enforce seat capacity limit
        if self.seat_number and self.seat_number > self.lab.capacity:
            raise ValidationError({
                'seat_number': f"Seat number {self.seat_number} exceeds lab capacity of {self.lab.capacity}."
            })

        # 2. Strict Check: If parent Lab is inactive, workstation status CANNOT be set to AVAILABLE
        if self.lab_id and not self.lab.is_active and self.status == self.Status.AVAILABLE:
            raise ValidationError({
                'status': f"Cannot set seat status to Available because parent '{self.lab.name}' is inactive/closed."
            })

    def __str__(self):
        state = "Available" if self.is_available else "Under Maintenance / Lab Closed"
        return f"{self.lab.name} - Seat #{self.seat_number} [{state}]"


class TimeSlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=50, help_text="e.g. Morning Slot 1 (08:00 - 10:00)")
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['start_time']

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})

    def __str__(self):
        return f"{self.label} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class ClassBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name='class_bookings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lab_bookings')
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_bookings',
        limit_choices_to={'role': 'LECTURER'}
    )
    date = models.DateField()
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='class_bookings')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent double-booking a lab room during the same slot
        unique_together = ('lab', 'date', 'time_slot')
        ordering = ['date', 'time_slot__start_time']

    def clean(self):
        super().clean()
        
        # 1. Check lab availability
        if self.lab_id and not self.lab.is_active:
            raise ValidationError({'lab': f"Cannot book class in '{self.lab.name}' because it is inactive/closed."})

        # 2. Check user role
        if self.lecturer_id and not self.lecturer.is_lecturer:
            raise ValidationError({'lecturer': 'Only users with the LECTURER role can book lab class sessions.'})

        # 3. Check course lecturer alignment
        if self.course_id and self.lecturer_id and self.course.lecturer != self.lecturer:
            raise ValidationError({'course': f"Lecturer {self.lecturer} is not assigned to teach course {self.course.course_code}."})

    def __str__(self):
        return f"{self.course.course_code} in {self.lab.name} on {self.date} ({self.time_slot.label})"


class WorkstationReservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workstation = models.ForeignKey(Workstation, on_delete=models.CASCADE, related_name='reservations')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        limit_choices_to={'role': 'STUDENT'}
    )
    date = models.DateField()
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='reservations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Enforce unique seat reservation per slot AND unique student reservation per slot
        unique_together = ('workstation', 'date', 'time_slot')
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'date', 'time_slot'],
                name='unique_student_reservation_per_slot'
            )
        ]
        ordering = ['date', 'time_slot__start_time']

    def clean(self):
        super().clean()

        # 1. Role validation
        if self.student_id and not self.student.is_student:
            raise ValidationError({'student': 'Only registered STUDENT users can reserve individual workstations.'})

        # 2. Seat / Lab status check
        if self.workstation_id and not self.workstation.is_available:
            raise ValidationError({'workstation': f"Workstation Seat #{self.workstation.seat_number} is currently unavailable or the lab is closed."})

        # 3. ONE SEAT PER STUDENT PER TIME SLOT CHECK
        if self.student_id and self.date and self.time_slot_id:
            existing_booking = WorkstationReservation.objects.filter(
                student=self.student,
                date=self.date,
                time_slot=self.time_slot
            )
            # Exclude current instance if updating an existing object
            if self.pk:
                existing_booking = existing_booking.exclude(pk=self.pk)

            if existing_booking.exists():
                raise ValidationError({
                    'workstation': f"You already have a seat reserved for this time slot on {self.date}."
                })

        # 4. CLASS LOCK & ENROLLMENT CONSTRAINT CHECK
        if self.workstation_id and self.date and self.time_slot_id:
            lab = self.workstation.lab
            active_class = ClassBooking.objects.filter(
                lab=lab,
                date=self.date,
                time_slot=self.time_slot
            ).first()

            if active_class:
                # Check if the student is enrolled in the scheduled course
                is_enrolled = CourseEnrollment.objects.filter(
                    course=active_class.course,
                    student=self.student
                ).exists()

                if not is_enrolled:
                    raise ValidationError({
                        'workstation': (
                            f"Reservation blocked: {lab.name} is reserved for course "
                            f"'{active_class.course.course_code}' during this time slot. "
                            f"Only enrolled students of {active_class.course.course_code} can reserve seats."
                        )
                    })

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} - Seat #{self.workstation.seat_number} ({self.date})"

class MaintenanceTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workstation = models.ForeignKey(
        'Workstation',
        on_delete=models.CASCADE,
        related_name='maintenance_tickets'
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_tickets'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        help_text="Staff or Admin handling the repair"
    )
    title = models.CharField(max_length=150, help_text="e.g. Broken Monitor, Mouse Unresponsive")
    description = models.TextField()
    priority = models.CharField(
        max_length=15,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.assigned_to_id and not (self.assigned_to.is_staff or getattr(self.assigned_to, 'role', '') in ['STAFF', 'ADMIN']):
            raise ValidationError({
                'assigned_to': 'Tickets can only be assigned to users with STAFF or ADMIN roles.'
            })

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Workstation Status Syncing
        active_statuses = [self.Status.OPEN, self.Status.IN_PROGRESS]
        
        if self.status in active_statuses:
            if self.workstation.status != self.workstation.Status.MAINTENANCE:
                self.workstation.status = self.workstation.Status.MAINTENANCE
                self.workstation.save(update_fields=['status'])
        else:
            has_other_active = MaintenanceTicket.objects.filter(
                workstation=self.workstation,
                status__in=active_statuses
            ).exclude(pk=self.pk).exists()

            if not has_other_active and self.workstation.lab.is_active:
                if self.workstation.status != self.workstation.Status.AVAILABLE:
                    self.workstation.status = self.workstation.Status.AVAILABLE
                    self.workstation.save(update_fields=['status'])

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title} - Seat #{self.workstation.seat_number}"