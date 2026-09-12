from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

# Autoretry on any Exception with exponential backoff (max 3 retries)
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_email_async(self, subject, message, recipient_list, template=None, context=None, workspace_id=None):
    """Send email as a Celery task with retries on failure.

    workspace_id is optional but included for tenant-aware task routing in Part 1.
    """
    try:
        from django.core.mail import EmailMultiAlternatives
        html_message = None
        if template and context:
            html_message = render_to_string(f'emails/{template}.html', context)
            message = strip_tags(html_message)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=recipient_list
        )
        
        if html_message:
            msg.attach_alternative(html_message, "text/html")
            
        msg.send(fail_silently=False)
        return f"Email sent to {recipient_list}"
    except Exception as exc:
        # Log and re-raise to trigger autoretry
        logger.exception("send_email_async failed")
        raise
