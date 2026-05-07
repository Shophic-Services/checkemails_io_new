from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
from django.db.models import JSONField
from checkemails.core.base_models import (CheckEmailsBaseModel, CheckEmailsModelWithoutUser,)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from tools import constants
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField

class SpamCategory(CheckEmailsModelWithoutUser):

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


class SpamKeyword(CheckEmailsModelWithoutUser):

    keyword = models.CharField(max_length=255)
    regex_pattern = models.CharField(max_length=500, null=True,blank=True)
    category = models.ForeignKey(SpamCategory, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % (self.keyword)

    
    class Meta:
        verbose_name = 'Spam Keyword'
        verbose_name_plural = 'Spam Keywords'

class EmailData(CheckEmailsModelWithoutUser):

    VALID = 1
    INVALID = 2
    RISKY = 3
    CATCHALL = 4
    UNKNOWN = 5
    SYNTAX_ERROR = 6
    DISPOSABLE = 7
    PROFESSIONAL = 8
    WEBMAIL = 9

    
    SMTP = 1
    SWAKS = 2
    SCRAPED = 3
    MANUAL = 4
    SOCIAL = 5

    QUALITY = (
        (UNKNOWN, 'Unknown'),
        (INVALID, 'Invalid'),
        (VALID, 'Valid'),
        (RISKY, 'Risky'),
    )
    
    STATUS = (
        (VALID, 'Ok'),
        (INVALID, 'Invalid'),
        (RISKY, 'Risky'),
        (CATCHALL, 'Catch All'),
        (DISPOSABLE, 'Disposable'),
        (UNKNOWN, 'Unknown'),
        (SYNTAX_ERROR, 'Syntax error')
    )
    STATUS_DICT = dict(STATUS)
    EMAIL_TYPE = (
        (PROFESSIONAL , 'Professional'),
        (WEBMAIL , 'Webmail'),
        (DISPOSABLE , 'Disposable'),
        (UNKNOWN , 'Unknown'),
    )
    EMAIL_SOURCE = (
        (SMTP , 'SMTP'),
        (SWAKS , 'Swaks'),
        (SCRAPED , 'Scraped'),
        (MANUAL, 'Manual'),
        (SOCIAL, 'Social')
    )

    email = models.EmailField()
    valid = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    code = models.IntegerField(default=204)
    email_result = models.CharField(max_length=500)
    disposable = models.BooleanField(default=False)
    professional = models.BooleanField(default=False)
    domain_age = models.IntegerField(default=0)
    has_domain_mx = models.BooleanField(default=False)
    has_dmarc = models.BooleanField(default=False)
    has_spf = models.BooleanField(default=False)
    has_smtp = models.BooleanField(default=False)
    role_based = models.BooleanField(default=False)
    retry_later = models.BooleanField(default=False)
    catch_all = models.BooleanField(default=False)
    permanent_failure = models.BooleanField(default=False)
    needs_manual_review = models.BooleanField(default=False)
    status = models.PositiveIntegerField(choices=STATUS, default=UNKNOWN)
    quality = models.PositiveIntegerField(choices=QUALITY, default=UNKNOWN)
    email_source = models.PositiveIntegerField(choices=EMAIL_SOURCE, default=MANUAL)
    email_type = models.PositiveIntegerField(choices=EMAIL_TYPE, default=UNKNOWN)

    class Meta:
        verbose_name = 'Email Data'

    def __str__(self):
        return self.email
    

class LeadFinder(CheckEmailsModelWithoutUser):
    '''
    Lead Finder Model
    '''

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.ForeignKey(
        EmailData,
        on_delete=models.CASCADE,
        related_name='lead_finders'
    )
    company = models.CharField(max_length=255, null=True, blank=True)
    position = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    social_links = ArrayField(models.URLField(max_length=500, null=True, blank=True), null=True, blank=True, default=list)

    def __str__(self):
        return u'%s - %s' % (self.name, self.email)



class DataSourceJob(CheckEmailsBaseModel):
    '''
    Data Source Job
    Supports bulk upload, website fetch, API & CRM sources
    '''

    PENDING = 1
    STARTED = 2
    INPROGRESS = 3
    ERROR = 4
    COMPLETED = 5
    UPLOAD_ERROR = 6



    STATUS_MAP = {
        "ALL": None,
        "PROCESSING": [STARTED, INPROGRESS],
        "COMPLETED": [COMPLETED],
        "UNPROCESSED": [PENDING],
        "FAILED": [ERROR]
    }

    STATUS_TYPE = (
        (PENDING, _('Pending')),
        (STARTED, 'Started'),
        (INPROGRESS, _('In Progress')),
        (COMPLETED, _('Completed')),
        (ERROR, _('Failed')),
        (UPLOAD_ERROR, _('Upload Failed')),
    )

    SOURCE_TYPE = (
        (constants.SINGLE, 'Single'),
        (constants.BULK, 'Bulk'),
        (constants.WEBSITE, 'Website'),
        (constants.LEAD, 'Lead'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    source_type = models.SmallIntegerField(
        choices=SOURCE_TYPE
    )
    source_reference = models.FileField(
        upload_to='source-reference/', max_length=500, 
        verbose_name='Source Reference', null=True, blank=True)
    source_format=models.CharField(max_length=50, null=True, blank=True)

    status = models.SmallIntegerField(
        choices=STATUS_TYPE,
        default=PENDING
    )

    total_items = models.PositiveIntegerField(default=0)
    total_duplicate = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)
    valid_count = models.PositiveIntegerField(default=0)
    risky_count = models.PositiveIntegerField(default=0)
    syntax_invalid_count = models.PositiveIntegerField(default=0)
    role_based_count = models.PositiveIntegerField(default=0)
    disposable_count = models.PositiveIntegerField(default=0)
    catch_all_count = models.PositiveIntegerField(default=0)
    invalid_count = models.PositiveIntegerField(default=0)
    unknown_count = models.PositiveIntegerField(default=0)
    upload_completed = models.BooleanField(default=False)
    upload_started_at = models.DateTimeField(auto_now_add=True)
    upload_completed_at = models.DateTimeField(null=True, blank=True)
    first_row_label=models.BooleanField(default=False)
    duplicate_confirm=models.BooleanField(default=False)
    selected_file_columns=ArrayField(models.CharField(max_length=500), null=True, blank=True, default=list)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    input_references = ArrayField(models.CharField(max_length=500), null=True, blank=True, default=list)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatch_task_id = models.CharField(max_length=255, null=True, blank=True)
    finalize_task_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = _('Data Source Job')
        verbose_name_plural = _('Data Source Jobs')
        ordering        = ["-create_date"]

    def __str__(self):
        return f'{self.name} ({self.get_source_type_display()})'
    
    @property
    def progress_percent(self):
        if not self.total_items:
            return 0
        return round((self.completed_count / self.total_items) * 100, 2)

class DataSourceItem(CheckEmailsBaseModel):
    '''
    Mapping between DataSourceJob and EmailData
    Stores per-source verification result
    '''

    PENDING = 1
    STARTED = 2
    INPROGRESS = 3
    COMPLETED = 4
    FAILED = 5

    RESULT_TYPE = (
        (PENDING, _('Pending')),
        (STARTED, 'Started'),
        (INPROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    )

    source_job = models.ForeignKey(
        DataSourceJob,
        on_delete=models.CASCADE,
        related_name='source_items',
    )

    input_value = models.CharField(max_length=255)
    result_data = models.JSONField(
        default=dict
    )

    status = models.SmallIntegerField(
        choices=RESULT_TYPE,
        default=PENDING
    )

    class Meta:
        verbose_name = 'Data Source Item'
        verbose_name_plural = 'Data Source Items'
        ordering        = ["-create_date"]
        indexes = [
            models.Index(fields=['source_job']),
            models.Index(fields=['result_data']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.source_job.name} ({self.input_value})'


class ScraperResult(CheckEmailsBaseModel):
    """
    One row per email found.
    Multiple rows can share the same source_item (one URL → many emails).
    Mirrors the flat 'emails_flat' sheet from the standalone script.
    """
    source_item  = models.ForeignKey(DataSourceItem, on_delete=models.CASCADE, related_name="results")
    source_job   = models.ForeignKey(DataSourceJob,  on_delete=models.CASCADE, related_name="results") 
    url          = models.TextField()
    final_url    = models.TextField(null=True, blank=True)
    scrape_name = models.CharField(max_length=255, null=True, blank=True)
    emaildata    = ArrayField(models.EmailField(), default=list)
    scrapedata   = models.JSONField(default=dict)
    http_status  = models.IntegerField(null=True, blank=True)
 
    class Meta:
        unique_together = [("source_job", "url")]
        ordering        = ["id"]
 
    def __str__(self):
        return f"{self.source_job} @ {self.url}"