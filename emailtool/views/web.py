
import csv, ast
import itertools
import json
import math
import tldextract
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
import openpyxl
from accounts.models import UserRole
from django.views.generic import CreateView, FormView, TemplateView, View, ListView, DetailView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Subquery, OuterRef, Value, BooleanField
from app import constant
from django.http.response import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from urllib.parse import quote
import smtplib
import dns.resolver
from queue import Empty, Queue
from threading import Thread, Lock
from emailtool.forms import EmailDataFormset, FetchWebsiteEmailDataFormset
from emailtool.helper import CompanyListBulkUploadHelper, generate_pattern, EmailBulkUploadHelper, EmailCheckHelper, WebsiteListFetchHelper, WebsiteListFetchHelperUpdated
from django.utils import timezone

from emailtool.models import EmailListFetch, EmailListGenerate, EmailSearch, SpamKeyword, EmailBulkUpload
from django.db.models.functions import Lower, Concat

from emailtool.tasks import get_website_emails


class DashBoard(LoginRequiredMixin, TemplateView):
    template_name = 'emailtool/dashboard.html'
    

class EmailCheckView(LoginRequiredMixin, TemplateView):

    def validate_email_smtp_dns(self, email):
        try:
            splitAddress = email.split('@')
            domain = str(splitAddress[1])
            fromAddress = email
            
            # MX record lookup
            records = dns.resolver.resolve(domain, 'MX')
            mxRecord = str(records[0].exchange)
            with smtplib.SMTP() as server:
                server.connect(mxRecord)
                server.helo(server.local_hostname)  # Get local server hostname
                server.mail(fromAddress)
                try:
                    # Send the RCPT command for the email address
                    code, message = server.rcpt(str(email))

                except smtplib.SMTPConnectError as e:
                    code, message = 421, "Service isn't available, try again later"
                except smtplib.SMTPAuthenticationError as e:
                    code, message = 535, "Authentication error: " + str(e)
                except smtplib.SMTPException as e:
                    code, message = 500, "Server couldn't recognize the command because of a syntax error"
                except Exception as e:
                    code, message = 500, "Server couldn't recognize the command because of a syntax error"
               
                return code, str(message)
        except Exception as ex:
            return 500, str(ex)

    def update_response_validate(self, code, message, email, response, request):
        verified = False
        if code == 250:
            verified = True
            email_response = {
                'email': email,
                'email_verified': verified,
                'code':code,
                'message':str(message),
                'errors':''
            }
            response['data'].append(email_response)
            if response['success']:
                response['success'] = True
        elif code == 421:
            verified = False
            response['data'].append({
                'email': email,
                'email_verified': verified,
                'code':code,
                'message':str(message),
                'errors': str(message)
            })
            response['success'] = False
        elif code == 535:
            verified = False
            response['data'].append({
                'email': email,
                'email_verified': verified,
                'code':code,
                'message':str(message),
                'errors': str(message)
            })
            response['success'] = False

        elif code == 550:
            verified = False
            response['data'].append({
                'email': email,
                'email_verified': verified,
                'code':code,
                'message':str(message),
                'errors': "Requested command failed because the user's mailbox was unavailable"
            })
            response['success'] = False

            
        else:
            verified = False
            response['data'].append({
                'email': email,
                'email_verified': verified,
                'code':code,
                'message':str(message),
                'errors':str(message)
            })
            response['success'] = False
        return response


    def post(self, request, *args, **kwargs):
        self.response = {'data': [], 'success': True, 'errors': ''}
        email_helper = EmailCheckHelper()
        try:
            try:
                emailList = json.loads(request.POST.get('email_address'))
            except:
                emailList = request.POST.get('email_address')
                if not isinstance(emailList, list):
                    code, message = email_helper.validate_email_smtp_dns(emailList)
                    response = email_helper.update_response_validate(code, message, emailList, self.response)
                    return JsonResponse(self.response)
            
            self.response = email_helper.update_response_validate_bulk(emailList, request)
            
        except Exception as e:
            self.response['sub_errors'] = str(e)
            self.response['errors'] = 'Error in verifying email(s) contact administor for more details - ' + str(e)
            self.response['data'] = []
        return JsonResponse(self.response)

