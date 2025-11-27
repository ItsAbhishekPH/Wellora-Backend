from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ClinicDoctorRequest, ClinicRevenue, DoctorFeeManagement, DoctorProfile, Appointment, Notification, Payment, 
    PatientProfile, MedicalReport, Reminder, Review, DoctorAvailability, 
    TimeSlot, HomeImage, Specialization, Clinic
)

User = get_user_model()


# ---------------------- USER SERIALIZER ----------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
class PatientDetailSerializer(serializers.Serializer):
    """
    Lightweight serializer for exposing basic patient info to doctors.
    Does NOT include uploaded reports.
    """

    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(allow_blank=True, required=False)
    age = serializers.IntegerField(allow_null=True, required=False)
    gender = serializers.CharField(allow_blank=True, required=False)
    phone = serializers.CharField(allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    medical_history = serializers.CharField(allow_blank=True, required=False)


# ---------------------- DOCTOR SERIALIZERS ----------------------
class DoctorSerializer(serializers.ModelSerializer):
    specialization = serializers.StringRelatedField()

    class Meta:
        model = DoctorProfile
        fields = "__all__"

# ---------------------- DOCTOR DETAIL (PUBLIC) ----------------------
from .models import DoctorProfile, ClinicDoctorRequest, DoctorAvailability


class DoctorAvailabilitySummarySerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    day = serializers.SerializerMethodField()

    class Meta:
        model = DoctorAvailability
        fields = ["clinic_name", "date", "day", "start_time", "end_time"]

    def get_day(self, obj):
        return obj.date.strftime("%A")


class DoctorDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    specialization_name = serializers.CharField(source="specialization.name", read_only=True)
    consultation_fee = serializers.DecimalField(source="fee", max_digits=8, decimal_places=2, read_only=True)
    clinics = serializers.SerializerMethodField()
    availabilities = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "id", "name", "email", "specialization_name",
            "qualification", "experience_years",
            "consultation_fee", "clinics", "availabilities", "is_verified"
        ]

    def get_clinics(self, obj):
        approved = ClinicDoctorRequest.objects.filter(doctor=obj, status="approved").select_related("clinic")
        return [
            {
                "id": r.clinic.id,
                "name": r.clinic.name,
                "address": r.clinic.address,
                "is_verified": r.clinic.is_verified,
            }
            for r in approved
        ]

    def get_availabilities(self, obj):
        qs = DoctorAvailability.objects.filter(doctor=obj, status="approved").select_related("clinic")
        grouped = {}
        for avail in qs:
            clinic_name = avail.clinic.name
            day = avail.date.strftime("%A")
            time_str = f"{avail.start_time.strftime('%H:%M')} - {avail.end_time.strftime('%H:%M')}"
            grouped.setdefault(clinic_name, []).append(f"{day} {time_str}")

        return [{"clinic": k, "schedule": v} for k, v in grouped.items()]

class DoctorProfileSerializer(serializers.ModelSerializer):
    specialization = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all(),
        required=False,
        allow_null=True
    )

    specialization_name = serializers.CharField(
        source="specialization.name",
        read_only=True
    )

    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "qualification",
            "specialization",
            "specialization_name",
            "experience_years",
            "bio",
            "fee",
            "profile_image",
            "profile_image_url",
        ]

    def get_profile_image_url(self, obj):
        """
        Returns full absolute URL for profile image
        """
        request = self.context.get("request")

        if obj.profile_image:
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        
        return None

