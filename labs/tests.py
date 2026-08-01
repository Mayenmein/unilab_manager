from datetime import date, time, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from labs.models import Lab, Workstation, TimeSlot, ClassBooking, WorkstationReservation
from academics.models import Course, CourseEnrollment

User = get_user_model()


class ReservationFunctionalityTests(TestCase):

    def setUp(self):
        # 1. Create Users (Lecturers & Students)
        self.lecturer_1 = User.objects.create_user(
            username="lecturer1",
            email="lecturer1@university.edu",
            password="Password123!",
            role="LECTURER"
        )
        self.lecturer_2 = User.objects.create_user(
            username="lecturer2",
            email="lecturer2@university.edu",
            password="Password123!",
            role="LECTURER"
        )
        self.enrolled_student = User.objects.create_user(
            username="enrolled_student",
            email="student1@university.edu",
            password="Password123!",
            role="STUDENT"
        )
        self.unenrolled_student = User.objects.create_user(
            username="unenrolled_student",
            email="student2@university.edu",
            password="Password123!",
            role="STUDENT"
        )

        # 2. Create Course & Register Student 1
        self.course = Course.objects.create(
            course_code="CS301",
            course_name="Database Systems",
            lecturer=self.lecturer_1
        )
        CourseEnrollment.objects.create(
            course=self.course,
            student=self.enrolled_student
        )

        # 3. Create Lab (Automatically provisions workstations via Lab.save())
        self.lab = Lab.objects.create(
            name="Computer Lab A",
            capacity=10,
            is_active=True
        )
        self.workstation = self.lab.workstations.first()

        # 4. Create TimeSlots
        self.slot_morning = TimeSlot.objects.create(
            label="Morning Slot (08:00 - 10:00)",
            start_time=time(8, 0),
            end_time=time(10, 0)
        )
        self.slot_afternoon = TimeSlot.objects.create(
            label="Afternoon Slot (12:00 - 14:00)",
            start_time=time(12, 0),
            end_time=time(14, 0)
        )

        self.target_date = date.today() + timedelta(days=1)

    # -------------------------------------------------------------------------
    # TEST 1: Lecturer booking a lab
    # -------------------------------------------------------------------------
    def test_lecturer_can_book_lab(self):
        """A lecturer should successfully book an active lab for their course."""
        booking = ClassBooking(
            lab=self.lab,
            course=self.course,
            lecturer=self.lecturer_1,
            date=self.target_date,
            time_slot=self.slot_morning
        )
        booking.full_clean()  # Triggers Model.clean() validation
        booking.save()

        self.assertEqual(ClassBooking.objects.count(), 1)
        self.assertEqual(booking.lab, self.lab)
        self.assertEqual(booking.lecturer, self.lecturer_1)

    # -------------------------------------------------------------------------
    # TEST 2: Enrolled student reserving workstation (Should Succeed)
    # -------------------------------------------------------------------------
    def test_enrolled_student_can_reserve_workstation_during_class_slot(self):
        """A student enrolled in the course should successfully reserve a seat during the class slot."""
        # Step A: Lecturer books the lab
        ClassBooking.objects.create(
            lab=self.lab,
            course=self.course,
            lecturer=self.lecturer_1,
            date=self.target_date,
            time_slot=self.slot_morning
        )

        # Step B: Enrolled student reserves a seat
        reservation = WorkstationReservation(
            workstation=self.workstation,
            student=self.enrolled_student,
            date=self.target_date,
            time_slot=self.slot_morning
        )
        reservation.full_clean()
        reservation.save()

        self.assertEqual(WorkstationReservation.objects.count(), 1)
        self.assertEqual(reservation.student, self.enrolled_student)

    # -------------------------------------------------------------------------
    # TEST 3: Unenrolled student reserving workstation (Should Fail)
    # -------------------------------------------------------------------------
    def test_unenrolled_student_cannot_reserve_workstation_during_class_slot(self):
        """A student NOT enrolled in the class should be blocked from reserving a seat."""
        # Step A: Lecturer books the lab
        ClassBooking.objects.create(
            lab=self.lab,
            course=self.course,
            lecturer=self.lecturer_1,
            date=self.target_date,
            time_slot=self.slot_morning
        )

        # Step B: Unenrolled student attempts to reserve a seat
        reservation = WorkstationReservation(
            workstation=self.workstation,
            student=self.unenrolled_student,
            date=self.target_date,
            time_slot=self.slot_morning
        )

        with self.assertRaises(ValidationError) as ctx:
            reservation.full_clean()

        self.assertIn('workstation', ctx.exception.message_dict)
        self.assertTrue(
            any("Reservation blocked" in msg for msg in ctx.exception.message_dict['workstation'])
        )

    # -------------------------------------------------------------------------
    # TEST 4: Double-booking lab room during same slot (Should Fail)
    # -------------------------------------------------------------------------
    def test_another_lecturer_cannot_book_already_booked_lab(self):
        """Another lecturer should be prevented from booking the same lab at the same date & time slot."""
        # Initial booking by Lecturer 1
        ClassBooking.objects.create(
            lab=self.lab,
            course=self.course,
            lecturer=self.lecturer_1,
            date=self.target_date,
            time_slot=self.slot_morning
        )

        # Course for Lecturer 2
        course_2 = Course.objects.create(
            course_code="CS404",
            course_name="Software Engineering",
            lecturer=self.lecturer_2
        )

        # Conflict booking attempt by Lecturer 2
        conflict_booking = ClassBooking(
            lab=self.lab,
            course=course_2,
            lecturer=self.lecturer_2,
            date=self.target_date,
            time_slot=self.slot_morning
        )

        with self.assertRaises(ValidationError):
            conflict_booking.full_clean()

    # -------------------------------------------------------------------------
    # TEST 5: Booking a lab after previous slot has passed (Should Succeed)
    # -------------------------------------------------------------------------
    def test_another_lecturer_can_book_lab_in_different_time_slot(self):
        """Another lecturer should successfully book the lab on the same date if it is in a different/subsequent slot."""
        # Lecturer 1 books Morning Slot (08:00 - 10:00)
        ClassBooking.objects.create(
            lab=self.lab,
            course=self.course,
            lecturer=self.lecturer_1,
            date=self.target_date,
            time_slot=self.slot_morning
        )

        course_2 = Course.objects.create(
            course_code="CS404",
            course_name="Software Engineering",
            lecturer=self.lecturer_2
        )

        # Lecturer 2 books Afternoon Slot (12:00 - 14:00) - Slot after the morning slot ends
        subsequent_booking = ClassBooking(
            lab=self.lab,
            course=course_2,
            lecturer=self.lecturer_2,
            date=self.target_date,
            time_slot=self.slot_afternoon
        )
        
        subsequent_booking.full_clean()
        subsequent_booking.save()

        self.assertEqual(ClassBooking.objects.count(), 2)