class SingleEmailCheckView(EmailCheckView):
    template_name = 'emailtool/single-email-check.html'


class MultiEmailCheckView(EmailCheckView):
    template_name = 'emailtool/email-check.html'

class SpamEmailCheckView(LoginRequiredMixin, TemplateView):
    template_name = 'emailtool/spam_checker.html'

    def get_context_data(self, **kwargs):
        context = super(SpamEmailCheckView, self).get_context_data(**kwargs)
        spamcategory = list(SpamKeyword.objects.all().values('keyword',category_title=F('category__title'), highlight=F('regex_pattern')))
        spamcategory_json_array = json.dumps(spamcategory)
        
        context.update({
            
            'spamcategory':spamcategory_json_array,
        })
            
        return context

class BulkEmailCheckView(LoginRequiredMixin, TemplateView):
    template_name = 'emailtool/upload_document.html'

    def get_context_data(self, **kwargs):
        context = super(BulkEmailCheckView, self).get_context_data(**kwargs)
        emailuploadfiles = EmailBulkUpload.objects.filter(added_by=self.request.user).order_by('-create_date')

        
        context.update({
            
            'emailuploadfiles':emailuploadfiles,
        })
            
        return context


    def post(self, request, *args, **kwargs):
        file = request.FILES['file'].read()
        file_name= request.POST['file_name']
        updated_file_name= request.POST['updated_file_name']
        existing_path = request.POST['existing_path']
        end = request.POST['end']
        next_slice = request.POST['next_slice']
        
        if file=="" or updated_file_name=="" or existing_path=="" or end=="" or next_slice=="":
            res = JsonResponse({'data':'Invalid Request'})
            return res
        else:
            if existing_path == "null":
                path = 'public/media/documents/' + updated_file_name
                total_email = 0
                with open(path, 'wb+') as destination: 
                    destination.write(file)
                with open(path, 'r', encoding='utf-8') as csv_file:
                    dataReader = csv.reader(csv_file, delimiter=',', quotechar='"')
                    next(dataReader)
                    total_email = len(list(dataReader))
                try:
                    emailuploadfolder = EmailBulkUpload.objects.get(existing_path=updated_file_name)
                except EmailBulkUpload.DoesNotExist:
                    emailuploadfolder = EmailBulkUpload()
                    emailuploadfolder.existing_path = updated_file_name
                    emailuploadfolder.eof = end
                    emailuploadfolder.name = file_name
                    emailuploadfolder.added_by = request.user
                    emailuploadfolder.email_count = total_email
                    emailuploadfolder.save()
                if int(end):
                    emailuploadfolder.eof = int(end)
                    emailuploadfolder.email_count = total_email
                    emailuploadfolder.save()
                    
                    res = JsonResponse({'data':'Uploaded Successfully','existingPath': file_name,
                            'date': emailuploadfolder.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'email_count':emailuploadfolder.email_count,
                            'uuid':str(emailuploadfolder.uuid)})
                    
                else:
                    res = JsonResponse({'existingPath': file_name})
            else:
                path = 'public/media/documents/' + updated_file_name
                try:
                    emailuploadfolder = EmailBulkUpload.objects.get(existing_path=updated_file_name)
                except EmailBulkUpload.DoesNotExist:
                    emailuploadfolder = None
                if emailuploadfolder.name == file_name:
                    if not emailuploadfolder.eof:
                        total_email = 0
                        with open(path, 'ab+') as destination: 
                            destination.write(file)
                        with open(path, 'r', encoding='utf-8') as csv_file:
                            dataReader = csv.reader(csv_file, delimiter=',', quotechar='"')
                            next(dataReader)
                            total_email = len(list(dataReader))

                        if int(end):
                            emailuploadfolder.eof = int(end)
                            emailuploadfolder.email_count = total_email
                            emailuploadfolder.save()
                            res = JsonResponse({'data':'Uploaded Successfully','existingPath':emailuploadfolder.existing_path,
                            'uuid':str(emailuploadfolder.uuid),
                            'date': emailuploadfolder.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'total_count':emailuploadfolder.total_count
                            })
                            
                        else:
                            res = JsonResponse({'existingPath':emailuploadfolder.existing_path})    
                        return res
                    else:
                        res = JsonResponse({'data':'EOF found. Invalid request'})
                        return res
                else:
                    res = JsonResponse({'data':'No such file exists in the existingPath'})
                    return res
            return res

    
