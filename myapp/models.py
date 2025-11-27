from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import uuid, random
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import traceback, sys

# =========================================================
# 🔹 USER MODEL & AUTH MANAGEMENT
# =========================================================

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)
        role = extra_fields.get("role", User.ROLE_PATIENT)

        # clinic owners inactive until approval
        if role == User.ROLE_CLINIC_OWNER:
            extra_fields.setdefault("is_active", False)
            extra_fields.setdefault("is_approved", False)
        else:
            extra_fields.setdefault("is_active", True)
            extra_fields.setdefault("is_approved", True)

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.ROLE_ADMIN)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_approved", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    objects = UserManager()

    ROLE_PATIENT = "patient"
    ROLE_DOCTOR = "doctor"
    ROLE_CLINIC_OWNER = "clinic_owner"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_PATIENT, "Patient"),
        (ROLE_DOCTOR, "Doctor"),
        (ROLE_CLINIC_OWNER, "Clinic Owner"),
        (ROLE_ADMIN, "Admin"),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PATIENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.role})"


# =========================================================
# 🔹 EMAIL OTP
# =========================================================

class EmailOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self, ttl_minutes=10):
        if self.verified:
            return False
        return timezone.now() < (self.created_at + timedelta(minutes=ttl_minutes))

    @staticmethod
    def generate_otp(email):
        code = f"{random.randint(0, 999999):06d}"
        EmailOTP.objects.create(email=email, code=code)
        return code


# =========================================================
# 🔹 SPECIALIZATION / SYMPTOM
# =========================================================

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='specializations/', blank=True, null=True)

    def __str__(self):
        return self.name


class Symptom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name="symptoms")

    def __str__(self):
        return f"{self.name} ({self.specialization.name})"


# =========================================================
# 🔹 CLINIC
# =========================================================

class Clinic(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clinics")
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="doctor_profile")
    profile_image = models.ImageField(upload_to="doctor_profiles/", blank=True, null=True)
    specialization = models.ForeignKey(Specialization, on_delete=models.SET_NULL, null=True, blank=True)
    qualification = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    bio = models.TextField(blank=True, null=True)
    clinic_name = models.CharField(max_length=255, blank=True, null=True)  # legacy support
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.full_name


# =========================================================
# 🔹 CLINIC DOCTOR REQUEST
# =========================================================

class ClinicDoctorRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    doctor = models.ForeignKey("DoctorProfile", on_delete=models.CASCADE, related_name="clinic_requests")
    clinic = models.ForeignKey("Clinic", on_delete=models.CASCADE, related_name="doctor_requests")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("doctor", "clinic")

    def __str__(self):
        return f"{self.doctor.user.full_name} → {self.clinic.name} [{self.status}]"


# =========================================================
# 🔹 AVAILABILITY & TIMESLOTS
# =========================================================

class DoctorAvailability(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    doctor = models.ForeignKey("DoctorProfile", on_delete=models.CASCADE, related_name="availabilities")
    clinic = models.ForeignKey("Clinic", on_delete=models.CASCADE, related_name="availabilities")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=30)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    recurrence_group = models.UUIDField(null=True, blank=True)

    class Meta:
        unique_together = ("doctor", "clinic", "date", "start_time", "end_time")

    def __str__(self):
        return f"{self.doctor.user.full_name} - {self.clinic.name} - {self.date}"


class TimeSlot(models.Model):
    doctor = models.ForeignKey("DoctorProfile", on_delete=models.CASCADE)
    clinic = models.ForeignKey("Clinic", on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doctor.user.full_name} ({self.start})"


class WeeklyAvailability(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=9)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)


# =========================================================
# 🔹 DOCTOR FEE MANAGEMENT
# =========================================================

class DoctorFeeManagement(models.Model):
    doctor = models.ForeignKey("DoctorProfile", on_delete=models.CASCADE, related_name="fee_details")
    clinic = models.ForeignKey("Clinic", on_delete=models.CASCADE, related_name="doctor_fees")
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    clinic_share_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    clinic_fixed_fee = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("doctor", "clinic")

    def __str__(self):
        return f"{self.doctor.user.full_name} - {self.clinic.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # sync DoctorProfile fee
        try:
            if self.doctor and self.consultation_fee:
                if self.doctor.fee != self.consultation_fee:
                    self.doctor.fee = self.consultation_fee
                    self.doctor.save(update_fields=["fee"])
        except:
            pass

    def calculate_clinic_share(self):
        fee = Decimal(self.consultation_fee or 0)
        if self.clinic_fixed_fee is not None:
            fixed = Decimal(self.clinic_fixed_fee)
            return min(fixed, fee)
        percent = Decimal(self.clinic_share_percent)
        return (fee * percent) / Decimal("100.0")

    def calculate_doctor_earning(self):
        clinic_share = self.calculate_clinic_share()
        return Decimal(self.consultation_fee) - clinic_share


