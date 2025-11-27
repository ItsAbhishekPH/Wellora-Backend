# ===============================================
# ✅ WELLORA — Views (Circular Import Safe Imports)
# ===============================================

import json
import os
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core.exceptions import ValidationError


from rest_framework import generics, status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from .models import ClinicRevenue, Clinic
from .serializers import ClinicRevenueSerializer, MedicalReportUploadSerializer
from openai import OpenAI

client = OpenAI()

import razorpay
from datetime import datetime, timedelta, date as date_cls
from decimal import Decimal
import uuid
import re

# =========================
# 🧩 LOCAL IMPORTS (safe order)
# =========================

# 🧩 First import models
from .models import (
    Clinic,
    ClinicDoctorRequest,
    DoctorFeeManagement,
    DoctorProfile,
    Appointment,
    EmailOTP,
    Notification,
    Payment,
    PatientProfile,
    MedicalReport,
    Reminder,
    Review,
    Symptom,
    TimeSlot,
    DoctorAvailability,
    Specialization,
    HomeImage,
)

# 🧩 Then import utils
from .utils import send_otp_via_email

# 🧩 Finally import serializers (AFTER models)
from .serializers import (
    DoctorScheduleSerializer,
    PatientDetailSerializer,
    SpecializationSerializer,
    UserSerializer,
    ClinicDoctorRequestSerializer,
    ClinicSerializer,
    DoctorDetailSerializer,
    DoctorFeeManagementSerializer,
    DoctorListSerializer,
    NotificationSerializer,
    PaymentSerializer,
    ReviewSerializer,
    DoctorSerializer,
    AppointmentSerializer,
    PatientProfileSerializer,
    MedicalReportSerializer,
    ReminderSerializer,
    HomeImageSerializer,
    DoctorAvailabilitySerializer,
    DoctorProfileSerializer,
)

# 💳 Razorpay Initialization
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# ✅ Custom user model
User = get_user_model()

# -------------------------
# Register view
# -------------------------
import re
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import User, Clinic, DoctorProfile, PatientProfile, Specialization
from .serializers import UserSerializer

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        role = data.get("role")
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        full_name = data.get("full_name")
        specialization_name = data.get("specialization_name", "")
        clinic_name = data.get("clinic_name", "")
        clinic_address = data.get("clinic_address", "")

        # ======== BASIC VALIDATIONS ========
        if not email or not password or not full_name or not role:
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered."}, status=status.HTTP_400_BAD_REQUEST)

        # ======== DOCTOR SIGNUP ========
        if role == "doctor":
            if not specialization_name:
                return Response({"error": "Specialization is required for doctors."}, status=status.HTTP_400_BAD_REQUEST)

            specialization, _ = Specialization.objects.get_or_create(name=specialization_name.strip())

            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=User.ROLE_DOCTOR,
                is_active=True,
                is_approved=True,  # ✅ no admin approval needed
            )

            DoctorProfile.objects.create(user=user, specialization=specialization,is_verified=False)
            return Response(
                {"message": "Doctor registered successfully."},
                status=status.HTTP_201_CREATED
            )

        # ======== PATIENT SIGNUP ========
        elif role == "patient":
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=User.ROLE_PATIENT,
                is_active=True,
                is_approved=True,
            )
            PatientProfile.objects.create(user=user)
            return Response(
                {"message": "Patient registered successfully."},
                status=status.HTTP_201_CREATED
            )
# ======== CLINIC OWNER SIGNUP ========
        elif role == "clinic_owner":
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=User.ROLE_CLINIC_OWNER,
                is_active=False,   # ✅ cannot log in until admin approval
                is_approved=False, # ✅ must be approved manually
            )

            return Response(
                {
                    "message": "Clinic owner registered successfully. Please wait for admin approval before logging in."
                },
                status=status.HTTP_201_CREATED,
            )
        
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.response import Response
from .models import Clinic
from .serializers import ClinicSerializer  # make sure you have this

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_clinic(request):
    user = request.user

    # 🔒 Only clinic owners can add clinics
    if user.role != "clinic_owner":
        return Response({"error": "Only clinic owners can add clinics."}, status=status.HTTP_403_FORBIDDEN)

    name = request.data.get("name")
    address = request.data.get("address")
    phone = request.data.get("phone", "")

    if not name or not address:
        return Response({"error": "Name and address are required."}, status=status.HTTP_400_BAD_REQUEST)

    clinic = Clinic.objects.create(
        owner=user,
        name=name,
        address=address,
        phone=phone,
        is_verified=False,  # 🕒 Admin verifies later
    )

    return Response(
        {"message": "Clinic created successfully. Waiting for admin verification.", "clinic": ClinicSerializer(clinic).data},
        status=status.HTTP_201_CREATED,
    )
#------Login------#

@api_view(["POST"])
@permission_classes([AllowAny])
def check_role(request):
    email = request.data.get("email", "").strip().lower()

    if not email:
        return Response({"role": "not_found"})

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"role": "not_found"})

    return Response({"role": user.role})

@api_view(["POST"])
@permission_classes([AllowAny])
def send_otp(request):
    email = request.data.get("email", "").strip().lower()

    if not email:
        return Response({"error": "Email is required"}, status=400)

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "No user found with this email"}, status=404)

    otp = EmailOTP.generate_otp(email)

    try:
        # Try sending email
        send_otp_via_email(email, otp)
        print(f"OTP sent to email: {otp}")
        return Response({"message": f"OTP sent to {email}"}, status=200)

    except Exception:
        # Fallback → Print in console
        print("\n====================")
        print("FAKE EMAIL DETECTED")
        print(f"OTP for {email} = {otp}")
        print("====================\n")

        return Response({"message": "OTP generated (check Django console)"}, status=200)

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get("email", "").strip().lower()
    code = request.data.get("code")

    if not email or not code:
        return Response({"error": "Email and OTP are required"}, status=400)

    otp_obj = EmailOTP.objects.filter(email=email, code=code).last()
    if not otp_obj or not otp_obj.is_valid():
        return Response({"error": "Invalid or expired OTP"}, status=400)

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "User not found"}, status=404)

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "role": user.role,
        "username": user.full_name,
        "profileCompleted": True
    }, status=200)

@api_view(["POST"])
@permission_classes([AllowAny])
def password_login(request):
    email = request.data.get("email", "").strip().lower()
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Email and password required"}, status=400)

    user = authenticate(email=email, password=password)

    if not user:
        return Response({"error": "Invalid email or password"}, status=400)

    # Clinic owner admin-approval removed → always allow
    if user.role == User.ROLE_CLINIC_OWNER:
        user.is_active = True
        user.is_approved = True
        user.save()

    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "role": user.role,
        "username": user.full_name,
        "profileCompleted": True
    }, status=200)





# -------------------------
# Admin: list & approve doctors
# -------------------------
class DoctorApprovalView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        pending_doctors = DoctorProfile.objects.filter(is_verified=False)
        serializer = DoctorSerializer(pending_doctors, many=True)
        return Response(serializer.data)

    def post(self, request, doctor_id):
        action = request.data.get("action")
        doctor = DoctorProfile.objects.filter(id=doctor_id).first()
        if not doctor:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)
        if action == "approve":
            doctor.is_verified = True
            doctor.save()
            return Response({"message": f"Doctor {doctor.user.email} approved"}, status=status.HTTP_200_OK)
        elif action == "reject":
            email = doctor.user.email
            doctor.user.delete()
            doctor.delete()
            return Response({"message": f"Doctor {email} rejected and removed"}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)


# -------------------------
# Doctors list & appointments
# -------------------------
class DoctorListView(generics.ListAPIView):
    serializer_class = DoctorListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = DoctorProfile.objects.filter(is_verified=True)
        spec = self.request.GET.get("specialization")
        if spec:
            qs = qs.filter(specialization_id=spec)
        return qs

    def get_serializer_context(self):
        return {"request": self.request}




class AppointmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        doctor_id = data.get("doctor")
        clinic_id = data.get("clinic")
        timeslot_id = data.get("timeslot")

        if not all([doctor_id, clinic_id, timeslot_id]):
            return Response(
                {"error": "Doctor, clinic, and timeslot are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = get_object_or_404(DoctorProfile, id=doctor_id)
        clinic = get_object_or_404(Clinic, id=clinic_id)
        timeslot = get_object_or_404(TimeSlot, id=timeslot_id, is_booked=False)

        timeslot.is_booked = True
        timeslot.save()

        today = timezone.now().date()

        # Generate a per-doctor-per-day counter
        same_day_count = Appointment.objects.filter(
            doctor=doctor, timeslot__start__date=today
        ).count() + 1

        # Add short random suffix for uniqueness
        short_uid = uuid.uuid4().hex[:4].upper()
        token_no = f"T{same_day_count}-{short_uid}"

        try:
            appointment = Appointment.objects.create(
                patient=request.user,
                doctor=doctor,
                clinic=clinic,
                timeslot=timeslot,
                token_no=token_no,
                amount=doctor.fee or 0,
                paid=False,
            )
        except IntegrityError:
            # In case of rare collision, regenerate a new token
            token_no = f"T{same_day_count}-{uuid.uuid4().hex[:4].upper()}"
            appointment = Appointment.objects.create(
                patient=request.user,
                doctor=doctor,
                clinic=clinic,
                timeslot=timeslot,
                token_no=token_no,
                amount=doctor.fee or 0,
                paid=False,
            )

        return Response(
            {
                "message": "Appointment booked successfully",
                "token_no": appointment.token_no,
                "doctor": doctor.id,
                "clinic": clinic.id,
                "timeslot": timeslot.id,
                "amount": float(doctor.fee or 0),
            },
            status=status.HTTP_201_CREATED,
        )

# Doctor Detail View (Public)
class DoctorDetailView(generics.RetrieveAPIView):
    queryset = DoctorProfile.objects.select_related("user", "specialization")
    serializer_class = DoctorDetailSerializer  # ✅ Use the new one
    permission_classes = [permissions.AllowAny]



# -------------------------
# Payments (Razorpay) - consolidated & fixed (token_no flow)
# -------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment_order(request):
    """
    Create a Razorpay order for the appointment identified by token_no.
    Expects JSON body: { "token_no": "<token_no>" }
    """
    try:
        token_no = request.data.get("token_no")
        if not token_no:
            return Response({"error": "Token number is required"}, status=status.HTTP_400_BAD_REQUEST)

        appointment = Appointment.objects.get(token_no=token_no, patient=request.user)
        fee_decimal = Decimal(appointment.doctor.fee or 0)
        amount_paise = int((fee_decimal * Decimal("100")).quantize(Decimal("1")))

        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
        })

        Payment.objects.create(
            appointment=appointment,
            order_id=order.get("id"),
            amount=fee_decimal,
            status="pending",
            payment_method="razorpay",
        )

        return Response({
            "success": True,
            "order_id": order.get("id"),
            "amount": amount_paise,
            "currency": "INR",
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "token_no": token_no,
        }, status=status.HTTP_201_CREATED)

    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found for this token number"}, status=status.HTTP_404_NOT_FOUND)
    except razorpay.errors.BadRequestError as e:
        return Response({"error": f"Razorpay error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print("Error creating Razorpay order:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """
    Verify Razorpay payment signature and update local payment & appointment.
    Also record clinic and doctor revenue split after successful payment.
    """
    try:
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({"error": "Incomplete payment data"}, status=status.HTTP_400_BAD_REQUEST)

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        payment = Payment.objects.filter(order_id=razorpay_order_id).first()
        if not payment:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        payment.transaction_id = razorpay_payment_id
        payment.status = "completed"
        payment.save()

        appointment = payment.appointment
        appointment.paid = True
        appointment.status = "confirmed"
        appointment.save()

        from .models import DoctorFeeManagement, ClinicRevenue

        try:
            fee_info = DoctorFeeManagement.objects.get(
                doctor=appointment.doctor,
                clinic=appointment.clinic
            )
            total_fee = Decimal(payment.amount)  # actual fee paid

            # Model B: fixed clinic fee
            if fee_info.clinic_fixed_fee:
                clinic_share = Decimal(fee_info.clinic_fixed_fee)
                if clinic_share > total_fee:
                    clinic_share = total_fee  # safety rule
                doctor_earning = total_fee - clinic_share

            else:
                # Model A: percentage
                percent = Decimal(fee_info.clinic_share_percent or 0)
                clinic_share = (total_fee * percent) / Decimal("100")
                doctor_earning = total_fee - clinic_share
            ClinicRevenue.objects.create(
                clinic=appointment.clinic,
                doctor=appointment.doctor,
                appointment=appointment,
                total_fee=fee_info.consultation_fee,
                clinic_share=clinic_share,
                doctor_earning=doctor_earning,
            )

            print(f"✅ Revenue recorded: Clinic ₹{clinic_share}, Doctor ₹{doctor_earning}")

        except DoctorFeeManagement.DoesNotExist:
            print("⚠️ Doctor fee not configured for this clinic. Revenue not recorded.")

        return Response(
            {"success": True, "message": "Payment verified and revenue recorded successfully."},
            status=status.HTTP_200_OK,
        )

    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "Payment signature verification failed"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print("Payment verification error:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# =========================================================
# 🔹 FETCH DOCTOR'S AVAILABLE SLOTS (PUBLIC ENDPOINT)
# =========================================================
from django.utils import timezone
from django.db.models.functions import TruncDate

class DoctorAvailableSlotsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, doctor_id):
        date_str = request.query_params.get("date")
        if not date_str:
            return Response({"error": "Date is required"}, status=400)

        try:
            # Convert to date object
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            local_tz = timezone.get_current_timezone()

            slots = (
                TimeSlot.objects.select_related("clinic")
                .filter(doctor_id=doctor_id, is_booked=False)
                .order_by("start")
            )

            filtered = []
            for s in slots:
                local_start = s.start.astimezone(local_tz)
                if local_start.date() == target_date:
                    filtered.append(s)

            formatted = [
                {
                    "id": s.id,
                    "start": s.start.astimezone(local_tz).strftime("%H:%M"),
                    "end": s.end.astimezone(local_tz).strftime("%H:%M"),
                    "clinic_id": s.clinic.id if s.clinic else None,
                    "clinic_name": s.clinic.name if s.clinic else "Unknown Clinic",
                }
                for s in filtered
            ]

            return Response({"slots": formatted}, status=200)

        except Exception as e:
            print("❌ Error fetching slots:", e)
            return Response({"error": str(e)}, status=500)
        
class DoctorAvailableDatesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, doctor_id):
        local_tz = timezone.get_current_timezone()

        # Get only unbooked future slots
        slots = (
            TimeSlot.objects.filter(doctor_id=doctor_id, is_booked=False)
            .order_by("start")
        )

        dates = set()
        for s in slots:
            local_start = s.start.astimezone(local_tz)
            if local_start.date() >= timezone.localdate():
                dates.add(local_start.date().isoformat())

        return Response({"dates": sorted(list(dates))})

    





# -------------------------
# Appointment list (patient)
# -------------------------
class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related("doctor", "clinic", "timeslot").order_by("-created_at")

        if user.role == "patient":
            return qs.filter(patient=user)
        elif user.role == "doctor":
            return qs.filter(doctor__user=user)
        elif user.role == "clinic_owner":
            return qs.filter(clinic__owner=user)
        return Appointment.objects.none()
    

# --------------------------------------
# 🔹 Appointment Cancel API
# --------------------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, pk):
    """
    Allows a patient to cancel their own appointment.
    Automatically frees up the booked timeslot.
    """
    try:
        appointment = Appointment.objects.select_related("timeslot").get(pk=pk)

        # ✅ Security: Only the patient who booked it can cancel
        if appointment.patient != request.user:
            return Response(
                {"error": "You are not authorized to cancel this appointment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ✅ Prevent double cancellation
        if appointment.status == "cancelled":
            return Response(
                {"message": "This appointment is already cancelled."},
                status=status.HTTP_200_OK,
            )

        # ✅ Mark appointment as cancelled
        appointment.status = "cancelled"
        appointment.save(update_fields=["status"])

        # ✅ Free up the timeslot
        if appointment.timeslot:
            appointment.timeslot.is_booked = False
            appointment.timeslot.save(update_fields=["is_booked"])

        return Response(
            {"success": True, "message": "Appointment cancelled successfully."},
            status=status.HTTP_200_OK,
        )

    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("❌ Cancel appointment error:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -------------------------------
# Doctor Availability System
# WEEKDAY MAP
# -------------------------------
WEEKDAY_MAP = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2,
    "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
}

# =========================================================
# Helper: Generate slots
# =========================================================
def _make_timeslots_for_window(doctor_profile, clinic, day_date, start_time, end_time, slot_minutes: int):
    slots_created = 0
    start_dt = timezone.make_aware(datetime.combine(day_date, start_time))
    end_dt = timezone.make_aware(datetime.combine(day_date, end_time))
    cursor = start_dt

    while cursor < end_dt:
        nxt = cursor + timedelta(minutes=slot_minutes)
        if nxt > end_dt:
            break

        exists = TimeSlot.objects.filter(
            doctor=doctor_profile,
            clinic=clinic,
            start=cursor,
            end=nxt
        ).exists()

        if not exists:
            TimeSlot.objects.create(
                doctor=doctor_profile,
                clinic=clinic,
                start=cursor,
                end=nxt,
                is_booked=False
            )
            slots_created += 1

        cursor = nxt

    return slots_created


# =========================================================
# SINGLE DAY AVAILABILITY (with leave + future validation)
# =========================================================
class DoctorAvailabilityView(generics.ListCreateAPIView):
    serializer_class = DoctorAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "doctor":
            dp = getattr(user, "doctor_profile", None)
            if not dp:
                return DoctorAvailability.objects.none()
            return DoctorAvailability.objects.filter(
                doctor=dp
            ).order_by("-date", "start_time")

        elif user.role == "admin":
            return DoctorAvailability.objects.all().order_by("-date", "start_time")

        return DoctorAvailability.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "doctor":
            raise PermissionDenied("Only doctors can add availability.")

        dp = getattr(user, "doctor_profile", None)
        if not dp:
            raise PermissionDenied("Doctor profile not found.")

        clinic_id = self.request.data.get("clinic_id") or self.request.data.get("clinic")
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise ValidationError({"error": "Invalid clinic ID."})

        approved = ClinicDoctorRequest.objects.filter(
            doctor=dp, clinic=clinic, status="approved"
        ).exists()

        if not approved:
            raise ValidationError({"error": "You are not approved for this clinic."})

        # Inputs
        date_str = self.request.data.get("date")
        start_str = self.request.data.get("start_time")
        end_str = self.request.data.get("end_time")
        slot_duration = int(self.request.data.get("slot_duration") or 30)
        leave_flag = str(self.request.data.get("leave", "false")).lower() in ["true", "1", "yes"]

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_obj = datetime.strptime(start_str, "%H:%M").time()
            end_obj = datetime.strptime(end_str, "%H:%M").time()
        except:
            raise ValidationError({"error": "Invalid date/time format."})

        if end_obj <= start_obj:
            raise ValidationError({"error": "End time must be after start time."})

        # ---------------------------------------------------
        # 🚫 BLOCK PAST AVAILABILITY
        # ---------------------------------------------------
        now = timezone.localtime()
        today = now.date()
        start_dt = timezone.make_aware(datetime.combine(date_obj, start_obj))

        if date_obj < today:
            raise ValidationError({"error": "You cannot add availability for past dates."})

        if date_obj == today and start_dt <= now:
            raise ValidationError({"error": "Start time must be in the future."})

        # ---------------------------------------------------
        # LEAVE MODE — cancel booked appointments + block slots
        # ---------------------------------------------------
        if leave_flag:
            affected_slots = TimeSlot.objects.filter(
                doctor=dp,
                clinic=clinic,
                start__date=date_obj
            )

            affected_appointments = Appointment.objects.filter(
                timeslot__in=affected_slots,
                status__in=["pending", "confirmed"]
            )

            for appt in affected_appointments:
                appt.status = "cancelled"
                appt.notes = (appt.notes or "") + " [Cancelled due to doctor leave]"
                appt.save()

                Notification.objects.create(
                    user=appt.patient,
                    title="Appointment cancelled",
                    message=f"Your appointment on {appt.timeslot.start.strftime('%d %b %Y %H:%M')} was cancelled due to doctor's leave."
                )

            affected_slots.update(is_booked=True)
            return  # Do not create availability

        # Remove old slots
        TimeSlot.objects.filter(
            doctor=dp,
            clinic=clinic,
            start__date=date_obj
        ).delete()

        # Save new availability
        availability = serializer.save(
            doctor=dp, clinic=clinic,
            slot_duration=slot_duration,
            status="approved"
        )

        # Generate slots
        _make_timeslots_for_window(
            doctor_profile=dp,
            clinic=clinic,
            day_date=availability.date,
            start_time=availability.start_time,
            end_time=availability.end_time,
            slot_minutes=slot_duration
        )


# =========================================================
# RECURRING (WEEKLY) AVAILABILITY
# =========================================================
class DoctorAvailabilityBulkCreateView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != "doctor":
            raise PermissionDenied("Only doctors can add recurring availability.")

        dp = getattr(user, "doctor_profile", None)
        if not dp:
            raise PermissionDenied("Doctor profile not found.")

        clinic_id = request.data.get("clinic_id") or request.data.get("clinic")
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            return Response({"error": "Invalid clinic ID."}, status=400)

        approved = ClinicDoctorRequest.objects.filter(
            doctor=dp, clinic=clinic, status="approved"
        ).exists()
        if not approved:
            return Response({"error": "You are not approved for this clinic."}, status=403)

        # Inputs
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        weekdays = request.data.get("weekdays", [])
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")
        slot_duration = int(request.data.get("slot_duration") or 30)

        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d").date()
            ed = datetime.strptime(end_date, "%Y-%m-%d").date()
            st = datetime.strptime(start_time, "%H:%M").time()
            et = datetime.strptime(end_time, "%H:%M").time()
        except:
            return Response({"error": "Invalid date/time format."}, status=400)

        if et <= st:
            return Response({"error": "End time must be after start time."}, status=400)

        # ---------------------------------------------------
        # 🚫 BLOCK PAST DATE START + PAST TODAY TIME
        # ---------------------------------------------------
        now = timezone.localtime()
        today = now.date()

        if sd < today:
            return Response({"error": "Start date cannot be in the past."}, status=400)

        if sd == today:
            start_dt = timezone.make_aware(datetime.combine(sd, st))
            if start_dt <= now:
                return Response({"error": "Start time must be in the future."}, status=400)

        weekday_ids = {WEEKDAY_MAP[w] for w in weekdays if w in WEEKDAY_MAP}

        recurrence_id = uuid.uuid4()
        created = slots = 0

        cur = sd
        while cur <= ed:
            if cur.weekday() in weekday_ids:

                exists = DoctorAvailability.objects.filter(
                    doctor=dp,
                    clinic=clinic,
                    date=cur,
                    start_time=st,
                    end_time=et
                ).exists()

                if not exists:
                    avail = DoctorAvailability.objects.create(
                        doctor=dp,
                        clinic=clinic,
                        date=cur,
                        start_time=st,
                        end_time=et,
                        recurrence_group=recurrence_id,
                        status="approved"
                    )
                    created += 1

                    slots += _make_timeslots_for_window(
                        doctor_profile=dp,
                        clinic=clinic,
                        day_date=cur,
                        start_time=st,
                        end_time=et,
                        slot_minutes=slot_duration
                    )

            cur += timedelta(days=1)

        return Response({
            "message": "Recurring availability added",
            "created": created,
            "slots": slots
        }, status=201)


# =========================================================
# DELETE RECURRING OR SINGLE-DAY AVAILABILITY
# =========================================================
class DoctorAvailabilityBulkDeleteView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        if user.role != "doctor":
            raise PermissionDenied("Only doctors can delete availability.")

        dp = getattr(user, "doctor_profile", None)
        group = request.query_params.get("recurrence_group")
        single = request.query_params.get("id")

        if group:
            DoctorAvailability.objects.filter(doctor=dp, recurrence_group=group).delete()
            return Response({"message": "Recurring availability deleted."})

        if single:
            DoctorAvailability.objects.filter(doctor=dp, id=single).delete()
            return Response({"message": "Single-day availability deleted."})

        return Response({"error": "Provide id or recurrence_group"}, status=400)


# =========================================================
# DELETE SINGLE SLOT (NEW FEATURE)
# =========================================================
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_single_slot(request, slot_id):
    user = request.user
    if user.role != "doctor":
        return Response({"error": "Only doctors can delete a slot"}, status=403)

    dp = getattr(user, "doctor_profile", None)
    if not dp:
        return Response({"error": "Doctor profile not found"}, status=404)

    try:
        slot = TimeSlot.objects.get(id=slot_id, doctor=dp)
    except TimeSlot.DoesNotExist:
        return Response({"error": "Slot not found"}, status=404)

    if slot.is_booked:
        return Response({"error": "Cannot delete a booked slot"}, status=400)

    slot.delete()
    return Response({"message": "Slot deleted successfully"})

from django.utils import timezone

class DoctorAppointmentsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        doctor = DoctorProfile.objects.get(user=request.user)

        appointments = (
            Appointment.objects
            .filter(doctor=doctor)
            .select_related("patient", "clinic", "timeslot")
            .order_by("timeslot__start")
        )

        data = []
        for a in appointments:
            if a.timeslot and a.timeslot.start:
                local_start = timezone.localtime(a.timeslot.start)
                date_str = local_start.date().isoformat()
                time_str = local_start.strftime("%H:%M")
            else:
                date_str = None
                time_str = None

            data.append({
                "id": a.id,
                "patient_name": a.patient.full_name,
                "clinic_name": a.clinic.name if a.clinic else "—",
                "date": date_str,
                "time": time_str,
                "amount": a.amount,
                "paid": a.paid,
                "status": a.status,
            })

        return Response(data, status=200)


class DoctorScheduleSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        doctor = DoctorProfile.objects.filter(user=request.user).first()
        if not doctor:
            return Response({"error": "Doctor profile not found"}, status=400)

        today = timezone.now().date()

        # ------------------------------
        # ✅ TODAY'S APPOINTMENTS
        # ------------------------------
        today_appointments = Appointment.objects.filter(
            doctor=doctor,
            timeslot__start__date=today,
            status__in=["pending", "confirmed"]
        ).order_by("timeslot__start")

        today_count = today_appointments.count()

        # ------------------------------
        # ✅ UPCOMING APPOINTMENTS (Future & Today)
        # ------------------------------
        upcoming = Appointment.objects.filter(
            doctor=doctor,
            timeslot__start__date__gte=today,
            status__in=["pending", "confirmed"]
        ).order_by("timeslot__start")

        upcoming_count = upcoming.count()

        # ------------------------------
        # ✅ NEXT APPOINTMENT
        # ------------------------------
        next_appt = upcoming.first()

        next_data = None
        if next_appt:
            next_data = {
                "date": next_appt.timeslot.start.date(),
                "time": next_appt.timeslot.start.time(),
                "patient": next_appt.patient.full_name,
                "clinic": next_appt.clinic.name,
            }

        return Response({
            "today_count": today_count,
            "upcoming_count": upcoming_count,
            "next": next_data,
        }, status=200)

    
class DoctorScheduleListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        doctor = DoctorProfile.objects.filter(user=request.user).first()
        if not doctor:
            return Response({"error": "Doctor profile not found"}, status=400)

        appointments = Appointment.objects.filter(
            doctor=doctor,
            status__in=["pending", "confirmed"]
        ).select_related("patient", "clinic", "timeslot") \
         .order_by("timeslot__start")

        serializer = DoctorScheduleSerializer(appointments, many=True)
        return Response(serializer.data, status=200)




# -------------------------
# Remaining views (profiles, reminders, reports, suggestions)
# -------------------------
class PatientProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        serializer = PatientProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        serializer = PatientProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ReminderListView(generics.ListAPIView):
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reminder.objects.filter(user=self.request.user).order_by("-created_at")


class AddReminderView(generics.CreateAPIView):
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # ✅ Save reminder tied to logged-in user
        serializer.save(user=self.request.user)

# --------------------------------------------------
# UPLOAD MEDICAL REPORT (FINAL WORKING VERSION)
# --------------------------------------------------
class UploadMedicalReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Get patient profile of logged-in user
        try:
            patient = PatientProfile.objects.get(user=request.user)
        except PatientProfile.DoesNotExist:
            return Response({"error": "Patient profile not found."}, status=404)

        # WRITE serializer for upload
        upload_serializer = MedicalReportUploadSerializer(data=request.data)

        if not upload_serializer.is_valid():
            print("❌ Upload Errors:", upload_serializer.errors)
            return Response(upload_serializer.errors, status=400)

        # Save report
        report = upload_serializer.save(patient=patient)

        # READ serializer to return file URL
        read_serializer = MedicalReportSerializer(report, context={"request": request})
        return Response(read_serializer.data, status=201)
# --------------------------------------------------
# LIST MEDICAL REPORTS (FINAL)
# --------------------------------------------------
class MedicalReportListView(generics.ListAPIView):
    serializer_class = MedicalReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            patient = PatientProfile.objects.get(user=self.request.user)
            return MedicalReport.objects.filter(patient=patient).order_by("-uploaded_at")
        except PatientProfile.DoesNotExist:
            return MedicalReport.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class DeleteMedicalReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            patient = PatientProfile.objects.get(user=request.user)
        except PatientProfile.DoesNotExist:
            return Response({"error": "Patient profile not found."}, status=404)

        try:
            report = MedicalReport.objects.get(id=pk, patient=patient)
        except MedicalReport.DoesNotExist:
            return Response({"error": "Report not found."}, status=404)

        # Delete the file from storage too
        if report.file:
            report.file.delete(save=False)

        report.delete()
        return Response({"message": "Report deleted successfully."}, status=200)







class HomeImageListView(generics.ListAPIView):
    queryset = HomeImage.objects.all()
    serializer_class = HomeImageSerializer
    permission_classes = [permissions.AllowAny]


class PatientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        requester = request.user
        role = getattr(requester, "role", None)

        if role != User.ROLE_DOCTOR and not requester.is_staff:
            return Response({"detail": "Permission denied"}, status=403)

        target_user = get_object_or_404(User, id=patient_id)

        profile = PatientProfile.objects.filter(user=target_user).first()

        profile_data = {
            "id": target_user.id,
            "full_name": target_user.full_name,
            "age": getattr(profile, "age", None),
            "gender": getattr(profile, "gender", None),
            "phone": getattr(profile, "phone", None),
            "address": getattr(profile, "address", None),
            "medical_history": getattr(profile, "medical_history", None),
        }

        reports = MedicalReport.objects.filter(patient=profile).order_by("-uploaded_at")
        report_data = MedicalReportSerializer(reports, many=True, context={"request": request}).data

        return Response({
            "profile": profile_data,
            "reports": report_data,
        }, status=200)

class DoctorBookFollowupView(APIView):
    """
    POST /api/doctor/book-followup/
    Body:
      {
        "patient_id": <int>,
        "clinic_id": <int>,
        "timeslot_id": <int>
      }
    Creates a confirmed, free follow-up appointment (paid=True, amount=0).
    Only accessible to authenticated doctors.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        requester = request.user
        role = getattr(requester, "role", None)

        # Allow only doctors or staff/admin
        if role != getattr(User, "ROLE_DOCTOR", "doctor") and not (requester.is_staff or requester.is_superuser):
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        patient_id = request.data.get("patient_id")
        clinic_id = request.data.get("clinic_id")
        timeslot_id = request.data.get("timeslot_id")

        if not (patient_id and clinic_id and timeslot_id):
            return Response({"detail": "patient_id, clinic_id and timeslot_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        doctor_profile = DoctorProfile.objects.filter(user=requester).first()
        if not doctor_profile:
            return Response({"detail": "Doctor profile not found for requester."}, status=status.HTTP_400_BAD_REQUEST)

        patient_user = get_object_or_404(User, id=patient_id)
        clinic = get_object_or_404(Clinic, id=clinic_id)
        timeslot = get_object_or_404(TimeSlot, id=timeslot_id)

        # Strict checks
        if timeslot.doctor != doctor_profile:
            return Response({"detail": "Timeslot does not belong to this doctor."}, status=status.HTTP_400_BAD_REQUEST)
        if timeslot.clinic != clinic:
            return Response({"detail": "Timeslot does not belong to the selected clinic."}, status=status.HTTP_400_BAD_REQUEST)
        if timeslot.is_booked:
            return Response({"detail": "Timeslot already booked."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            token_no = f"FUP-{uuid.uuid4().hex[:8].upper()}"
            appointment = Appointment.objects.create(
                patient=patient_user,
                doctor=doctor_profile,
                clinic=clinic,
                timeslot=timeslot,
                status="confirmed",
                notes=f"Follow-up booked by Dr. {doctor_profile.user.full_name}",
                amount=0.00,
                paid=True,
                token_no=token_no,
            )
            timeslot.is_booked = True
            timeslot.save(update_fields=["is_booked"])

            # Create a notification for patient (best-effort)
            try:
                Notification.objects.create(
                    user=patient_user,
                    title="Follow-up appointment booked",
                    message=f"Dr. {doctor_profile.user.full_name} booked your follow-up on {timeslot.start.strftime('%d %b %Y %H:%M')}. Token: {token_no}"
                )
            except Exception:
                pass

        return Response({
            "detail": "Follow-up appointment booked (free).",
            "appointment_id": appointment.id,
            "token_no": token_no,
            "appointment": {
                "id": appointment.id,
                "patient": appointment.patient.full_name or appointment.patient.email,
                "clinic": clinic.name,
                "date": timeslot.start.date().isoformat() if timeslot.start else None,
                "time": timeslot.start.time().isoformat() if timeslot.start else None,
                "token_no": token_no,
            }
        }, status=status.HTTP_201_CREATED)


from rest_framework.parsers import MultiPartParser, FormParser

class DoctorProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        doctor = DoctorProfile.objects.filter(user=request.user).first()
        if not doctor:
            return Response({"error": "Doctor profile not found"}, status=404)

        serializer = DoctorProfileSerializer(doctor, context={"request": request})
        return Response(serializer.data)

    def put(self, request):
        doctor = DoctorProfile.objects.filter(user=request.user).first()
        if not doctor:
            return Response({"error": "Doctor profile not found"}, status=404)

        serializer = DoctorProfileSerializer(
            doctor,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

@api_view(["GET"])
@permission_classes([AllowAny])
def suggest_doctors(request):
    symptom = request.GET.get("symptom", "").lower().strip()
    if not symptom:
        return Response({"message": "No symptom provided."}, status=400)

    symptom_keywords = {
        "fever": "General Physician",
        "cold": "General Physician",
        "cough": "General Physician",
        "headache": "Neurologist",
        "migraine": "Neurologist",
        "skin": "Dermatologist",
        "rash": "Dermatologist",
        "heart": "Cardiologist",
        "chest": "Cardiologist",
        "eye": "Ophthalmologist",
        "tooth": "Dentist",
        "teeth": "Dentist",
        "pain": "Orthopedic",
        "bone": "Orthopedic",
        "stomach": "Gastroenterologist",
        "digest": "Gastroenterologist",
        "mental": "Psychiatrist",
        "anxiety": "Psychiatrist",
    }

    matched_specialization = next((spec for key, spec in symptom_keywords.items() if key in symptom), None)

    if not matched_specialization:
        return Response({"message": "No matching specialization found."}, status=200)

    doctors = DoctorProfile.objects.filter(specialization__name__icontains=matched_specialization, is_verified=True)

    if not doctors.exists():
        return Response({"message": "No doctors found."}, status=200)

    serializer = DoctorSerializer(doctors, many=True)
    return Response(serializer.data, status=200)


@api_view(["GET"])
@permission_classes([AllowAny])
def suggest_doctor(request):
    symptom_name = request.GET.get("symptom", "").strip().lower()
    if not symptom_name:
        return Response({"message": "Symptom is required."}, status=400)

    try:
        symptom = Symptom.objects.get(name__iexact=symptom_name)
    except Symptom.DoesNotExist:
        return Response({"message": "No specialization found for this symptom."}, status=404)

    doctors = DoctorProfile.objects.filter(specialization=symptom.specialization, is_verified=True)
    if not doctors.exists():
        return Response({"message": "No doctors found for this symptom."}, status=404)

    serializer = DoctorProfileSerializer(doctors, many=True)
    return Response({
        "specialization": symptom.specialization.name,
        "doctors": serializer.data
    })


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return notifications only for the logged-in user."""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        """Ensure the notification is always linked to the correct user."""
        serializer.save(user=self.request.user)



class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by("-created_at")
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "doctor":
            return Appointment.objects.filter(doctor__user=user)
        elif user.role == "patient":
            return Appointment.objects.filter(patient=user)
        elif user.role == "clinic":
            return Appointment.objects.filter(clinic__owner=user)
        return super().get_queryset()

    def perform_create(self, serializer):
        # Automatically set patient and generate a token number
        user = self.request.user
        token_number = f"TOK-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        serializer.save(patient=user, token_no=token_number)

    @action(detail=False, methods=["get"], url_path="by-doctor/(?P<doctor_id>[^/.]+)")
    def get_by_doctor(self, request, doctor_id=None):
        appointments = Appointment.objects.filter(doctor__id=doctor_id)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="by-clinic/(?P<clinic_id>[^/.]+)")
    def get_by_clinic(self, request, clinic_id=None):
        appointments = Appointment.objects.filter(clinic__id=clinic_id)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_appointment(self, request, pk=None):
        appointment = get_object_or_404(Appointment, pk=pk)
        if appointment.status != "cancelled":
            appointment.status = "cancelled"
            appointment.save()
            return Response({"message": "Appointment cancelled successfully"})
        return Response({"message": "Already cancelled"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm_appointment(self, request, pk=None):
        appointment = get_object_or_404(Appointment, pk=pk)
        if appointment.status == "pending":
            appointment.status = "confirmed"
            appointment.save()
            return Response({"message": "Appointment confirmed successfully"})
        return Response({"message": "Cannot confirm this appointment"}, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Patient view → see only their own payments
        if hasattr(user, "id"):
            return Payment.objects.filter(
                appointment__patient=user
            ).select_related(
                "appointment__doctor__user",
                "appointment__clinic",
                "appointment__timeslot",
            ).order_by("-created_at")

        # Fallback (admin, etc.)
        return Payment.objects.all().order_by("-created_at")

class ReviewViewSet(viewsets.ModelViewSet):
    """
    Reviews: patients create reviews; doctors see reviews about themselves; admins see all.
    """
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_role = getattr(user, "role", None)
        # Doctor: return reviews for this doctor's profile
        if user_role in (getattr(User, "ROLE_DOCTOR", "doctor"), "doctor"):
            dp = getattr(user, "doctor_profile", None) or getattr(user, "doctor_profile", None)
            if dp:
                return Review.objects.filter(doctor=dp).order_by("-created_at")
            return Review.objects.none()
        # Patient: return their own reviews
        if user_role in (getattr(User, "ROLE_PATIENT", "patient"), "patient"):
            return Review.objects.filter(user=user).order_by("-created_at")
        # Admin/others: return all
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------------------------------------------------
# Clinics & requests
# ---------------------------------------------------------

from .models import (
    Clinic,
    ClinicDoctorRequest,
    DoctorAvailability,
    Notification,
)
from .serializers import (
    ClinicSerializer,
    ClinicDoctorRequestSerializer,
    NotificationSerializer,
)


# =========================================================
# 🔹 CLINICS
# =========================================================


class ClinicListView(generics.ListCreateAPIView):
    """
    - GET  → list clinics
      * Clinic owner → only their clinics
      * Doctor/patient → all clinics
      * Public → all verified clinics
    - POST → create a clinic (auto-assigns owner)
    """
    serializer_class = ClinicSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.role == "clinic_owner":
                return Clinic.objects.filter(owner=user).order_by("-created_at")
            elif user.role in ["doctor", "patient", "admin"]:
                return Clinic.objects.all().order_by("-created_at")
        # Unauthenticated users → only verified ones
        return Clinic.objects.filter(is_verified=True).order_by("-created_at")

    def perform_create(self, serializer):
        """
        When a clinic owner adds a clinic, it automatically links to them.
        """
        user = self.request.user
        if not user.is_authenticated or user.role != "clinic_owner":
            raise PermissionDenied("Only clinic owners can add clinics.")
        serializer.save(owner=user, is_verified=False)
    
# CLINIC DETAIL VIEW
# ======================
class ClinicDetailView(generics.RetrieveAPIView):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        clinic_data = self.get_serializer(instance).data

        # ✅ Get all doctors who are approved to work in this clinic
        approved_doctors = ClinicDoctorRequest.objects.filter(
            clinic=instance, status="approved"
        ).select_related("doctor__user", "doctor__specialization")

        # ✅ Include approved doctor details in clinic response
        clinic_data["approved_doctors"] = [
            {
                "id": r.doctor.id,
                "full_name": r.doctor.user.full_name,
                "specialization": (
                    r.doctor.specialization.name if r.doctor.specialization else "General Practitioner"
                ),
                "is_verified": r.doctor.is_verified,
            }
            for r in approved_doctors
        ]

        return Response(clinic_data, status=status.HTTP_200_OK)


# =========================================================
# 🔹 DOCTOR → CLINIC REQUEST
# =========================================================
class ClinicDoctorRequestCreateView(generics.CreateAPIView):
    """
    Allows a doctor to send or re-send a request to join a clinic.
    Prevents duplicates by updating rejected ones instead of creating new rows.
    """
    queryset = ClinicDoctorRequest.objects.all()
    serializer_class = ClinicDoctorRequestSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        doctor = getattr(request.user, "doctor_profile", None)
        if not doctor:
            return Response(
                {"error": "Doctor profile not found for this user."},
                status=status.HTTP_400_BAD_REQUEST
            )

        clinic_id = request.data.get("clinic")
        if not clinic_id:
            return Response({"error": "Clinic ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            return Response({"error": "Clinic not found."}, status=status.HTTP_404_NOT_FOUND)

        # 🧠 Check for existing request
        existing = ClinicDoctorRequest.objects.filter(doctor=doctor, clinic=clinic).first()

        if existing:
            if existing.status == "pending":
                return Response(
                    {"error": "You already have a pending request for this clinic."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing.status == "approved":
                return Response(
                    {"error": "You are already approved for this clinic."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing.status == "rejected":
                # ♻️ Reopen the rejected request
                existing.status = "pending"
                existing.save()

                Notification.objects.create(
                    user=clinic.owner,
                    message=f"Dr. {doctor.user.full_name} has re-sent a join request for '{clinic.name}'."
                )

                return Response(
                    {"message": "Join request re-sent successfully."},
                    status=status.HTTP_200_OK
                )

        # ✅ No previous request → create a new one
        new_request = ClinicDoctorRequest.objects.create(
            doctor=doctor,
            clinic=clinic,
            status="pending"
        )

        Notification.objects.create(
            user=clinic.owner,
            message=f"Dr. {doctor.user.full_name} has requested to join your clinic '{clinic.name}'."
        )

        return Response(
            {"message": "Join request sent successfully."},
            status=status.HTTP_201_CREATED
        )


class DoctorClinicRequestListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != "doctor":
            return Response({"error": "Only doctors can view this"}, status=403)

        doctor = getattr(user, "doctor_profile", None)
        if not doctor:
            return Response({"error": "Doctor profile not found"}, status=404)

        requests = ClinicDoctorRequest.objects.filter(doctor=doctor).select_related("clinic")

        data = [
            {
                "id": r.id,
                "clinic": r.clinic.name,
                "clinic_id": r.clinic.id,
                "status": r.status,
                "requested_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in requests
        ]

        return Response(data, status=200)

# =========================================================
# 🔹 DOCTOR → VIEW APPROVED CLINICS
# =========================================================
class DoctorClinicsView(APIView):
    """
    Returns all approved clinics for a specific doctor, along with consultation fee if set.
    Public endpoint (for patient view).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, doctor_id):
        doctor = DoctorProfile.objects.filter(id=doctor_id).first()
        if not doctor:
            return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

        approved_links = ClinicDoctorRequest.objects.filter(
            doctor=doctor, status="approved"
        ).select_related("clinic")

        data = []
        for link in approved_links:
            clinic = link.clinic
            # Look for a DoctorFeeManagement record for (doctor, clinic)
            fee_record = DoctorFeeManagement.objects.filter(doctor=doctor, clinic=clinic).first()
            consultation_fee = float(fee_record.consultation_fee) if fee_record else None
            clinic_share_percent = float(fee_record.clinic_share_percent) if fee_record else None

            data.append({
                "id": clinic.id,
                "name": clinic.name,
                "address": clinic.address,
                "consultation_fee": consultation_fee,
                "clinic_share_percent": clinic_share_percent,
            })

        return Response(data, status=status.HTTP_200_OK)

class DoctorApprovedClinicsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != "doctor":
            return Response({"error": "Only doctors can view this."}, status=403)

        doctor = getattr(user, "doctor_profile", None)
        if not doctor:
            return Response({"error": "Doctor profile not found."}, status=404)

        approved = ClinicDoctorRequest.objects.filter(
            doctor=doctor, status="approved"
        ).select_related("clinic")

        data = [
            {
                "id": r.clinic.id,
                "name": r.clinic.name,
                "address": r.clinic.address,
                "owner": r.clinic.owner.full_name,
            }
            for r in approved
        ]
        return Response(data, status=200)
    
class DoctorFeeManagementView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Return all fee records for the logged-in doctor."""
        user = request.user
        if user.role != "doctor":
            return Response({"error": "Only doctors can view this."}, status=403)

        doctor = getattr(user, "doctor_profile", None)
        if not doctor:
            return Response({"error": "Doctor profile not found."}, status=404)

        fees = DoctorFeeManagement.objects.filter(doctor=doctor).select_related("clinic")
        serializer = DoctorFeeManagementSerializer(fees, many=True)
        return Response(serializer.data, status=200)

    def post(self, request):
        """Create or update consultation fee for a clinic and sync DoctorProfile.fee."""
        user = request.user
        if user.role != "doctor":
            return Response({"error": "Only doctors can set fees."}, status=403)

        doctor = getattr(user, "doctor_profile", None)
        if not doctor:
            return Response({"error": "Doctor profile not found."}, status=404)

        clinic_id = request.data.get("clinic_id")
        consultation_fee = request.data.get("consultation_fee")

        if not clinic_id or consultation_fee is None:
            return Response({"error": "clinic_id and consultation_fee are required."}, status=400)

        try:
            consultation_fee = float(consultation_fee)
        except ValueError:
            return Response({"error": "Invalid fee amount."}, status=400)

        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            return Response({"error": "Clinic not found."}, status=404)

        # ✅ Check approval
        approved = ClinicDoctorRequest.objects.filter(
            doctor=doctor, clinic=clinic, status="approved"
        ).exists()
        if not approved:
            return Response({"error": "You are not approved for this clinic."}, status=403)

        # ✅ Create or update DoctorFeeManagement
        fee_obj, created = DoctorFeeManagement.objects.update_or_create(
            doctor=doctor,
            clinic=clinic,
            defaults={"consultation_fee": consultation_fee},
        )

        # 🟢 NEW: Sync DoctorProfile global fee
        if consultation_fee > 0:
            doctor.fee = consultation_fee
            doctor.save(update_fields=["fee"])

        message = "Fee set successfully." if created else "Fee updated successfully."
        serializer = DoctorFeeManagementSerializer(fee_obj)
        return Response({"message": message, "data": serializer.data}, status=200)
    
class DoctorEarningsSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Only doctors allowed
        if user.role != "doctor":
            return Response({"error": "Only doctors can access earnings."}, status=403)

        doctor = getattr(user, "doctor_profile", None)
        if not doctor:
            return Response({"error": "Doctor profile not found."}, status=404)

        today = timezone.localdate()
        month_start = today.replace(day=1)

        # Filter earnings related to this doctor
        revenues = ClinicRevenue.objects.filter(doctor=doctor)

        # Today's earnings
        today_amount = revenues.filter(date=today).aggregate(
            total=Sum("doctor_amount")
        )["total"] or 0

        # This month's earnings
        month_amount = revenues.filter(date__gte=month_start).aggregate(
            total=Sum("doctor_amount")
        )["total"] or 0

        # Lifetime / total
        total_amount = revenues.aggregate(
            total=Sum("doctor_amount")
        )["total"] or 0

        return Response(
            {
                "today": today_amount,
                "month": month_amount,
                "total": total_amount,
            },
            status=200,
        )



# =========================================================
# 🔹 CLINIC OWNER → APPROVE / REJECT DOCTOR REQUEST
# =========================================================
class ClinicDoctorApprovalView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            req = ClinicDoctorRequest.objects.get(pk=pk)
        except ClinicDoctorRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")

        if action == "approve":
            req.status = "approved"
            req.save()

            # ✅ Automatically verify doctor when approved
            doctor_profile = req.doctor
            doctor_profile.is_verified = True
            doctor_profile.save()

            # Optional: create notification for doctor
            Notification.objects.create(
                user=doctor_profile.user,
                message=f"Your request to join {req.clinic.name} has been approved."
            )

            return Response({"message": "Doctor approved and verified successfully"}, status=status.HTTP_200_OK)

        elif action == "reject":
            req.status = "rejected"
            req.save()

            Notification.objects.create(
                user=req.doctor.user,
                message=f"Your request to join {req.clinic.name} was rejected."
            )

            return Response({"message": "Doctor request rejected"}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
# =========================================================
# 🔹 CLINIC OWNER → VIEW ALL DOCTOR JOIN REQUESTS
# =========================================================
# =========================================================
# 🔹 CLINIC OWNER → VIEW ALL DOCTOR JOIN REQUESTS (FIXED)
# =========================================================
class ClinicOwnerRequestListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != "clinic_owner":
            return Response({"error": "Only clinic owners can view this"}, status=403)

        # ✅ Get all clinics owned by this clinic owner
        clinics = Clinic.objects.filter(owner=user)

        # ✅ Include doctor, user, and clinic info efficiently
        requests = ClinicDoctorRequest.objects.filter(clinic__in=clinics).select_related(
            "doctor__user", "doctor__specialization", "clinic"
        )

        data = [
            {
                "id": r.id,
                "doctor_name": r.doctor.user.full_name,
                "doctor_specialization": (
                    r.doctor.specialization.name if r.doctor.specialization else "N/A"
                ),
                "clinic_name": r.clinic.name,
                "clinic_id": r.clinic.id,
                "status": r.status,
                "requested_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in requests
        ]

        return Response(data, status=200)


# =========================================================
# 🔹 CLINIC OWNER → APPROVE DOCTOR AVAILABILITY
# =========================================================
class ClinicApproveAvailabilityView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            availability = DoctorAvailability.objects.get(pk=pk)
        except DoctorAvailability.DoesNotExist:
            return Response({"error": "Availability not found"}, status=404)

        action = request.data.get("action")
        if action == "approve":
            availability.status = "approved"
        elif action == "reject":
            availability.status = "rejected"
        else:
            return Response({"error": "Invalid action"}, status=400)

        availability.save()
        return Response({"message": "Doctor approved and verified successfully"}, status=status.HTTP_200_OK)

def _dt_combine(d: date_cls, t):
    return datetime.combine(d, t)

def _make_timeslots_for_window(doctor_profile, clinic, day_date, start_time, end_time, slot_minutes: int):
    slots_created = 0
    start_dt = _dt_combine(day_date, start_time)
    end_dt = _dt_combine(day_date, end_time)
    cursor = start_dt

    while cursor < end_dt:
        nxt = cursor + timedelta(minutes=slot_minutes)
        if nxt > end_dt:
            break

        exists = TimeSlot.objects.filter(
            doctor=doctor_profile,
            start=cursor,
            end=nxt,
        ).exists()

        if not exists:
            TimeSlot.objects.create(
                doctor=doctor_profile,
                clinic=clinic,
                start=cursor,
                end=nxt,
                is_booked=False
            )
            slots_created += 1

        cursor = nxt
    return slots_created

class ClinicAppointmentsView(APIView):
    """
    GET /api/clinic/appointments/
    Returns appointments for clinics owned by the requesting clinic owner.
    Staff/superuser see all appointments.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # If user is staff/superuser, show all appointments (optional)
        if user.is_staff or user.is_superuser:
            appointments_qs = Appointment.objects.select_related(
                "patient", "doctor__user", "clinic", "timeslot__clinic", "timeslot"
            ).all().order_by("timeslot__start")
        else:
            # Owner should have clinics: Clinic.owner == request.user
            clinics = Clinic.objects.filter(owner=user).values_list("id", flat=True)
            if not clinics:
                return Response([], status=status.HTTP_200_OK)

            appointments_qs = Appointment.objects.select_related(
                "patient", "doctor__user", "clinic", "timeslot__clinic", "timeslot"
            ).filter(clinic_id__in=list(clinics)).order_by("timeslot__start")

        # Serialize with AppointmentSerializer (handles missing timeslot)
        serializer = AppointmentSerializer(appointments_qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AddOfflineAppointmentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Only clinic owners allowed
        if user.role != "clinic_owner":
            return Response({"error": "Only clinic owners can add offline appointments"}, status=403)

        data = request.data
        clinic_id = data.get("clinic")
        doctor_id = data.get("doctor")
        patient_name = data.get("patient_name")
        contact = data.get("contact")
        date = data.get("date")
        time = data.get("time")
        notes = data.get("notes", "")

        if not all([clinic_id, doctor_id, patient_name, date, time]):
            return Response({"error": "Missing required fields"}, status=400)

        # Validate clinic
        try:
            clinic = Clinic.objects.get(id=clinic_id, owner=user)
        except Clinic.DoesNotExist:
            return Response({"error": "Invalid clinic"}, status=404)

        # Validate doctor
        try:
            doctor = DoctorProfile.objects.get(id=doctor_id)
        except DoctorProfile.DoesNotExist:
            return Response({"error": "Invalid doctor"}, status=404)

        # Create OR reuse guest patient
        guest_email = f"offline_{contact}@guest.com"
        patient, _ = User.objects.get_or_create(
            email=guest_email,
            defaults={"full_name": patient_name, "role": "patient"},
        )

        # Convert date + time
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        dt = timezone.make_aware(dt)

        # Create temporary slot
        slot = TimeSlot.objects.create(
            doctor=doctor,
            clinic=clinic,
            start=dt,
            end=dt + timedelta(minutes=20),   # default offline slot duration
            is_booked=True
        )

        # Generate unique token
        token_no = f"OFF-{uuid.uuid4().hex[:8].upper()}"

        # Create appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            clinic=clinic,
            timeslot=slot,
            status="confirmed",
            paid=False,
            amount=0,
            token_no=token_no,
            notes=notes
        )

        return Response({
            "message": "Offline appointment added",
            "appointment_id": appointment.id,
            "token_no": token_no
        }, status=201)

class ClinicRevenueListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_staff or user.is_superuser:
            qs = ClinicRevenue.objects.select_related("clinic", "doctor__user", "appointment").order_by("-created_at")
        else:
            clinic_ids = Clinic.objects.filter(owner=user).values_list("id", flat=True)
            qs = ClinicRevenue.objects.filter(clinic_id__in=list(clinic_ids)).select_related("clinic", "doctor__user", "appointment").order_by("-created_at")

        serializer = ClinicRevenueSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClinicRevenueSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_staff or user.is_superuser:
            clinic_ids = Clinic.objects.values_list("id", flat=True)
        else:
            clinic_ids = Clinic.objects.filter(owner=user).values_list("id", flat=True)

        qs = ClinicRevenue.objects.filter(clinic_id__in=list(clinic_ids))

        total = qs.aggregate(
            total_fee=Sum("total_fee"),
            clinic_share=Sum("clinic_share"),
            doctor_earning=Sum("doctor_earning")
        )

        per_clinic = (
            qs.values("clinic_id", "clinic__name")
              .annotate(total_fee=Sum("total_fee"), clinic_share=Sum("clinic_share"), doctor_earning=Sum("doctor_earning"))
              .order_by("-total_fee")
        )

        return Response({
            "total": {
                "total_fee": float(total["total_fee"] or 0),
                "clinic_share": float(total["clinic_share"] or 0),
                "doctor_earning": float(total["doctor_earning"] or 0),
            },
            "per_clinic": [
                {
                    "clinic_id": c["clinic_id"],
                    "clinic_name": c["clinic__name"],
                    "total_fee": float(c["total_fee"] or 0),
                    "clinic_share": float(c["clinic_share"] or 0),
                    "doctor_earning": float(c["doctor_earning"] or 0),
                }
                for c in per_clinic
            ]
        }, status=status.HTTP_200_OK)

# =========================================================
# 🔹 SPECIALIZATION LIST (PUBLIC)
# =========================================================
class SpecializationListView(generics.ListAPIView):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@api_view(["POST"])
@permission_classes([AllowAny])
def analyze_symptoms(request):
    symptoms = request.data.get("symptoms", "")
    if not symptoms or len(symptoms) < 3:
        return Response({"error": "Please enter valid symptoms"}, status=400)

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # ----------------------------------------------
        # AI PROMPT
        # ----------------------------------------------
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical diagnosis assistant. "
                        "Given symptoms, respond ONLY in this format:\n\n"
                        "Possible Conditions:\n"
                        "- condition 1\n"
                        "- condition 2\n"
                        "Suggested Specialist: <name>\n"
                        "Advice: <short advice>"
                    )
                },
                {"role": "user", "content": symptoms}
            ],
            max_tokens=400,
        )

        text = response.choices[0].message.content.strip()

        # ----------------------------------------------
        # PARSE AI RESPONSE
        # ----------------------------------------------
        conditions = re.findall(r"- (.+)", text)
        specialist_match = re.search(r"Suggested Specialist:\s*(.+)", text)
        advice_match = re.search(r"Advice:\s*(.+)", text)

        specialist_raw = specialist_match.group(1).strip() if specialist_match else "General Physician"
        advice = advice_match.group(1).strip() if advice_match else "Consult a doctor for proper diagnosis."

        # ----------------------------------------------
        # MAP SPECIALIST → DATABASE SPECIALIZATION
        # ----------------------------------------------
        specialist_map = {
            "general physician": "General Physician",
            "primary care physician": "General Physician",
            "doctor": "General Physician",
            "family doctor": "General Physician",

            "dentist": "Dentist",
            "orthopedist": "Orthopedist",
            "physiotherapist": "Physiotherapist",
            "psychiatrist": "Psychiatrist",

            "dermatologist": "Dermatology",
            "skin specialist": "Dermatology",

            "gynecologist": "Gynecologist",
            "women specialist": "Gynecologist",
        }

        mapped_specialist = specialist_map.get(
            specialist_raw.lower(),  
            "General Physician"      # fallback
        )

        # ----------------------------------------------
        # GET MATCHING DOCTORS
        # ----------------------------------------------
        matched_doctors = []
        doctors = DoctorProfile.objects.filter(
            specialization__name=mapped_specialist,
            is_verified=True
        )

        for d in doctors:
            matched_doctors.append({
                "id": d.id,
                "name": d.user.full_name,
                "qualification": d.qualification,
                "fee": float(d.fee),
                "specialization": d.specialization.name if d.specialization else "",
            })

        # ----------------------------------------------
        # SEND TO FRONTEND
        # ----------------------------------------------
        return Response({
            "conditions": conditions,
            "specialist": mapped_specialist,
            "advice": advice,
            "doctors": matched_doctors
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

@api_view(["POST"])
@permission_classes([AllowAny])
def homepage_chatbot(request):
    """
    Lightweight public chatbot for homepage.
    """
    try:
        question = request.data.get("message", "").strip()
        if not question:
            return Response({"error": "Message is required"}, status=400)

        # Create OpenAI client
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Make completion request
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are WELLORA assistant. Help visitors politely."},
                {"role": "user", "content": question},
            ],
            max_tokens=150
        )

        # FIXED LINE
        reply = response.choices[0].message.content

        return Response({"reply": reply})

    except Exception as e:
        import traceback
        print("\n\n=== CHATBOT ERROR TRACEBACK ===")
        traceback.print_exc()
        print("=== END TRACEBACK ===\n\n")
        return Response({"error": str(e)}, status=500)
