from datetime import time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from labs.models import Lab, TimeSlot

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds time slots and demo labs into the database."

    def handle(self, *args, **options):
        slots = [
            ("Morning Slot 1", time(8, 0), time(10, 0)),
            ("Morning Slot 2", time(10, 0), time(12, 0)),
            ("Afternoon Slot 1", time(12, 0), time(14, 0)),
            ("Afternoon Slot 2", time(14, 0), time(16, 0)),
        ]
        for label, start, end in slots:
            TimeSlot.objects.get_or_create(label=label, start_time=start, end_time=end)

        self.stdout.write(self.style.SUCCESS("Time slots seeded successfully!"))