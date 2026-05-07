'''
Register Celery Task
'''
from django.core.mail import EmailMessage as DjangoMail
from checkemails.celery import app
from core.models import EmailMessage
from checkemails.celery import ScopeBasedTask
from celery.contrib import rdb


@app.task(bind=True, max_retries=3, base=ScopeBasedTask)
def send_email(self, email_id, *args, **kwargs):
    # rdb.set_trace()
    '''
    Send Email
    '''
    data = {}
    try:
        email_obj = EmailMessage.objects.filter(pk=email_id).first()
        data = {'email': email_obj.to_email,
                'from_email': email_obj.from_email,
                'subject': email_obj.subject}
        if isinstance(email_obj.to_email, list):
            to_email = email_obj.to_email
        else:
            to_email = email_obj.to_email.split(",")
        email = DjangoMail(
            email_obj.subject,
            email_obj.html_message,
            email_obj.from_email,
            to=to_email,
            cc=email_obj.cc,
            bcc=email_obj.bcc)
        email.content_subtype = "html"
        email.send()
        email_obj.sent_status = EmailMessage.SENT
        email_obj.save()
        data['result'] = 'success'
    except Exception as exc:
        data['result'] = 'failed'
        data['error_message'] = 'error'
        if email_obj:
            email_obj.sent_status = EmailMessage.ERROR
            email_obj.save()
        self.retry(exc=exc, countdown=60)
    return data