# =========================================================
# 🔹 APPOINTMENT / PAYMENT / REVIEW
# =========================================================

class Appointment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey("DoctorProfile", on_delete=models.CASCADE, related_name="appointments")
    clinic = models.ForeignKey("Clinic", on_delete=models.CASCADE, null=True, blank=True)
    timeslot = models.ForeignKey("TimeSlot", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    paid = models.BooleanField(default=False)
    token_no = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.patient.full_name} -> {self.doctor.user.full_name}"


class Payment(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
    payment_method = models.CharField(max_length=50, default="razorpay")
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment.patient.full_name} - {self.amount}"


class Review(models.Model):
    doctor = models.ForeignKey("DoctorProfile", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} rated {self.doctor.user.full_name}"


# =========================================================
# 🔹 CLINIC REVENUE
# =========================================================

class ClinicRevenue(models.Model):
    clinic = models.ForeignKey("Clinic", on_delete=models.CASCADE, related_name="revenues")
    doctor = models.ForeignKey("DoctorProfile", on_delete=models.CASCADE, related_name="revenues")
    appointment = models.ForeignKey("Appointment", on_delete=models.CASCADE, related_name="revenue_record")
    total_fee = models.DecimalField(max_digits=8, decimal_places=2)
    clinic_share = models.DecimalField(max_digits=8, decimal_places=2)
    doctor_earning = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.clinic.name} ← {self.doctor.user.full_name}"


# =========================================================
# 🔹 PATIENT PROFILE / REPORT / REMINDER
# =========================================================

class PatientProfile(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
        ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True)
    dob = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, blank=True, null=True, default=None)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.user.full_name


class MedicalReport(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="reports")
    file = models.FileField(upload_to="reports/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report of {self.patient.full_name}"


class Reminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    appointment = models.ForeignKey("Appointment", on_delete=models.CASCADE, related_name="reminders", null=True, blank=True)
    message = models.CharField(max_length=255)
    frequency = models.CharField(max_length=50, default="Once")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reminder for {self.user.full_name}"


# =========================================================
# 🔹 HOME IMAGE & NOTIFICATION
# =========================================================

class HomeImage(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to="home_images/")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.email}"


# =========================================================
# 🔹 SIGNALS — PAYMENT → CLINIC REVENUE
# =========================================================

@receiver(post_save, sender=Payment)
def myapp_handle_payment_completed(sender, instance, created, **kwargs):
    """
    Create ClinicRevenue for successful payments.
    """
    try:
        if not instance:
            return

        paid_statuses = {"paid", "success", "completed"}
        if (instance.status or "").lower() not in paid_statuses:
            return

        appt = instance.appointment
        if not appt:
            return

        # Prevent duplicate
        if ClinicRevenue.objects.filter(appointment=appt).exists():
            return

        clinic = appt.clinic
        doctor = appt.doctor
        total_fee = Decimal(instance.amount or appt.amount or 0)

        clinic_share = Decimal("0.00")
        doctor_earning = total_fee

        try:
            fee_record = DoctorFeeManagement.objects.filter(
                doctor=doctor, clinic=clinic
            ).order_by("-updated_at").first()
        except:
            fee_record = None

        if fee_record:
            try:
                clinic_share = fee_record.calculate_clinic_share()
            except:
                clinic_share = Decimal("0.00")

            clinic_share = min(clinic_share, total_fee)
            doctor_earning = total_fee - clinic_share

        with transaction.atomic():
            ClinicRevenue.objects.create(
                clinic=clinic,
                doctor=doctor,
                appointment=appt,
                total_fee=total_fee,
                clinic_share=clinic_share,
                doctor_earning=doctor_earning,
            )

            if appt.timeslot:
                ts = appt.timeslot
                ts.is_booked = True
                ts.save(update_fields=["is_booked"])

            appt.paid = True
            appt.save(update_fields=["paid"])

    except Exception:
        traceback.print_exc(file=sys.stderr)

