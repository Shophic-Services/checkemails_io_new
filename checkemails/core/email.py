'''
Email reusable component
'''

from django.conf import settings
from django.core.mail import EmailMessage as DjangoMail
from django.template.loader import get_template

from app.models import EmailMessage
from checkemails.tasks import send_email


class Email(object):
    ''' 
    Email Create Object 
    '''

    def __init__(self, to, subject, html_message=None, cc=None, bcc=None, from_addr=None):
        if not isinstance(to, list):
            self.to = [to, ]
        else:            
            self.to = to
        if cc and not isinstance(cc, list) :
            self.cc = [cc, ]
        else:
            self.cc = cc
        if bcc and not isinstance(bcc, list):
            self.bcc = [bcc, ]
        else:
            self.bcc = bcc
        self.subject = subject
        self.html = html_message
        self.from_addr = from_addr

    def html(self, html):
        ''' Html object '''
        self.html = html
        return self

    def from_address(self, from_address):
        ''' From Address '''
        self.from_addr = from_address
        return self

    def message_from_template(self, template_name, context, request=None):
        ''' Message Body '''
        context.update({
            'protocol': settings.SITE_PROTOCOL,
            'domain': settings.SITE_DOMAIN
        })
        self.html = get_template(template_name).render(context, request)
        return self

    def send(self):
        ''' Create mail object '''
        if not self.from_addr:
            self.from_addr = settings.EMAIL_DEFAULT
        if not self.html:
            raise Exception('Text or HTMl is required')
        email_data = {
            'from_email': self.from_addr,
            'to_email': self.to,
            'cc': self.cc,
            'bcc': self.bcc,
            'subject': self.subject,
            'html_message': self.html
        }
        email_obj = EmailMessage.objects.create(**email_data)
        ''' sending email '''
        try:
            if settings.CELERY_ENABLED:
                send_email.delay(email_obj.pk)
            else:
                send_email(email_obj.pk)
        except Exception as ex:
            pass
