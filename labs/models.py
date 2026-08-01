import uuid
from django.db import models
from django.core.exceptions import ValidationError


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