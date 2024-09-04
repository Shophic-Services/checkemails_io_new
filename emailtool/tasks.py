'''
Register Celery Task
'''
from django.core.mail import EmailMessage as DjangoMail
from celery import shared_task
from app.models import EmailMessage
from emailtool.helper import WebsiteListFetchHelperUpdated
from emailtool.models import EmailListFetch, EmailSearch
from checkemails.celery import app
import csv
from django.http import HttpResponse
from django.conf import settings
from django.template.loader import render_to_string

from datetime import datetime, timedelta


@shared_task(bind=True, max_retries=3)
def get_website_emails(self, uuid):
    data = {}
    emaillistfetch = None
    try:
        emaillistfetch = EmailListFetch.objects.get(uuid=uuid)
    except EmailListFetch.DoesNotExist:
        data['result'] = 'failed'
        data['error_message'] = 'error'
    try:
        WebsiteListFetchHelperUpdated(emaillistfetch).get_email_result()
        data['result'] = 'success'
    except Exception as exc:
        data['result'] = 'failed'
        data['error_message'] = 'error'
        if emaillistfetch:
            emaillistfetch.status = EmailListFetch.ERROR
            emaillistfetch.save()
        self.retry(exc=exc, countdown=60)
    return data

def backup_attachment_in_batches(email, backup_date_file_name, dataset, batch_size=5000):
    part_name = ''
    initial_batch_size = 0
    part_number = 1
    if len(dataset) > 5000:
        part_name = "-part-"
    while True:
        
        emailsearchs = dataset[initial_batch_size:batch_size]
        if not emailsearchs:
            break
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="data_backup_email_searches'+ backup_date_file_name + part_name + str(part_number) +'.csv"'

        writer = csv.writer(response)
        writer.writerow(['Email Address', 'Verified', 'Message', 'Code', 'Added By'])

        for search in emailsearchs:
            writer.writerow([search.email_address, search.verified, search.message, search.code, search.added_by])          

        email.attach('data_backup_email_searches_'+ backup_date_file_name + part_name + str(part_number) +'.csv', response.getvalue(), 'text/csv')
        part_number += 1
        initial_batch_size = batch_size
        batch_size += 5000

    return email
        

def delete_email_searches_in_batches(dataset, batch_size=1000):
    while True:
        # Get the primary keys of the first batch_size records
        email_search_ids = list(dataset.values_list('id', flat=True)[:batch_size])
        
        if not email_search_ids:
            break

        # Delete the records in the current batch
        EmailSearch.objects.filter(id__in=email_search_ids).delete()

@app.task()
def emailsearch_send_data(delete=False):
    emailsearchs = EmailSearch.objects.filter(verified=True).order_by('-create_date')[:50000]
    backup_date_now = datetime.now()
    backup_date = backup_date_now.strftime("%A, %B %d, %Y %I:%M %p")
    backup_date_file_name = backup_date_now.strftime("%Y%m%d_%H%M%S")
    html_content = render_to_string('emailtool/email_template.html', {
        'backup_date': backup_date,
        'description': 'Data Backup',
        'additional_info': {
            'records': len(emailsearchs),
        }
    })

    # Send the CSV file via email
    email = DjangoMail(
        'Data Backup for Checkemails '+  backup_date,
        html_content,
        settings.EMAIL_DEFAULT,
        ['sim@checkemails.io'],
        ['anjali.dhingra@sophicservices.com'],
    )


    email = backup_attachment_in_batches(email, backup_date_file_name, emailsearchs)

    email.content_subtype = 'html' 
    email.send()
    if delete:
        delete_email_searches_in_batches(emailsearchs)