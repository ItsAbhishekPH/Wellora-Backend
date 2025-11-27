from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from django.core.mail import send_mail

@receiver(post_save, sender=Appointment)
def appointment_notify(sender, instance, created, **kwargs):
    if created:
        # Notify patient (email backend set to console in settings by default)
        send_mail(
            subject="Appointment requested",
            message=f"Your appointment request with {instance.doctor} is received and pending.",
            from_email="noreply@docproject.local",
            recipient_list=[instance.patient.email],
            fail_silently=True,
        )
    else:
        # status change notification
        send_mail(
            subject=f"Appointment {instance.status}",
            message=f"Your appointment #{instance.id} status changed to {instance.status}.",
            from_email="noreply@docproject.local",
            recipient_list=[instance.patient.email],
            fail_silently=True,
        )
