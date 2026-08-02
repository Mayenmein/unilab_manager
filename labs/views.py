from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Func

from labs.models import Lab, Workstation, TimeSlot, ClassBooking, WorkstationReservation, MaintenanceTicket
from labs.decorators import student_required, lecturer_required
from academics.models import Course, CourseEnrollment

@login_required
def root_redirect_view(request):
    """Gateway redirect based on user role."""
    if request.user.is_staff or getattr(request.user, 'role', '') in ['ADMIN', 'STAFF']:
        return redirect('/admin/')
    elif getattr(request.user, 'role', '') == 'LECTURER':
        return redirect('labs:lecturer_dashboard')
    return redirect('labs:student_dashboard')


# --- STUDENT PORTAL ---

@login_required
@student_required
def student_dashboard(request):
    user = request.user
    today = now().date()

    # 1. Get courses the student is enrolled in
    enrolled_course_ids = CourseEnrollment.objects.filter(
        student=user
    ).values_list('course_id', flat=True)

    # 2. Get active class bookings for those courses from today onwards
    active_class_bookings = ClassBooking.objects.filter(
        course_id__in=enrolled_course_ids,
        date__gte=today
    ).select_related('lab', 'time_slot', 'course').order_by('date', 'time_slot__start_time')

    # Global Empty State Check
    if not active_class_bookings.exists():
        return render(request, 'labs/student_dashboard.html', {
            'no_active_locks': True,
            'message': 'No labs are currently booked for your enrolled courses.'
        })

    # 3. Filter distinct operational labs with active bookings
    available_labs = Lab.objects.filter(
        id__in=active_class_bookings.values_list('lab_id', flat=True).distinct(),
        is_active=True
    )

    # 4. Resolve Selected Lab
    selected_lab_id = request.GET.get('lab')
    if selected_lab_id and available_labs.filter(pk=selected_lab_id).exists():
        selected_lab = available_labs.get(pk=selected_lab_id)
    else:
        selected_lab = available_labs.first()

    # Filter bookings for the selected lab
    lab_bookings = active_class_bookings.filter(lab=selected_lab)

    # 5. Resolve Available & Selected Date
    available_dates = lab_bookings.values_list('date', flat=True).distinct()
    
    selected_date_str = request.GET.get('date')
    selected_date = None
    if selected_date_str:
        try:
            parsed_date = timezone.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            if parsed_date in available_dates:
                selected_date = parsed_date
        except ValueError:
            pass
            
    if not selected_date:
        selected_date = available_dates.first()

    # 6. Resolve Available & Selected Time Slot
    date_bookings = lab_bookings.filter(date=selected_date)
    available_slots = TimeSlot.objects.filter(
        id__in=date_bookings.values_list('time_slot_id', flat=True).distinct()
    ).order_by('start_time')

    selected_slot_id = request.GET.get('slot')
    selected_slot = None

    if selected_slot_id and available_slots.filter(pk=selected_slot_id).exists():
        selected_slot = available_slots.get(pk=selected_slot_id)
    else:
        # Auto-select the FIRST (earliest) time slot on that date
        selected_slot = available_slots.first()

    # 7. Build Seat Availability Grid
    workstations_data = []
    if selected_lab and selected_date and selected_slot:
        active_class = date_bookings.filter(time_slot=selected_slot).first()

        for seat in selected_lab.workstations.all():
            is_reserved = WorkstationReservation.objects.filter(
                workstation=seat,
                date=selected_date,
                time_slot=selected_slot
            ).exists()

            if seat.status == Workstation.Status.MAINTENANCE:
                seat_status = 'MAINTENANCE'
            elif is_reserved:
                seat_status = 'OCCUPIED'
            elif active_class:
                # Check student enrollment in the active class
                is_enrolled = active_class.course.enrollments.filter(student=user).exists()
                seat_status = 'AVAILABLE' if is_enrolled else 'CLASS_LOCKED'
            else:
                seat_status = 'AVAILABLE'

            workstations_data.append({'seat': seat, 'ui_status': seat_status})

    my_reservations = WorkstationReservation.objects.filter(student=user, date__gte=today)

    context = {
        'no_active_locks': False,
        'labs': available_labs,
        'selected_lab': selected_lab,
        'available_dates': available_dates,
        'selected_date': str(selected_date),
        'available_slots': available_slots,
        'selected_slot': selected_slot,
        'workstations_data': workstations_data,
        'my_reservations': my_reservations,
    }

    return render(request, 'labs/student_dashboard.html', context)

@login_required
@student_required
def reserve_workstation(request, seat_id):
    if request.method == 'POST':
        workstation = get_object_or_404(Workstation, pk=seat_id)
        booking_date = request.POST.get('date')
        slot_id = request.POST.get('time_slot')

        try:
            slot = TimeSlot.objects.get(pk=slot_id)
            reservation = WorkstationReservation(
                workstation=workstation,
                student=request.user,
                date=booking_date,
                time_slot=slot
            )
            reservation.full_clean()
            reservation.save()
            messages.success(request, f"Seat #{workstation.seat_number} reserved successfully!")
        except ValidationError as e:
            messages.error(request, e.messages[0] if isinstance(e.messages, list) else str(e))

    url = f"{reverse('labs:student_dashboard')}?lab={workstation.lab.id}&date={booking_date}&slot={slot_id}"
    return redirect(url)


