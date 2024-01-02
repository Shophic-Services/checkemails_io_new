
import itertools, re
import smtplib, csv
import dns.resolver
from queue import Empty, Queue
from threading import Thread, Lock

from emailtool.models import EmailSearch, EmailBulkUpload

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class EmailCheckHelper(object):
    

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

    def update_response_validate(self, code, message, email, response):
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

    def update_response_validate_bulk(self, email_list,request):
        
        self.response = {'data': [], 'success': True, 'errors': ''}
        q = Queue()
        lock = Lock()
        for e in email_list:
            q.put(e)


        def process_queue(queue: Queue):
            while True:
                try:
                    email = queue.get(block=False)
                except Empty:
                    break
                code, message = self.validate_email_smtp_dns(email)
                response = self.update_response_validate(code, message, email, self.response)
                lock.acquire()
                lock.release()


        NUM_THREADS = len(email_list)
        threads = []

        for i in range(NUM_THREADS):
            thread = Thread(target=process_queue, args=(q,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        
        for data in self.response['data']:                
            try:
                email_data = EmailSearch.objects.get(email_address=data['email'])
            except EmailSearch.MultipleObjectsReturned:
                EmailSearch.objects.filter(email_address=data['email']).delete()
                email_data = EmailSearch.objects.create(email_address=data['email'])
            except EmailSearch.DoesNotExist:
                email_data = EmailSearch.objects.create(email_address=data['email'])
            email_data.verified = data['email_verified']
            email_data.message = str(data['message'])
            email_data.code = data['code']
            email_data.added_by = request.user
            email_data.save()

        return self.response

class EmailBulkUploadHelper(object):
    def __init__(self, instance, request, *args, **kwargs):
        self.instance = instance
        self.request = request

    def update_response_validate(self, code, message, email, row, column, response):

        status = 'In-Valid'
        if code == 250:
            status = 'Valid'
        
        try:
            response[row]
        except:
            response.update({row:{}})
        
        try:
            response[row][column] = {
                'email': email,
                'code':code,
                'message':message,
                'status':status,
            }
        except:
            response[row] = {column:{
                'email': email,
                'code':code,
                'message':message,
                'status':status,
            }}

    def get_email_result(self):
        try:
            all = []
            all_updated = []
            with open('public/media/documents/' + self.instance.existing_path, 'r', encoding='utf-8') as csv_file:
                dataReader = csv.reader(csv_file, delimiter=',', quotechar='"')
                self.instance.valid_count = 0
                self.instance.invalid_count = 0
                write_row = next(dataReader)
                index_set = []
                email_addresses = []
                for row_index, row in enumerate(dataReader):
                    email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
                    email_addresses += [(row_index, index, element) for index, element in enumerate(row) if email_regex.match(element)]
                    all.append(row)
                
                self.response = {}

                q = Queue()
                lock = Lock()
                for e in email_addresses:
                    q.put(e)


                def process_queue(queue: Queue):
                    while True:
                        try:
                            row, column, email = queue.get(block=False)
                        except Empty:
                            break
                        code, message = EmailCheckHelper().validate_email_smtp_dns(email)
                        self.update_response_validate(code, message, email,row, column,  self.response)
                        lock.acquire()
                        lock.release()


                NUM_THREADS = len(email_addresses)
                threads = []

                for i in range(NUM_THREADS):
                    thread = Thread(target=process_queue, args=(q,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()
                sorted_data_outer = dict(sorted(self.response.items()))
                sorted_data_inner = {outer_key: dict(sorted(inner_dict.items())) for outer_key, inner_dict in sorted_data_outer.items()}
                for row, row_data in sorted_data_inner.items():
                    index = 0
                    for column, column_data in row_data.items():
                        try:
                            email_data = EmailSearch.objects.get(email_address=column_data['email'])
                        except EmailSearch.MultipleObjectsReturned:
                            EmailSearch.objects.filter(email_address=column_data['email']).delete()
                            email_data = EmailSearch.objects.create(email_address=column_data['email'])
                        except EmailSearch.DoesNotExist:
                            email_data = EmailSearch.objects.create(email_address=column_data['email'])
                        email_data.message = str(column_data['message'])
                        email_data.verified = False
                        email_data.code = column_data['code']
                        if self.request.user.is_authenticated:
                            email_data.added_by = self.request.user
                        index_value = column
                        index_set.append(index_value + index)
                        index += 1
                        if column_data['code'] == 250:
                            email_data.verified = True
                            self.instance.valid_count += 1
                            all[row].insert(index_value + index, 'Valid')
                            all_updated.append(all[row])
                        else:
                            self.instance.invalid_count += 1
                            all[row].insert(index_value + index, 'InValid')
                            all_updated.append(all[row])

                        email_data.save()
                for data in sorted(set(index_set)):
                    write_row.insert(data+1, 'Output')
                all_updated.insert(0, write_row)
                self.instance.status = EmailBulkUpload.COMPLETED
            with open('public/media/documents/' + self.instance.existing_path, 'w', encoding='utf-8') as csv_file:            
                write_file = csv.writer(csv_file, lineterminator='\n')
                write_file.writerows(all_updated)

        except Exception as ex:
            print(ex)
            self.instance.description = str(ex)
            self.instance.status = EmailBulkUpload.ERROR
        self.instance.save()