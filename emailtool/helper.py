
import itertools, re, ast, urllib.request, time
import smtplib, csv
import dns.resolver
from queue import Empty, Queue
from threading import Thread, Lock
import tldextract
from emailtool.models import EmailListFetch, EmailListGenerate, EmailSearch, EmailBulkUpload

import re
import requests
import requests.exceptions
from urllib.parse import urlsplit
from collections import deque
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning, SoupStrainer
from gazpacho import Soup, get as gazpacho_get

from requests.exceptions import SSLError

def generate_pattern(first_name='', last_name='', domain=''):
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


class CompanyListBulkUploadHelper(object):
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
            self.all = [['First Name', 'Last Name','Domain', 'Emails']]
            
            dataset = ast.literal_eval(self.instance.dataset)
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
                        if code == 250:
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
                            email_data.verified = True
                            self.instance.email_count += 1
                            self.row.append(email)
                            
                            self.instance.total_count += 1
                            self.instance.patterns.append(email)
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

            with open('public/media/documents/' + self.instance.existing_path, 'w', encoding='utf-8') as csv_file:            
                write_file = csv.writer(csv_file, lineterminator='\n')
                write_file.writerows(self.all)
            self.instance.status = EmailListGenerate.COMPLETED
            self.instance.save()

        except Exception as ex:
            print(ex)
            self.instance.description = str(ex)
            self.instance.status = EmailBulkUpload.ERROR
        self.instance.save()


class WebsiteListFetchHelper(object):

    def __init__(self, instance, request, *args, **kwargs):
        self.instance = instance
        self.request = request

    def fetch_emails(self, url):
        try:
            response = requests.get(url, timeout=10)  # Added timeout parameter
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            # Find all email addresses using a regular expression
            email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
            emails = set(re.findall(email_pattern, soup.text))

            return emails

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            return None
        
    def get_email_result(self):
        try:
            self.all = [['Website','Emails']]
            
            dataset = ast.literal_eval(self.instance.dataset)
            for data in dataset:
                q = Queue()
                lock = Lock()
                self.instance.page_count += 1
                self.instance.page_patterns.append(data['website'])
                self.instance.save()
                patterns = self.fetch_emails(data['website'])
                if patterns:
                    for e in patterns:                           
                        self.instance.total_count += 1
                        self.instance.patterns.append(e)
                        self.instance.save()
                        q.put(e)
                        self.all.append([data['website'], e])



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

            with open('public/media/documents/' + self.instance.existing_path, 'w', encoding='utf-8') as csv_file:            
                write_file = csv.writer(csv_file, lineterminator='\n')
                write_file.writerows(self.all)
            self.instance.status = EmailListFetch.COMPLETED
            self.instance.save()

        except Exception as ex:
            print(ex)
            self.instance.description = str(ex)
            self.instance.status = EmailListFetch.ERROR
        self.instance.save()