class BulkProcessEmailCheckView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            emailuploadfolder = EmailBulkUpload.objects.get(uuid=kwargs.get('uuid'))
        except EmailBulkUpload.DoesNotExist:
            return JsonResponse({'data': 'error in request'})     
        emailuploadfolder.status = EmailBulkUpload.INPROGRESS
        emailuploadfolder.save()       
        EmailBulkUploadHelper(emailuploadfolder, request).get_email_result()
        res = JsonResponse({'data':'Success',})
        return res

# start firstname, lastname, domain
class BulkProcessEmailListView(LoginRequiredMixin,View):

    def get(self, request, *args, **kwargs):
        try:
            emailchecklists = EmailListGenerate.objects.get(uuid=kwargs.get('uuid'))
        except EmailListGenerate.DoesNotExist:
            return JsonResponse({'data': 'error in request'})     
        emailchecklists.status = EmailListGenerate.INPROGRESS
        emailchecklists.save()       
        CompanyListBulkUploadHelper(emailchecklists, request).get_email_result()
        res = JsonResponse({'data':'Success',})
        return res

    def post(self, request, *args, **kwargs):
        file = request.FILES['file'].read()
        file_name= request.POST['file_name']
        updated_file_name= request.POST['updated_file_name']
        existing_path = request.POST['existing_path']
        end = request.POST['end']
        next_slice = request.POST['next_slice']
        
        if file=="" or updated_file_name=="" or existing_path=="" or end=="" or next_slice=="":
            res = JsonResponse({'data':'Invalid Request'})
            return res
        else:
            if existing_path == "null":
                path = 'public/media/documents/' + updated_file_name
                with open(path, 'wb+') as destination: 
                    destination.write(file)
                try:
                    emailchecklists = EmailListGenerate.objects.get(existing_path=updated_file_name)
                except EmailListGenerate.DoesNotExist:
                    emailchecklists = EmailListGenerate.objects.create(
                                        name="Email List - " + timezone.now().strftime('%Y-%m-%d %H-%M-%S') + '.csv',
                                        eof = end,
                                        existing_path = updated_file_name,
                                        dataset=[],
                                        patterns=[],)
                    
                                        
                    if request.user.is_authenticated:
                        emailchecklists.added_by=request.user
                        emailchecklists.save()

                if int(end):                    
                    emailchecklists.eof = int(end)
                    emailchecklists.save()

                    
                    with open(path, 'r', encoding='utf-8') as csv_file:
                        dataReader = csv.reader(csv_file, delimiter=',', quotechar='"')
                        next(dataReader)
                        dataset = list(dataReader)
                        for data in dataset:
                            firstname = data[0].lower()
                            lastname = data[1].lower()
                            domain = data[2].lower()
                            if firstname and lastname and domain:
                                patterns = generate_pattern(firstname,  lastname, domain)
                                emailchecklists.dataset += [{"firstname":firstname, "lastname":lastname,
                                                            "domain": domain}]
                                # emailchecklists.patterns += [patterns]
                                emailchecklists.save()
                    res = JsonResponse({'data':'Uploaded Successfully','existingPath': file_name,
                            'date': emailchecklists.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'filename': 'Website Fetch Email List - ' + emailchecklists.create_date.strftime('%Y-%m-%d %H-%M-%S') + '.csv',
                            'total_count':len(emailchecklists.patterns),
                            'uuid':str(emailchecklists.uuid)})
                    
                else:
                    res = JsonResponse({'existingPath': file_name})
            else:
                path = 'public/media/documents/' + updated_file_name
                try:
                    emailchecklists = EmailListGenerate.objects.get(existing_path=updated_file_name)
                except EmailListGenerate.DoesNotExist:
                    emailchecklists = None
                if emailchecklists.name == file_name:
                    if not emailchecklists.eof:
                        total_email = 0
                        with open(path, 'ab+') as destination: 
                            destination.write(file)

                        if int(end):
                            emailchecklists.eof = int(end)
                            emailchecklists.save()
                            res = JsonResponse({'data':'Uploaded Successfully','existingPath':emailchecklists.existing_path,
                            'uuid':str(emailchecklists.uuid),
                            'date': emailchecklists.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'filename': 'Website Fetch Email List - ' + emailchecklists.create_date.strftime('%Y-%m-%d %H-%M-%S') + '.csv',
                            'total_count':len(emailchecklists.patterns)
                            })
                            
                        else:
                            res = JsonResponse({'existingPath':emailchecklists.existing_path})    
                        return res
                    else:
                        res = JsonResponse({'data':'EOF found. Invalid request'})
                        return res
                else:
                    res = JsonResponse({'data':'No such file exists in the existingPath'})
                    return res
            return res

