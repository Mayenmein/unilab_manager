from django.urls import path
from labs import views

app_name = 'labs'

urlpatterns = [
    path('', views.root_redirect_view, name='root_redirect'),

    path('class-booking/<uuid:booking_id>/cancel/', views.cancel_class_booking, name='cancel_class_booking'),
    
    # Student Routes
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/reserve/<uuid:seat_id>/', views.reserve_workstation, name='reserve_seat'),
    path('student/report-fault/<uuid:seat_id>/', views.report_fault, name='report_fault'),

    # Lecturer Routes
    path('lecturer/', views.lecturer_dashboard, name='lecturer_dashboard'),
]