class DoctorListSerializer(serializers.ModelSerializer):
    specialization_name = serializers.CharField(source="specialization.name", read_only=True)
    qualification = serializers.CharField(read_only=True)
    consultation_fee = serializers.SerializerMethodField()
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    profile_image_url = serializers.SerializerMethodField()

    # === NEW FIELDS ===
    clinics = serializers.SerializerMethodField()
    primary_clinic_name = serializers.SerializerMethodField()
    today_slots = serializers.SerializerMethodField()
    next_available = serializers.SerializerMethodField()
    next_available_clinic = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "full_name",
            "specialization_name",
            "qualification",
            "consultation_fee",
            "is_verified",
            "profile_image",
            "profile_image_url",

            # NEW
            "clinics",
            "primary_clinic_name",
            "today_slots",
            "next_available",
            "next_available_clinic",
        ]

    # ===========================================
    # Basic fields (already existed)
    # ===========================================
    def get_profile_image_url(self, obj):
        request = self.context.get("request")
        if obj.profile_image:
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None

    def get_consultation_fee(self, obj):
        fee_record = (
            DoctorFeeManagement.objects.filter(doctor=obj)
            .order_by("-updated_at")
            .first()
        )
        if fee_record and fee_record.consultation_fee:
            return float(fee_record.consultation_fee or 0)
        return float(obj.fee or 0)

    # ===========================================
    # NEW: Clinics (approved)
    # ===========================================
    def get_clinics(self, obj):
        links = ClinicDoctorRequest.objects.filter(
            doctor=obj, status="approved"
        ).select_related("clinic")

        return [
            {
                "id": str(link.clinic.id),
                "name": link.clinic.name,
            }
            for link in links
        ]

    # ===========================================
    # NEW: Primary clinic name
    # ===========================================
    def get_primary_clinic_name(self, obj):
        links = ClinicDoctorRequest.objects.filter(
            doctor=obj, status="approved"
        ).select_related("clinic")

        if not links:
            return None

        return links.first().clinic.name

    # ===========================================
    # NEW: Today's slot count
    # ===========================================
    def get_today_slots(self, obj):
        today = timezone.localdate()

        # approved clinics
        clinic_ids = ClinicDoctorRequest.objects.filter(
            doctor=obj, status="approved"
        ).values_list("clinic_id", flat=True)

        qs = TimeSlot.objects.filter(
            doctor=obj,
            clinic_id__in=clinic_ids,
            is_booked=False,
            start__date=today,
        ).count()

        return qs

    # ===========================================
    # NEW: Next available slot datetime
    # ===========================================
    def get_next_available(self, obj):
        now = timezone.now()

        clinic_ids = ClinicDoctorRequest.objects.filter(
            doctor=obj, status="approved"
        ).values_list("clinic_id", flat=True)

        slot = (
            TimeSlot.objects.filter(
                doctor=obj,
                clinic_id__in=clinic_ids,
                is_booked=False,
                start__gte=now,
            )
            .select_related("clinic")
            .order_by("start")
            .first()
        )

        return slot.start.isoformat() if slot else None

    # ===========================================
    # NEW: Next available clinic name
    # ===========================================
    def get_next_available_clinic(self, obj):
        now = timezone.now()

        clinic_ids = ClinicDoctorRequest.objects.filter(
            doctor=obj, status="approved"
        ).values_list("clinic_id", flat=True)

        slot = (
            TimeSlot.objects.filter(
                doctor=obj,
                clinic_id__in=clinic_ids,
                is_booked=False,
                start__gte=now,
            )
            .select_related("clinic")
            .order_by("start")
            .first()
        )

        return slot.clinic.name if slot and slot.clinic else None



class SpecializationSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Specialization
        fields = ["id", "name", "description", "icon"]

    def get_icon(self, obj):
        request = self.context.get("request")
        if obj.icon:
            return request.build_absolute_uri(obj.icon.url)
        return None
    
class DoctorScheduleSerializer(serializers.ModelSerializer):
    patient = serializers.CharField(source="patient.full_name", read_only=True)
    patient_age = serializers.SerializerMethodField()
    patient_id = serializers.IntegerField(source="patient.id", read_only=True)

    clinic = serializers.CharField(source="clinic.name", read_only=True)
    clinic_id = serializers.IntegerField(source="clinic.id", read_only=True)

    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True)
    timeslot_id = serializers.IntegerField(source="timeslot.id", read_only=True)

    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_age",
            "patient_id",
            "clinic",
            "clinic_id",
            "doctor_id",
            "timeslot_id",
            "date",
            "time",
            "status",
        ]

    def get_patient_age(self, obj):
        """
        Accurate patient age:
        - Uses stored age if present
        - Otherwise compute from DOB
        """
        try:
            profile = obj.patient.patientprofile
        except:
            return None

        if getattr(profile, "age", None):
            return profile.age

        if profile.dob:
            from datetime import date
            today = date.today()
            dob = profile.dob
            return today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )

        return None

    def get_date(self, obj):
        ts = getattr(obj, "timeslot", None)
        if not ts or not ts.start:
            return None
        local_start = timezone.localtime(ts.start)
        return local_start.date().isoformat()

    def get_time(self, obj):
        ts = getattr(obj, "timeslot", None)
        if not ts or not ts.start:
            return None
        local_start = timezone.localtime(ts.start)
        return local_start.strftime("%H:%M")