class EmailCheckListView(LoginRequiredMixin,TemplateView):
    template_name = 'emailtool/emails_list.html'
    
    def get_context_data(self, **kwargs):

        context = super(EmailCheckListView,
                        self).get_context_data(**kwargs)
        
        emailchecklists = EmailListGenerate.objects.filter(added_by=self.request.user).order_by('-create_date')
        
        generate_uuid = self.request.session.get('uuid')
        
        context.update({
            
            'emailchecklists':emailchecklists,
            'generate_uuid':generate_uuid
        })
            
        return context


class GenerateEmailCheckView(LoginRequiredMixin, FormView):
    template_name = 'emailtool/generate_emails_list.html'
    form_class = EmailDataFormset
    success_url = reverse_lazy(
        'emailtool:email_check_list')

    
    def get_context_data(self, **kwargs):

        context = super(GenerateEmailCheckView,
                        self).get_context_data(**kwargs)
        formset = self.form_class()
        context.update({
                'formset': formset,
            })
        return context

    def post(self, request, *args, **kwargs):
        patterns = []
        email_formset = self.form_class(request.POST)
        
        emailchecklists = EmailListGenerate.objects.create(
            name="Email List - " + timezone.now().strftime('%Y-%m-%d %H-%M-%S') + '.csv',            
            eof = 1,
            dataset=[],
            patterns=[],)
        if self.request.user.is_authenticated:
            emailchecklists.added_by=self.request.user
        emailchecklists.existing_path = str(emailchecklists.uuid) + '.csv'
        emailchecklists.save()
        for email_form in email_formset:
            if email_form.is_valid():
                firstname = email_form.cleaned_data.get('firstname').lower()
                lastname = email_form.cleaned_data.get('lastname').lower()
                domain = email_form.cleaned_data.get('domain').lower()
                if firstname and lastname and domain:
                    patterns = generate_pattern(firstname,  lastname, domain)
                    emailchecklists.dataset += [{"firstname":firstname, "lastname":lastname,
                                                "domain": domain}]
                    # emailchecklists.patterns += [patterns]
                    emailchecklists.save()
                    request.session['uuid'] = str(emailchecklists.uuid)
            else:
                return self.form_invalid(email_formset)
        return self.form_valid(email_formset)

