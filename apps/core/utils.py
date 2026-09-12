from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import csv
import json
from io import StringIO


# Prefer a Celery task when available; fall back to a synchronous function for environments
# where Celery isn't present (tests or simple local installs).
try:
    # apps.core.tasks defines a shared_task named send_email_async
    from .tasks import send_email_async  # type: ignore
except Exception:
    def send_email_async(subject, message, recipient_list, template=None, context=None):
        """Fallback synchronous email sender."""
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
            return f"Error sending email: {exc}"


class DataExporter:
    """Export data to CSV or JSON."""

    @staticmethod
    def export_to_csv(queryset, fields):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(fields)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in fields])
        return output.getvalue()

    @staticmethod
    def export_to_json(queryset, serializer_class):
        serializer = serializer_class(queryset, many=True)
        return json.dumps(serializer.data, indent=2, default=str)


class GlobalSearch:
    """Global search across multiple models."""

    @staticmethod
    def search(query, models):
        results = {}
        for model, search_fields in models.items():
            from django.db.models import Q
            q_objects = Q()
            for field in search_fields:
                q_objects |= Q(**{f'{field}__icontains': query})
            results[model.__name__] = model.objects.filter(q_objects)[:5]
        return results


class PaginationHelper:
    """Helper for pagination."""

    @staticmethod
    def paginate_queryset(queryset, page, page_size=20):
        start = (page - 1) * page_size
        end = start + page_size
        total = queryset.count()
        paginated = queryset[start:end]
        return {
            'data': paginated,
            'page': page,
            'page_size': page_size,
            'total': total,
            'pages': (total + page_size - 1) // page_size,
        }