class WebsiteListFetchHelperUpdated(object):

    def __init__(self, instance, *args, **kwargs):
        self.instance = instance

    def fetch_emails(self, starting_url):
        try:
            unprocessed_urls = deque([starting_url ])

            # set of already crawled urls for email
            processed_urls = set()

            # a set of fetched emails
            emails = set()

            # process urls one by one from unprocessed_url queue until queue is empty
            while len(unprocessed_urls):

                # move next url from the queue to the set of processed urls
                url = unprocessed_urls.popleft()
                processed_urls.add(url)

                # extract base url to resolve relative links
                parts = urlsplit(url)
                base_url = "{0.scheme}://{0.netloc}".format(parts)
                path = url[:url.rfind('/')+1] if '/' in parts.path else url

                try:
                    response = requests.get(url)
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching data from {url}: {e}")
                # except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
                    # ignore pages with errors and continue with next url
                    continue

                # extract all email addresses and add them into the resulting set
                # You may edit the regular expression as per your requirement
                new_emails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", response.text, re.I))
                emails.update(new_emails)
                # create a beutiful soup for the html document
                soup = BeautifulSoup(response.text, 'lxml')

                # Once this document is parsed and processed, now find and process all the anchors i.e. linked urls in this document
                for anchor in soup.find_all("a"):
                    # extract link url from the anchor
                    link = anchor.attrs["href"] if "href" in anchor.attrs else ''
                    # resolve relative links (starting with /)
                    if link.startswith('/'):
                        link = base_url + link
                    elif not link.startswith('http'):
                        link = path + link
                    # add the new url to the queue if it was not in unprocessed list nor in processed list yet
                    if not link in unprocessed_urls and not link in processed_urls and link.startswith(base_url) and 'cdn-cgi' not in link and 'tel:' not in link:
                        unprocessed_urls.append(link)
            
            return emails

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            return None
    
    def process_queue(self, url, sub_page=True):
        
        allowed_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.pdf', '.png', '.jpg', '../..','.ico', '.webp', 'linkedin:',
        '.jpeg', '.mp4', '.mkv', '.avi', '.flv', '.mov', '.wmv','cdn-cgi','tel:','mailto:', '#', '?', 'javascript:void']
        # a set of fetched emails

        # process urls one by one from unprocessed_url queue until queue is empty
        
        
        # extract base url to resolve relative links
        parts = urlsplit(url)
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        urlhtmlText = ''
        
        new_emails = set()
        new_urls = list()
        try:
            if not url.startswith('http'):
                url = 'https://' + url
            try:
                response = requests.get(url, timeout=5)  # Added timeout parameter
                response.raise_for_status()
            except SSLError as e:
                print(e)
                if url.startswith('http://'):
                    url = url.replace('http://','https://')
                if url.startswith('https://'):
                    url = url.replace('https://','http://')
                response = requests.get(url, timeout=5)
                response.raise_for_status()
            urlText = response.text
            soup = BeautifulSoup(urlText, 'html.parser')
            for span in soup.find_all('span', class_='__cf_email__'):
                encodedString = span['data-cfemail']
                int_r = int(encodedString[:2],16)
                email = ''.join([chr(int(encodedString[i:i+2], 16) ^ int_r) for i in range(2, len(encodedString), 2)])
                self.emails.add(email)
            urlhtmlText = soup.prettify()  
            email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
            extractedEmail = set(email_pattern.findall(urlhtmlText))
            
            new_emails = set([email.lower() for email in extractedEmail if not any(email.endswith(ext) and email not in self.emails for ext in allowed_extensions)])
            self.processed_urls.add(url)
            extra_emails = new_emails.difference(self.emails)
            if extra_emails:
                for e in extra_emails:
                    self.all.append([base_url, e])
                self.emails.update(extra_emails)
            # create a beutiful soup for the html document
            # Once this document is parsed and processed, now find and process all the anchors i.e. linked urls in this document
            # seturls = soup.find_all(filter_links)
            
            if sub_page:
                
                parts = urlsplit(url)
                base_url = "{0.scheme}://{0.netloc}".format(parts)
                path = url[:url.rfind('/')+1] if '/' in parts.path else url
                link_strainer = SoupStrainer('a', href=True)
                soup = BeautifulSoup(urlhtmlText, 'html.parser', parse_only=link_strainer)
                # sub_q = Queue()
                for anchor in soup.find_all('a'):

                    # extract link url from the anchor
                    if "href" in anchor.attrs:
                        link = anchor.attrs["href"]
                    else:
                        continue
                    # resolve relative links (starting with /)
                    if any(ext in link for ext in allowed_extensions):
                        continue
                    if link == '/':
                        continue
                    # if not link.startswith('http') and link != '/':
                    #     continue
                    if link == base_url:
                        continue
                    if link.startswith('/'):
                        link = base_url + link
                    elif not link.endswith('/') and not link.startswith('http'):
                        link = '/' + link
                    elif not link.startswith('http'):
                        link = path + link
                    if not link in self.processed_urls and link.startswith(base_url) and link not in new_urls:
                        
                        new_urls.append(link)
                new_urls = list(set(new_urls))
                new_urls_len = len(new_urls) if len(new_urls) > 0 else 1
                self.website_data[url] += new_urls_len
                self.instance.page_count += 1
                base_url_count = url + ' - (' +str(new_urls_len) + ')'
                self.instance.patterns = list(set(self.emails))
                self.instance.page_patterns.append(base_url_count)
                self.instance.save()
            
        except Exception as e:
            print(f"Error fetching data from {url}: {e}")
        return new_urls
        

    def get_email_result(self):
        self.emails = set()
        self.processed_urls = set()
        self.website_data = {}
        self.all = [['Website','Emails']]
        try:
            
            dataset = ast.literal_eval(self.instance.dataset)
            new_urls = set()
            self.instance.page_count = 0
            self.instance.total_count = 0
            self.instance.patterns = []
            self.instance.page_patterns = []
            for data in dataset:
                starting_url = data['website']
                self.website_data[data['website']] = 1
                if starting_url in self.processed_urls:
                    continue
                _new_urls = self.process_queue(starting_url)
                if _new_urls:
                    new_urls.update(_new_urls)
            # for urls_data  in new_urls:
                

            #     if urls_data in self.processed_urls:
            #         continue
            #     self.process_queue(urls_data, False)

                
            #         code, message = EmailCheckHelper().validate_email_smtp_dns(email)
            #         try:
            #             email_data = EmailSearch.objects.get(email_address=email)
            #         except EmailSearch.MultipleObjectsReturned:
            #             EmailSearch.objects.filter(email_address=email).delete()
            #             email_data = EmailSearch.objects.create(email_address=email)
            #         except EmailSearch.DoesNotExist:
            #             email_data = EmailSearch.objects.create(email_address=email)
            #         email_data.message = str(message)
            #         email_data.verified = False
            #         email_data.code = code
            #         if self.request.user.is_authenticated:
            #             email_data.added_by = self.request.user
            #         email_data.save()

                
                

        except Exception as ex:
            print(ex)
        websites_from_dataset1 = [item['website'] for item in dataset]

        # Create a mapping of website to index position
        self.instance.page_patterns = []
        website_to_index_mapping = {website: index for index, website in enumerate(websites_from_dataset1)}
        self.instance.page_count = len(self.website_data.items()) 
        for column, column_data in self.website_data.items():
            base_url_count = column + '- (' +str(column_data) + ')'
            self.instance.page_patterns.append(base_url_count)
        self.all = [self.all[0]] + sorted(self.all[1:], key=lambda x: website_to_index_mapping.get(x[0], website_to_index_mapping.get(x[0] + '/', float('inf')))) 
        with open('public/media/documents/' + self.instance.existing_path, 'w', encoding='utf-8') as csv_file:            
            write_file = csv.writer(csv_file, lineterminator='\n')
            write_file.writerows(self.all)
        self.instance.total_count = len(self.emails)
        self.instance.patterns = list(set(self.emails))
        self.instance.status = EmailListFetch.COMPLETED
        self.instance.save() 