class ProcessEmailCheckView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):        
        if request.session.get('uuid'):
            del request.session['uuid']
        try:
            emailchecklists = EmailListGenerate.objects.get(uuid=kwargs.get('uuid'))
        except EmailListGenerate.DoesNotExist:
            return JsonResponse({'data': 'errorin request'})     
        emailchecklists.status = EmailListGenerate.INPROGRESS
        emailchecklists.save()       
        try:
            self.all = [['First Name', 'Last Name','Domain', 'Emails']]
            dataset = ast.literal_eval(emailchecklists.dataset)
            for data in dataset:
                q = Queue()
                lock = Lock()
                domain_extract = tldextract.extract(data['domain'])
                domain = domain_extract.registered_domain
                patterns = generate_pattern(data['firstname'],  data['lastname'], domain)
                for e in patterns:
                    q.put(e)

                self.row = [data['firstname'],  data['lastname'], data['domain']]

                def process_queue(queue: Queue):
                    while True:
                        try:
                            email = queue.get(block=False)
                        except Empty:
                            break
                        code, message = EmailCheckHelper().validate_email_smtp_dns(email)
                        try:
                            email_data = EmailSearch.objects.get(email_address=email)
                        except EmailSearch.MultipleObjectsReturned:
                            EmailSearch.objects.filter(email_address=email).delete()
                            email_data = EmailSearch.objects.create(email_address=email)
                        except EmailSearch.DoesNotExist:
                            email_data = EmailSearch.objects.create(email_address=email)
                        email_data.message = str(message)
                        email_data.verified = False
                        email_data.code = code
                        if self.request.user.is_authenticated:
                            email_data.added_by = self.request.user
                        if code == 250:
                            email_data.verified = True
                            emailchecklists.email_count += 1
                            self.row.append(email)
                        
                        emailchecklists.total_count += 1
                        emailchecklists.patterns.append(email)
                        email_data.save()
                        lock.acquire()
                        lock.release()


                NUM_THREADS = len(patterns)
                threads = []

                for i in range(NUM_THREADS):
                    thread = Thread(target=process_queue, args=(q,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()
                self.all.append(self.row)

            with open('public/media/documents/' + emailchecklists.existing_path, 'w', encoding='utf-8') as csv_file:            
                write_file = csv.writer(csv_file, lineterminator='\n')
                write_file.writerows(self.all)
            emailchecklists.status = EmailListGenerate.COMPLETED
            emailchecklists.save()
        except Exception as ex:
            res = JsonResponse({'data':'Error in processing','error': str(ex)})
            emailchecklists.status = EmailListFetch.ERROR
            emailchecklists.save()
        res = JsonResponse({'data':'Success',})
        return res
    
# fetch website
class FetchEmailCheckListView(LoginRequiredMixin, ListView):
    template_name = 'emailtool/fetch_emails_list.html'
    model = EmailListFetch
    paginate_by = 10
    context_object_name = 'emaillistfetch'

    def get_queryset(self):
        return EmailListFetch.objects.filter(added_by=self.request.user).order_by('-create_date')
    
    def get_context_data(self, **kwargs):

        context = super(FetchEmailCheckListView,
                        self).get_context_data(**kwargs)
        
        generate_uuid = self.request.session.get('uuid')
        
        context['current_page'] = context.pop('page_obj', None)
        
        context.update({
            'generate_uuid':generate_uuid
        })
            
        return context


class GenerateFetchEmailCheckView(LoginRequiredMixin, FormView):
    template_name = 'emailtool/generate_fetch_emails_list.html'
    form_class = FetchWebsiteEmailDataFormset
    success_url = reverse_lazy(
        'emailtool:fetch_email_web_list')

    
    def get_context_data(self, **kwargs):

        context = super(GenerateFetchEmailCheckView,
                        self).get_context_data(**kwargs)
        formset = self.form_class()
        context.update({
                'formset': formset,
            })
        return context

    def post(self, request, *args, **kwargs):
        patterns = []
        email_formset = self.form_class(request.POST)
        
        emaillistfetch = EmailListFetch.objects.create(
            name="Website Fetch Email List - " + timezone.now().strftime('%Y-%m-%d %H-%M-%S') + '.csv',            
            eof = 1,
            dataset=[],
            patterns=[],
            page_patterns=[],
            )
        if self.request.user.is_authenticated:
            emaillistfetch.added_by=self.request.user
        emaillistfetch.existing_path = str(emaillistfetch.uuid) + '.csv'
        emaillistfetch.save()
        for email_form in email_formset:
            if email_form.is_valid():
                website = email_form.cleaned_data.get('website')
                if website:
                    emaillistfetch.dataset += [{"website":website}]
                    emaillistfetch.save()
                    request.session['uuid'] = str(emaillistfetch.uuid)
            else:
                return self.form_invalid(email_formset)
        return self.form_valid(email_formset)

class ProcessFetchEmailCheckView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):        
        if request.session.get('uuid'):
            del request.session['uuid']
        try:
            emaillistfetch = EmailListFetch.objects.get(uuid=kwargs.get('uuid'))
        except EmailListFetch.DoesNotExist:
            return JsonResponse({'data': 'errorin request'})     
        emaillistfetch.status = EmailListFetch.INPROGRESS
        emaillistfetch.total_count = 0
        emaillistfetch.page_patterns = []
        emaillistfetch.patterns = []
        emaillistfetch.save()     
        
        if settings.CELERY_ENABLED:
            get_website_emails.delay(emaillistfetch.uuid)
        else:
            get_website_emails(emaillistfetch.uuid)  
        res = JsonResponse({'data':'Success',})
        return res
    
class BulkProcessFetchEmailListView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            emaillistfetch = EmailListFetch.objects.get(uuid=kwargs.get('uuid'))
        except EmailListFetch.DoesNotExist:
            return JsonResponse({'data': 'error in request'})     
        emaillistfetch.status = EmailListFetch.INPROGRESS
        emaillistfetch.save()       
        
        if settings.CELERY_ENABLED:
            get_website_emails.delay(emaillistfetch.uuid)
        else:
            get_website_emails(emaillistfetch.uuid)  
        res = JsonResponse({'data':'Success',})
        return res

    def post(self, request, *args, **kwargs):
        file = request.FILES['file'].read()
        file_name= request.POST['file_name']
        updated_file_name= request.POST['updated_file_name']
        existing_path = request.POST['existing_path']
        end = request.POST['end']
        next_slice = request.POST['next_slice']
        
        if file=="" or updated_file_name=="" or existing_path=="" or end=="" or next_slice=="":
            res = JsonResponse({'data':'Invalid Request'})
            return res
        else:
            if existing_path == "null":
                path = 'public/media/documents/' + updated_file_name
                with open(path, 'wb+') as destination: 
                    destination.write(file)
                try:
                    emaillistfetch = EmailListFetch.objects.get(existing_path=updated_file_name)
                except EmailListFetch.DoesNotExist:
                    emaillistfetch = EmailListFetch.objects.create(
                                        name="Website Fetch Email List - " + timezone.now().strftime('%Y-%m-%d %H-%M-%S') + '.csv',
                                        eof = end,
                                        existing_path = updated_file_name,
                                        dataset=[],
                                        patterns=[],
                                        page_patterns=[],
                                        )
                    
                                        
                    if request.user.is_authenticated:
                        emaillistfetch.added_by=request.user
                        emaillistfetch.save()

                if int(end):                    
                    emaillistfetch.eof = int(end)
                    emaillistfetch.save()

                    
                    with open(path, 'r', encoding='utf-8') as csv_file:
                        dataReader = csv.reader(csv_file, delimiter=',', quotechar='"')
                        next(dataReader)
                        dataset = list(dataReader)
                        for data in dataset:
                            website = data[0]
                            if website:
                                emaillistfetch.dataset += [{"website":website}]
                                # emaillistfetch.patterns += [patterns]
                                emaillistfetch.save()
                    res = JsonResponse({'data':'Uploaded Successfully','existingPath': file_name,
                            'date': emaillistfetch.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'total_count':len(emaillistfetch.patterns),
                            'uuid':str(emaillistfetch.uuid)})
                    
                else:
                    res = JsonResponse({'existingPath': file_name})
            else:
                path = 'public/media/documents/' + updated_file_name
                try:
                    emaillistfetch = EmailListFetch.objects.get(existing_path=updated_file_name)
                except EmailListFetch.DoesNotExist:
                    emaillistfetch = None
                if emaillistfetch.name == file_name:
                    if not emaillistfetch.eof:
                        total_email = 0
                        with open(path, 'ab+') as destination: 
                            destination.write(file)

                        if int(end):
                            emaillistfetch.eof = int(end)
                            emaillistfetch.save()
                            res = JsonResponse({'data':'Uploaded Successfully','existingPath':emaillistfetch.existing_path,
                            'uuid':str(emaillistfetch.uuid),
                            'date': emaillistfetch.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'total_count':len(emaillistfetch.patterns)
                            })
                            
                        else:
                            res = JsonResponse({'existingPath':emaillistfetch.existing_path})    
                        return res
                    else:
                        res = JsonResponse({'data':'EOF found. Invalid request'})
                        return res
                else:
                    res = JsonResponse({'data':'No such file exists in the existingPath'})
                    return res
            return res



class BackupEmailSearchView(LoginRequiredMixin, View):
    
    delete = False

    def get(self, request, *args, **kwargs):

        from emailtool.tasks import emailsearch_send_data
        emailsearch_send_data(self.delete)
        request.session['backup'] = True
        return HttpResponseRedirect(reverse_lazy('admin:emailtool_backupemailsearch_changelist'))


class BackupEmailSearchDeleteView(BackupEmailSearchView):
    delete = True