@login_required
@student_required
def report_fault(request, seat_id):
    if request.method != 'POST':
        return redirect('labs:student_dashboard')

    workstation = get_object_or_404(Workstation, id=seat_id)
    title = request.POST.get('title')
    priority = request.POST.get('priority', MaintenanceTicket.Priority.MEDIUM)
    description = request.POST.get('description')

    with transaction.atomic():
        # 1. Create the fault ticket (triggers workstation status change to MAINTENANCE)
        MaintenanceTicket.objects.create(
            workstation=workstation,
            reported_by=request.user,
            title=title,
            priority=priority,
            description=description
        )

        today = now().date()

        # 2. Check if the user currently holds a reservation for this faulty seat
        current_reservation = WorkstationReservation.objects.filter(
            student=request.user,
            workstation=workstation,
            date__gte=today
        ).select_related('time_slot').order_by('date', 'time_slot__start_time').first()

        if current_reservation:
            target_date = current_reservation.date
            target_slot = current_reservation.time_slot
            lab = workstation.lab

            # Get IDs of all seats reserved in this lab for this slot/date
            reserved_seat_ids = WorkstationReservation.objects.filter(
                workstation__lab=lab,
                date=target_date,
                time_slot=target_slot
            ).values_list('workstation_id', flat=True)

            # Query available operational seats, excluding the faulty one and reserved ones
            candidate_seats = Workstation.objects.filter(
                lab=lab,
                status=Workstation.Status.AVAILABLE
            ).exclude(
                id__in=reserved_seat_ids
            ).exclude(
                id=workstation.id
            ).annotate(
                distance=Func(F('seat_number') - workstation.seat_number, function='ABS')
            ).order_by('distance', 'seat_number')

            closest_seat = candidate_seats.first()

            if closest_seat:
                # Cancel old reservation
                current_reservation.delete()

                # Reserve closest seat
                WorkstationReservation.objects.create(
                    student=request.user,
                    workstation=closest_seat,
                    date=target_date,
                    time_slot=target_slot
                )

                messages.success(
                    request,
                    f"Issue reported for Seat #{workstation.seat_number}. "
                    f"You have been automatically moved to Seat #{closest_seat.seat_number}."
                )
            else:
                # All seats are full — maintain existing seat
                messages.warning(
                    request,
                    f"Issue reported for Seat #{workstation.seat_number}. "
                    f"No alternative seats are available in {lab.name} during this slot, "
                    f"so your current reservation has been maintained."
                )
        else:
            messages.info(
                request,
                f"Thank you for reporting the issue on Seat #{workstation.seat_number}."
            )

    return redirect('labs:student_dashboard')

@login_required
@lecturer_required
def cancel_class_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(ClassBooking, id=booking_id, lecturer=request.user)
        
        with transaction.atomic():
            # 1. Clean up student seat reservations tied to this class lock
            WorkstationReservation.objects.filter(
                workstation__lab=booking.lab,
                date=booking.date,
                time_slot=booking.time_slot
            ).delete()

            # 2. Delete the class booking
            course_code = booking.course.course_code
            booking_date = booking.date
            booking.delete()

            messages.success(
                request, 
                f"Lab booking for {course_code} on {booking_date} has been successfully canceled."
            )

    return redirect('labs:lecturer_dashboard')

# --- LECTURER PORTAL ---

@login_required
@lecturer_required
def lecturer_dashboard(request):
    courses = Course.objects.filter(lecturer=request.user)
    labs = Lab.objects.filter(is_active=True)
    time_slots = TimeSlot.objects.all()

    if request.method == 'POST':
        course_id = request.POST.get('course')
        lab_id = request.POST.get('lab')
        booking_date = request.POST.get('date')
        slot_id = request.POST.get('time_slot')

        try:
            course = Course.objects.get(pk=course_id, lecturer=request.user)
            lab = Lab.objects.get(pk=lab_id)
            slot = TimeSlot.objects.get(pk=slot_id)

            booking = ClassBooking(
                course=course,
                lab=lab,
                lecturer=request.user,
                date=booking_date,
                time_slot=slot
            )
            booking.full_clean()
            booking.save()
            messages.success(request, f"Lab '{lab.name}' locked for {course.course_code}!")
            return redirect('labs:lecturer_dashboard')
        except ValidationError as e:
            messages.error(request, e.messages[0] if isinstance(e.messages, list) else str(e))

    my_class_bookings = ClassBooking.objects.filter(lecturer=request.user, date__gte=now().date())

    context = {
        'courses': courses,
        'labs': labs,
        'time_slots': time_slots,
        'my_class_bookings': my_class_bookings,
    }
    return render(request, 'labs/lecturer_dashboard.html', context)