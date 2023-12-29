
import csv, ast
import itertools
import json
import math
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
from django.utils.http import urlquote
import smtplib
import dns.resolver
from queue import Empty, Queue
from threading import Thread, Lock
from emailtool.forms import EmailDataFormset
from emailtool.helper import EmailBulkUploadHelper, EmailCheckHelper
from django.utils import timezone

from emailtool.models import EmailListGenerate, EmailSearch, SpamKeyword, EmailBulkUpload
from django.db.models.functions import Lower, Concat


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

class SpamEmailCheckView(TemplateView):
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
        emailuploadfiles = EmailBulkUpload.objects.filter(added_by=self.request.user).order_by('-modify_date')
        
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

    
class ProcessEmailCheckView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            emailuploadfolder = EmailBulkUpload.objects.get(uuid=kwargs.get('uuid'))
        except EmailBulkUpload.DoesNotExist:
            return JsonResponse({'data': 'errorin request'})     
        emailuploadfolder.status = EmailBulkUpload.INPROGRESS
        emailuploadfolder.save()       
        EmailBulkUploadHelper(emailuploadfolder).get_email_result()
        res = JsonResponse({'data':'Success',})
        return res

class EmailCheckListView(TemplateView):
    template_name = 'emailtool/emails_list.html'
    
    def get_context_data(self, **kwargs):

        context = super(EmailCheckListView,
                        self).get_context_data(**kwargs)
        
        emailchecklists = EmailListGenerate.objects.all().order_by('-modify_date')
        
        generate_uuid = self.request.session.get('uuid')
        
        context.update({
            
            'emailchecklists':emailchecklists,
            'generate_uuid':generate_uuid
        })
            
        return context


class GenerateEmailCheckView(FormView):
    template_name = 'emailtool/generate_emails_list.html'
    form_class = EmailDataFormset
    success_url = reverse_lazy(
        'emailtool:email_check_list')

    def generate_pattern(self, first_name='', last_name='', domain=''):
        first_initial = first_name[0] if first_name else ''
        last_initial = last_name[0] if last_name else ''


        patterns = [
            first_name,
            last_name,
            first_name + last_name,
            f"{first_name}.{last_name}",
            f"{first_initial}{last_name}",
            f"{first_initial}.{last_name}",
            f"{first_name}{last_initial}",
            f"{first_name}.{last_initial}",
            f"{first_initial}{last_initial}",
            f"{first_initial}.{last_initial}",
            last_name + first_name,
            f"{last_name}.{first_name}",
            f"{last_name}{first_initial}",
            f"{last_name}.{first_initial}",
            f"{last_initial}{first_name}",
            f"{last_initial}.{first_name}",
            f"{last_initial}{first_initial}",
            f"{last_initial}.{first_initial}",

            f"{first_name}-{last_name}",
            f"{first_initial}-{last_name}",
            f"{first_name}-{last_initial}",
            f"{first_initial}-{last_initial}",
            f"{last_name}-{first_name}",
            f"{last_name}-{first_initial}",
            f"{last_initial}-{first_name}",
            f"{last_initial}-{first_initial}",

            f"{first_name}_{last_name}",
            f"{first_initial}_{last_name}",
            f"{first_name}_{last_initial}",
            f"{first_initial}_{last_initial}",
            f"{last_name}_{first_name}",
            f"{last_name}_{first_initial}",
            f"{last_initial}_{first_name}",
            f"{last_initial}_{first_initial}",

        ]

        if domain:
            patterns = [pattern + '@' + domain for pattern in patterns]

        return patterns

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
            dataset=[],
            patterns=[],)
        if self.request.user.is_authenticated:
            emailchecklists.added_by=self.request.user
        emailchecklists.existing_path = str(emailchecklists.uuid) + '.csv'
        emailchecklists.save()
        for email_form in email_formset:
            if email_form.is_valid():
                firstname = email_form.cleaned_data.get('firstname')
                lastname = email_form.cleaned_data.get('lastname')
                domain = email_form.cleaned_data.get('domain')
                if firstname and lastname and domain:
                    patterns = self.generate_pattern(firstname,  lastname, domain)
                    emailchecklists.dataset += [{"firstname":firstname, "lastname":lastname,
                                                "domain": domain}]
                    emailchecklists.patterns += patterns
                    emailchecklists.save()
                    request.session['uuid'] = str(emailchecklists.uuid)
            else:
                return self.form_invalid(email_formset)
        return self.form_valid(email_formset)

class ProcessEmailCheckView(View):

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
            all = [['Emails']]
            for data in ast.literal_eval(emailchecklists.patterns):
                row = []
                code, message = EmailCheckHelper().validate_email_smtp_dns(data)
                if code == 250:
                    emailchecklists.email_count += 1
                    row.append(data)
                    all.append(row)
            with open('public/media/documents/' + emailchecklists.existing_path, 'w', encoding='utf-8') as csv_file:            
                write_file = csv.writer(csv_file, lineterminator='\n')
                write_file.writerows(all)
            emailchecklists.status = EmailListGenerate.COMPLETED
            emailchecklists.save()
        except Exception as ex:
            print(ex)
            pass
        res = JsonResponse({'data':'Success',})
        return res