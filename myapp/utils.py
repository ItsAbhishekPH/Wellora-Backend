# myapp/utils.py
from django.core.mail import send_mail
from django.conf import settings

def send_otp_via_email(email, otp_code):
    """Send OTP to user's email."""
    subject = "Your Login OTP - Wellora"
    message = f"Dear user,\n\nYour OTP code is: {otp_code}\nThis code is valid for 5 minutes.\n\nRegards,\nWellora Team"
    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(subject, message, from_email, [email])
        print(f"✅ OTP sent to {email}: {otp_code}")
    except Exception as e:
        print("❌ Email send error:", e)
        raise e
