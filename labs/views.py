from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.urls import reverse

from labs.models import Lab, Workstation, TimeSlot, ClassBooking, WorkstationReservation, MaintenanceTicket
from labs.decorators import student_required, lecturer_required
from academics.models import Course

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
    labs = Lab.objects.filter(is_active=True).prefetch_related('workstations')
    time_slots = TimeSlot.objects.all()
    
    selected_lab_id = request.GET.get('lab')
    selected_slot_id = request.GET.get('slot')
    selected_date = request.GET.get('date', str(now().date()))

    selected_lab = None
    workstations_data = []

    if selected_lab_id:
        selected_lab = get_object_or_404(Lab, pk=selected_lab_id)
        active_class = None

        if selected_slot_id:
            active_class = ClassBooking.objects.filter(
                lab=selected_lab,
                date=selected_date,
                time_slot_id=selected_slot_id
            ).first()

        for seat in selected_lab.workstations.all():
            is_reserved = WorkstationReservation.objects.filter(
                workstation=seat,
                date=selected_date,
                time_slot_id=selected_slot_id
            ).exists()

            if seat.status == Workstation.Status.MAINTENANCE:
                seat_status = 'MAINTENANCE'
            elif is_reserved:
                seat_status = 'OCCUPIED'
            elif active_class:
                is_enrolled = active_class.course.enrollments.filter(student=request.user).exists()
                seat_status = 'AVAILABLE' if is_enrolled else 'CLASS_LOCKED'
            else:
                seat_status = 'AVAILABLE'

            workstations_data.append({'seat': seat, 'ui_status': seat_status})

    my_reservations = WorkstationReservation.objects.filter(student=request.user, date__gte=now().date())

    context = {
        'labs': labs,
        'time_slots': time_slots,
        'selected_lab': selected_lab,
        'selected_date': selected_date,
        'selected_slot_id': selected_slot_id,
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
    if request.method == 'POST':
        workstation = get_object_or_404(Workstation, pk=seat_id)
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority', 'MEDIUM')

        ticket = MaintenanceTicket(
            workstation=workstation,
            reported_by=request.user,
            title=title,
            description=description,
            priority=priority,
            status=MaintenanceTicket.Status.OPEN
        )
        ticket.save()
        messages.warning(request, f"Fault reported for Seat #{workstation.seat_number}. Seat set to maintenance.")

    return redirect('labs:student_dashboard')


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