from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
from django.db.models import JSONField
from checkemails.core.base_models import (CheckEmailsBaseModel,)

class SpamCategory(CheckEmailsBaseModel):

    URGENCY = 'pushy'
    SHADY = 'crafty'
    OVERPROMISE = 'overcommit'
    MONEY = 'monetary'
    UNNATURAL = 'notnatural'

    SPAM_CATEGORY_CHOICES = (
        (URGENCY, 'Pushy'),
        (SHADY, 'Crafty'),
        (OVERPROMISE, 'Overcommit'),
        (MONEY, 'Monetary'),
        (UNNATURAL, 'Not natural'),
    )

    title = models.CharField(max_length=255, choices=SPAM_CATEGORY_CHOICES, unique=True)

    def __str__(self):
        return u'%s' % (self.get_title_display())

    
    class Meta:
        verbose_name = 'Spam Category'
        verbose_name_plural = 'Spam Categories'


class SpamKeyword(CheckEmailsBaseModel):

    keyword = models.CharField(max_length=255)
    regex_pattern = models.CharField(max_length=500, null=True,blank=True)
    category = models.ForeignKey(SpamCategory, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % (self.keyword)

    
    class Meta:
        verbose_name = 'Spam Keyword'
        verbose_name_plural = 'Spam Keywords'



class EmailSearch(CheckEmailsBaseModel):
    email_address = models.CharField(max_length=500)
    verified = models.BooleanField(default=False)
    message = models.TextField()
    code = models.CharField(max_length=250)

    class Meta:
        verbose_name = 'Email Search'
        verbose_name_plural = 'Email Search'



class BackupEmailSearch(EmailSearch):
    
    class Meta:
        verbose_name = 'Backup Email Search'
        verbose_name_plural = 'Backup Email Search'

        
class EmailBulkUpload(CheckEmailsBaseModel):
    
    PENDING = 1
    INPROGRESS = 2
    COMPLETED = 3
    ERROR = 4

    STATUS_TYPE = ((PENDING, _('Pending')), (INPROGRESS, _('Processing')),
                   (COMPLETED, _('Completed')), (ERROR, _('Error')))

    
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    existing_path = models.CharField(max_length=100)
    name = models.CharField(max_length=50)
    eof = models.BooleanField()
    status = models.SmallIntegerField(
        choices=STATUS_TYPE, default=PENDING)
    valid_count = models.IntegerField(default=0)
    invalid_count = models.IntegerField(default=0)
    email_count = models.IntegerField(default=0)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Email Bulk Upload'
        verbose_name_plural = 'Email Bulk Uploads'



class EmailListGenerate(CheckEmailsBaseModel):
    
    PENDING = 1
    INPROGRESS = 2
    COMPLETED = 3
    ERROR = 4

    STATUS_TYPE = ((PENDING, _('Pending')), (INPROGRESS, _('Processing')),
                   (COMPLETED, _('Completed')), (ERROR, _('Error')))

    
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    existing_path = models.CharField(max_length=100)
    dataset = models.TextField(default=[])
    eof = models.BooleanField()
    status = models.SmallIntegerField(
        choices=STATUS_TYPE, default=PENDING)
    email_count = models.IntegerField(default=0)
    total_count = models.IntegerField(default=0)
    patterns = ArrayField(
        models.EmailField(max_length=255), blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Email List Generate'
        verbose_name_plural = 'Email List Generates'


class EmailListFetch(CheckEmailsBaseModel):
    
    PENDING = 1
    INPROGRESS = 2
    COMPLETED = 3
    ERROR = 4

    STATUS_TYPE = ((PENDING, _('Pending')), (INPROGRESS, _('Processing')),
                   (COMPLETED, _('Completed')), (ERROR, _('Error')))

    
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    existing_path = models.CharField(max_length=100)
    dataset = models.TextField(default=[])
    eof = models.BooleanField()
    status = models.SmallIntegerField(
        choices=STATUS_TYPE, default=PENDING)
    page_count = models.IntegerField(default=0)
    total_count = models.IntegerField(default=0)
    patterns = ArrayField(
        models.EmailField(max_length=255), blank=True, null=True)
    page_patterns = ArrayField(
        models.URLField(max_length=500), blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Email List Fetch'
        verbose_name_plural = 'Email List Fetchs'