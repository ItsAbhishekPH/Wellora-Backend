# =========================
# ✅ WELLORA - API ROUTES (Clean & Ordered)
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'reviews', views.ReviewViewSet, basename='review')

# =========================
# AUTH / LOGIN / OTP ROUTES
# =========================
auth_patterns = [
    path('check-role/', views.check_role),
    path('send-otp/', views.send_otp),
    path('verify-otp/', views.verify_otp),
    path('login/', views.password_login),
]

auth_patterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('check-role/', views.check_role, name='check-role'),
    path('password-login/', views.password_login, name='password-login'),
    path('send-otp/', views.send_otp, name='send-otp'),
    path('verify-otp/', views.verify_otp, name='verify-otp'),

   
]


urlpatterns = [
   


    # AUTH
    # =========================
    path("auth/check-role/", views.check_role, name="check-role"),
    path('auth/', include(auth_patterns)),


    # =========================
    # DOCTORS & AVAILABILITY
    # =========================
    # ⚠️ must come BEFORE <int:pk> to avoid route conflicts
    path("doctors/<int:doctor_id>/available-slots/", views.DoctorAvailableSlotsView.as_view(), name="doctor-available-slots"),
    path("doctors/<int:doctor_id>/availability/", views.DoctorAvailableSlotsView.as_view(), name="doctor-availability-by-date"),
    path("doctors/<int:doctor_id>/available-dates/", views.DoctorAvailableDatesView.as_view()),
    path('doctors/', views.DoctorListView.as_view(), name='doctor-list'),
    path('doctors/<int:pk>/', views.DoctorDetailView.as_view(), name='doctor-detail'),
    path('doctor/profile/', views.DoctorProfileView.as_view(), name='doctor-profile'),

    # Doctor availability management
    path('doctor/availability/', views.DoctorAvailabilityView.as_view(), name='doctor-availability'),
    path('doctor/availability/recurring/', views.DoctorAvailabilityBulkCreateView.as_view(), name='doctor-availability-recurring'),
    path('doctor/availability/delete/', views.DoctorAvailabilityBulkDeleteView.as_view(), name='doctor-availability-delete'),
    path('doctor/fee-management/', views.DoctorFeeManagementView.as_view(), name='doctor-fee-management'),
    path("doctor/<int:doctor_id>/clinics/", views.DoctorClinicsView.as_view(), name="doctor-clinics"),
    path('specializations/', views.SpecializationListView.as_view(), name='specialization-list'),
    path("doctor/earnings-summary/", views.DoctorEarningsSummaryView.as_view(), name="doctor-earnings-summary"),


    # =========================
    # CLINIC SYSTEM
    # =========================
    path('clinics/', views.ClinicListView.as_view(), name='clinic-list'),
    path('clinics/<int:pk>/', views.ClinicDetailView.as_view(), name='clinic-detail'),
    path('clinic/add/', views.add_clinic, name='add-clinic'),
    path('clinic/doctor-requests/', views.ClinicOwnerRequestListView.as_view(), name='clinic-owner-requests'),
    path('clinic/doctor-requests/<int:pk>/action/', views.ClinicDoctorApprovalView.as_view(), name='clinic-doctor-request-action'),
    path('clinic/availability/<int:pk>/action/', views.ClinicApproveAvailabilityView.as_view(), name='clinic-availability-action'),
    path('clinic/appointments/', views.ClinicAppointmentsView.as_view(), name='clinic-appointments'),
    path('clinic/add-offline-appointment/', views.AddOfflineAppointmentView.as_view(), name='add-offline-appointment'),
    path('clinic/revenues/', views.ClinicRevenueListView.as_view(), name='clinic-revenues'),
    path('clinic/revenues/summary/', views.ClinicRevenueSummaryView.as_view(), name='clinic-revenues-summary'),

    # Doctor join clinic requests
    path('clinic-doctor-requests/', views.ClinicDoctorRequestCreateView.as_view(), name='clinic-doctor-request-create'),
    path('doctor/clinic-requests/', views.DoctorClinicRequestListView.as_view(), name='doctor-clinic-requests'),
    path('doctor/approved-clinics/', views.DoctorApprovedClinicsView.as_view(), name='doctor-approved-clinics'),
    path("clinic/doctor-requests/<int:pk>/action/", views.ClinicDoctorApprovalView.as_view(), name="clinic-doctor-request-action"),

    # Doctor Schedule
    path("doctor/schedule/", views.DoctorScheduleListView.as_view(), name="doctor-schedule"),
    path("doctor/schedule/summary/", views.DoctorScheduleSummaryView.as_view(), name="doctor-schedule-summary"),


    # =========================
    # APPOINTMENTS & PAYMENTS
    # =========================
    path('appointments/', views.AppointmentListView.as_view(), name='appointment-list'),
    path('appointments/create/', views.AppointmentCreateView.as_view(), name='appointment-create'),
    path('appointments/<int:pk>/cancel/', views.cancel_appointment, name='appointment-cancel'),
    path("doctor/appointments/", views.DoctorAppointmentsListView.as_view(), name="doctor-appointments"),
    path('payment/create-order/', views.create_payment_order, name='create-payment-order'),
    path('payment/verify/', views.verify_payment, name='verify-payment'),
    

    # =========================
    # PATIENT DASHBOARD
    # =========================
    path('patient/profile/', views.PatientProfileView.as_view(), name='patient-profile'),
    path('patient/reports/', views.MedicalReportListView.as_view(), name='patient-reports'),
    path('patient/reports/upload/', views.UploadMedicalReportView.as_view(), name='upload-report'),
    path('patient/reports/<int:pk>/delete/', views.DeleteMedicalReportView.as_view(), name='delete-report'),
    path('reminders/', views.ReminderListView.as_view(), name='reminder-list'),
    path('reminder/add/', views.AddReminderView.as_view(), name='add-reminder'),
    path('patient/<int:patient_id>/details/', views.PatientDetailView.as_view(), name='patient-details'),
    path('doctor/book-followup/', views.DoctorBookFollowupView.as_view(), name='doctor-book-followup'),
    path("analyze-symptoms/", views.analyze_symptoms),
    path("chatbot/", views.homepage_chatbot),

  



    # =========================
    # STATIC / HOME
    # =========================
    path('home-images/', views.HomeImageListView.as_view(), name='home-images'),

    # =========================
    # ROUTER (notifications, payments, reviews)
    # =========================
    path('', include(router.urls)),
]
