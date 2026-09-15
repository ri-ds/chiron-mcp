from django.template.loader import get_template
from django.core.mail import send_mail

from chiron import chiron_settings


def send_email_report_notification(chiron_user, user_content, full_link):
    """
    Sends an email notification to a user when a saved item (report) has been shared with them.

    Args:
        chiron_user: An object representing the user the email is being sent to
        user_content: The content or details of the shared report to be included in the email.
        full_link: The full URL link to the shared report.

    Returns:
        None

    Side Effects:
        Sends an email to the specified user using the configured email templates and settings.
    """
    email_from = chiron_settings.CHIRON_EMAIL_FROM
    email_subject = "[{site_title}] A saved item has been shared with you.".format(
        site_title=chiron_settings.CHIRON_SITE_TITLE
    )
    email_html_body = get_template("chiron/emails/new_shared_report.html").render(
        {
            "user_content": user_content,
            "user": chiron_user.user,
            "link": full_link,
            "footer": get_template(chiron_settings.CHIRON_FOOTER_TEMPLATE).render(),
        }
    )

    email_text_body = get_template("chiron/emails/new_shared_report.txt").render(
        {
            "user_content": user_content,
            "user": chiron_user.user,
            "link": full_link,
        }
    )

    send_mail(
        subject=email_subject,
        message=email_text_body,
        from_email=email_from,
        recipient_list=[chiron_user.user.email],
        html_message=email_html_body,
    )