# ---------------------- CLINIC SERIALIZER ----------------------


class ClinicSerializer(serializers.ModelSerializer):
    total_doctors = serializers.SerializerMethodField()
    approved_doctors = serializers.SerializerMethodField()
    pending_requests = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)

    class Meta:
        model = Clinic
        fields = [
            "id", "owner", "owner_name", "name", "address", "phone",
            "is_verified", "created_at", "updated_at",
            "total_doctors", "approved_doctors", "pending_requests"
        ]
        read_only_fields = ["owner", "is_verified", "created_at", "updated_at"]

    # ✅ Total doctors (approved + pending)
    def get_total_doctors(self, obj):
        return ClinicDoctorRequest.objects.filter(clinic=obj).count()

    # ✅ Approved doctors → full DoctorProfile data
    def get_approved_doctors(self, obj):
        approved_requests = (
            ClinicDoctorRequest.objects.filter(clinic=obj, status="approved")
            .select_related("doctor__user", "doctor__specialization")
        )

        doctors = [r.doctor for r in approved_requests]
        if not doctors:
            return []
        return DoctorProfileSerializer(doctors, many=True).data

    # ✅ Pending requests count
    def get_pending_requests(self, obj):
        return ClinicDoctorRequest.objects.filter(clinic=obj, status="pending").count()

    # ✅ Custom create method to auto-assign logged-in owner
    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["owner"] = request.user
        validated_data["is_verified"] = False  # Always pending admin verification
        return super().create(validated_data)

# ---------------------- PAYMENT ----------------------
class PaymentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="appointment.doctor.user.full_name", read_only=True)
    clinic_name = serializers.CharField(source="appointment.clinic.name", read_only=True)
    token_no = serializers.CharField(source="appointment.token_no", read_only=True)
    appointment_date = serializers.SerializerMethodField()

    def get_appointment_date(self, obj):
        """Extracts appointment date from the slot's start DateTimeField."""
        timeslot = getattr(obj.appointment, "timeslot", None)
        if timeslot and hasattr(timeslot, "start") and timeslot.start:
            return timeslot.start.date()
        return None

    class Meta:
        model = Payment
        fields = [
            "id",
            "doctor_name",
            "clinic_name",
            "appointment_date",
            "token_no",
            "amount",
            "status",
            "payment_method",
            "transaction_id",
            "created_at",
        ]


class ClinicRevenueSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.user.full_name", read_only=True)
    appointment_token = serializers.CharField(source="appointment.token_no", read_only=True)
    appointment_date = serializers.SerializerMethodField()
    appointment_time = serializers.SerializerMethodField()

    class Meta:
        model = ClinicRevenue
        fields = [
            "id",
            "clinic", "clinic_name",
            "doctor", "doctor_name",
            "appointment", "appointment_token",
            "appointment_date", "appointment_time",
            "total_fee", "clinic_share", "doctor_earning", "created_at"
        ]

    def get_appointment_date(self, obj):
        try:
            if obj.appointment and obj.appointment.timeslot and obj.appointment.timeslot.start:
                return obj.appointment.timeslot.start.date().isoformat()
        except Exception:
            return None

    def get_appointment_time(self, obj):
        try:
            if obj.appointment and obj.appointment.timeslot and obj.appointment.timeslot.start:
                return obj.appointment.timeslot.start.time().isoformat()
        except Exception:
            return None

# ---------------------- REVIEW ----------------------
class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"


# ---------------------- NOTIFICATION ----------------------

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']  # explicit, safer
        read_only_fields = ['id', 'created_at']



# ---------------------- REMINDER ----------------------
class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = "__all__"
        read_only_fields = ["user", "created_at"]



