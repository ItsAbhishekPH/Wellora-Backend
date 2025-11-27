from django.contrib import admin
from .models import (
    ClinicRevenue, User, DoctorProfile, PatientProfile, Clinic, ClinicDoctorRequest,
    DoctorAvailability, Appointment, Payment, Review, MedicalReport,
    Reminder, Notification, HomeImage, Specialization, Symptom, TimeSlot
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'full_name', 'role', 'is_active', 'is_verified', 'is_approved']
    search_fields = ("full_name", "email", "role")
    list_filter = ("role", "is_active", "is_approved")
    actions = ["approve_users", "reject_users"]

    @admin.action(description="✅ Approve selected users")
    def approve_users(self, request, queryset):
        updated = queryset.filter(role="clinic_owner").update(
            is_approved=True,
            is_active=True  # ✅ Activate on approval so they can log in
        )
        self.message_user(request, f"{updated} clinic owner(s) approved successfully.")

    @admin.action(description="❌ Reject selected users")
    def reject_users(self, request, queryset):
        updated = queryset.filter(role="clinic_owner").update(
            is_approved=False,
            is_active=False  # ✅ Deactivate on rejection
        )
        self.message_user(request, f"{updated} clinic owner(s) rejected successfully.")


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "address", "phone", "is_verified")
    search_fields = ("name", "address", "owner__email")
    list_filter = ("is_verified",)
    actions = ["approve_clinic", "reject_clinic"]

    @admin.action(description="✅ Approve selected clinics")
    def approve_clinic(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"{updated} clinic(s) approved successfully.")

    @admin.action(description="❌ Reject selected clinics")
    def reject_clinic(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f"{updated} clinic(s) rejected successfully.")


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "qualification", "experience_years", "fee", "is_verified")
    search_fields = ("user__full_name", "specialization__name")
    list_filter = ("is_verified", "specialization")
    actions = ["approve_doctor", "reject_doctor"]

    @admin.action(description="✅ Approve selected doctors")
    def approve_doctor(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"{updated} doctor(s) approved successfully.")

    @admin.action(description="❌ Reject selected doctors")
    def reject_doctor(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f"{updated} doctor(s) rejected successfully.")


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "dob", "blood_group", "age")
    search_fields = ("user__full_name", "blood_group")


@admin.register(ClinicDoctorRequest)
class ClinicDoctorRequestAdmin(admin.ModelAdmin):
    list_display = ("doctor", "clinic", "status", "created_at")
    list_filter = ("status", "clinic")
    search_fields = ("doctor__user__full_name", "clinic__name")


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("doctor", "clinic", "date", "start_time", "end_time", "status")
    list_filter = ("status", "clinic", "doctor")
    search_fields = ("doctor__user__full_name", "clinic__name")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "clinic", "status", "created_at", "paid")
    list_filter = ("status", "paid")
    search_fields = ("patient__user__full_name", "doctor__user__full_name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("appointment", "order_id", "amount", "status", "payment_method", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("order_id",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("doctor", "user", "rating", "short_comment", "created_at")
    list_filter = ("rating", "doctor")
    search_fields = ("doctor__user__full_name", "user__full_name", "comment")

    def short_comment(self, obj):
        return obj.comment[:20] + "..." if obj.comment else "—"
    short_comment.short_description = "Comment"



@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display = ('patient', 'file', 'uploaded_at')


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "frequency", "created_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "message", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__full_name", "message")


@admin.register(HomeImage)
class HomeImageAdmin(admin.ModelAdmin):
    list_display = ("title", "image", "description")


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ("name", "specialization")


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("doctor", "clinic", "start", "end", "is_booked")
    list_filter = ("is_booked",)

@admin.register(ClinicRevenue)
class ClinicRevenueAdmin(admin.ModelAdmin):
    list_display = ("clinic", "doctor", "appointment", "total_fee", "clinic_share", "doctor_earning", "created_at")
    list_filter = ("clinic", "doctor")
    search_fields = ("clinic__name", "doctor__user__full_name", "appointment__token_no")