from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from checkemails.core.base_models import (CheckEmailsBaseModel, CheckEmailsBaseWithDeleteModel)

import uuid, os
from datetime import datetime
from accounts import constant as account_constant
from django.contrib.postgres.fields import JSONField

class EmailMessage(CheckEmailsBaseModel):
    '''
    Email Model
    '''
    PENDING = 1
    INPROGRESS = 2
    SENT = 3
    ERROR = 4

    STATUS_TYPE = ((PENDING, _('Pending')), (INPROGRESS, _('In-Progress')),
                   (SENT, _('Sent')), (ERROR, _('Error')))

    from_email = models.EmailField(default=settings.EMAIL_DEFAULT)
    to_email = ArrayField(
        models.EmailField(max_length=255), blank=True, null=True)
    cc = ArrayField(models.EmailField(max_length=255), blank=True, null=True)
    bcc = ArrayField(models.EmailField(max_length=255), blank=True, null=True)
    subject = models.TextField(null=True, blank=True)
    html_message = models.TextField()
    tries = models.PositiveSmallIntegerField(default=0)
    error_detail = models.CharField(max_length=255, null=True, blank=True)
    sent_status = models.SmallIntegerField(
        choices=STATUS_TYPE, default=PENDING)
    sent_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return u'%s' % self.id