# ---------------------- PATIENT PROFILE ----------------------
from datetime import date
from rest_framework import serializers
from .models import PatientProfile

class PatientProfileSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()

    class Meta:
        model = PatientProfile
        fields = [
            "id",
            "full_name",
            "dob",
            "age",
            "gender",
            "phone",
            "address",
            "blood_group",
            "medical_history",
        ]

    def get_age(self, obj):
        if not obj.dob:
            return None

        today = date.today()
        age = today.year - obj.dob.year - (
            (today.month, today.day) < (obj.dob.month, obj.dob.day)
        )
        return age



# ---------------------- MEDICAL REPORT ----------------------

class MedicalReportUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalReport
        fields = ["file"]   # only file field needed for upload

class MedicalReportSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = MedicalReport
        fields = ["id", "file", "uploaded_at"]

    def get_file(self, obj):
        request = self.context.get("request")
        if obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None



# ---------------------- HOME IMAGE ----------------------
class HomeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeImage
        fields = "__all__"


# ---------------------- DOCTOR AVAILABILITY ----------------------
class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.user.full_name", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    clinic_id = serializers.IntegerField(source="clinic.id", read_only=True)

    class Meta:
        model = DoctorAvailability
        fields = [
            "id",
            "doctor", "doctor_name",
            "clinic_id", "clinic_name",
            "date", "start_time", "end_time",
            "slot_duration", "status",
            "recurrence_group", "created_at",
            "fee",  # ✅ Added fee field
        ]
        read_only_fields = ["recurrence_group", "status", "created_at"]
        extra_kwargs = {
            "doctor": {"required": False, "read_only": True},  # ✅ fix
            "clinic": {"required": False},                     # ✅ handled in view
            "fee": {"required": False},                        # ✅ optional fee
        }

class DoctorAvailabilitySummarySerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    day = serializers.SerializerMethodField()

    class Meta:
        model = DoctorAvailability
        fields = ["clinic_name", "date", "day", "start_time", "end_time"]

    def get_day(self, obj):
        return obj.date.strftime("%A")



class DoctorFeeManagementSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    clinic_id = serializers.IntegerField(source="clinic.id", read_only=True)

    class Meta:
        model = DoctorFeeManagement
        fields = [
            "id",
            "doctor",
            "clinic",
            "clinic_id",
            "clinic_name",
            "consultation_fee",
            "clinic_share_percent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["clinic_share_percent", "created_at", "updated_at"]

# ---------------------- CLINIC DOCTOR REQUEST ----------------------
class ClinicDoctorRequestSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.user.full_name", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)

    class Meta:
        model = ClinicDoctorRequest
        fields = ["id", "doctor", "doctor_name", "clinic", "clinic_name", "status", "created_at"]
        read_only_fields = ["status", "created_at"]



# ---------------------- APPOINTMENT ----------------------
class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.user.full_name", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    patient_age = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "doctor_name",
            "clinic_name",
            "patient_name",
            "patient_id",
            "patient_age",
            "token_no",
            "amount",
            "paid",
            "status",
            "date",
            "time",
        ]

    def get_date(self, obj):
        ts = getattr(obj, "timeslot", None)
        if not ts or not ts.start:
            return None
        local_start = timezone.localtime(ts.start)
        return local_start.date().isoformat()

    def get_time(self, obj):
        ts = getattr(obj, "timeslot", None)
        if not ts or not ts.start:
            return None
        local_start = timezone.localtime(ts.start)
        return local_start.strftime("%H:%M")

    def get_patient_name(self, obj):
        return getattr(obj.patient, "full_name", getattr(obj.patient, "email", None))

    def get_patient_id(self, obj):
        return obj.patient.id if obj.patient else None

    def get_patient_age(self, obj):
        """
        Accurate patient age calculation:
        - If PatientProfile.age exists → return it
        - Else compute from DOB
        """
        try:
            profile = obj.patient.patientprofile
        except:
            return None

        # If age stored directly
        if getattr(profile, "age", None):
            return profile.age

        # Compute from DOB
        if profile.dob:
            from datetime import date
            today = date.today()
            dob = profile.dob
            return today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )

        return None
