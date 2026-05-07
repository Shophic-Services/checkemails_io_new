
import re, time
import smtplib
import dns.resolver
from tools.models import DataSourceItem, DataSourceJob, EmailData, DataSourceJob

import re
import requests
import requests.exceptions
from bs4 import BeautifulSoup
import urllib.parse
import subprocess
import time
import sys
from base64 import b64decode

import socket
import random
import string
import time
import psutil
import logging
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from tools import constants
ZYTE_API_KEY = "fd1cdfe3ed9145af87d90af969f716eb"

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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

EMAIL_REGEX = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

def is_valid_syntax(email: str) -> bool:
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

class EmailCheckHelper(object):
    def __init__(self, request=None, **kwargs):
        self.request = request
        self.user_id = kwargs.get('user_id', None)
        self.FREE_EMAIL_PROVIDERS = {
            "gmail.com",
            "googlemail.com",
            "yahoo.com",
            "yahoo.co.in",
            "yahoo.co.uk",
            "yahoo.ca",
            "yahoo.fr",
            "yahoo.co.jp",
            "hotmail.com",
            "hotmail.co.uk",
            "hotmail.fr",
            "hotmail.de",
            "hotmail.com.br",
            "outlook.com",
            "outlook.in",
            "outlook.co.uk",
            "live.com",
            "msn.com",
            "icloud.com",
            "me.com",
            "mac.com",
            "aol.com",

            "protonmail.com",
            "proton.me",
            "tutanota.com",
            "tuta.io",
            "hushmail.com",
            "mailfence.com",
            "countermail.com",

            "zoho.com",
            "mail.com",
            "gmx.com",
            "gmx.net",

            "yandex.com",
            "yandex.ru",
            "yandex.ua",
            "yandex.kz",
            "yandex.by",
            "mail.ru",
            "bk.ru",
            "inbox.ru",
            "list.ru",
            "rambler.ru",
            "ukr.net",

            "rediffmail.com",
            "rediff.com",
            "sify.com",
            "in.com",

            "qq.com",
            "163.com",
            "126.com",
            "yeah.net",
            "sina.com",
            "sina.cn",
            "sohu.com",
            "foxmail.com",
            "aliyun.com",

            "ezweb.ne.jp",
            "docomo.ne.jp",
            "softbank.ne.jp",
            "nifty.com",

            "naver.com",
            "daum.net",
            "hanmail.net",

            "orange.fr",
            "wanadoo.fr",
            "laposte.net",
            "free.fr",
            "sfr.fr",

            "web.de",
            "gmx.de",
            "t-online.de",
            "freenet.de",

            "btinternet.com",
            "virginmedia.com",
            "talktalk.net",
            "sky.com",

            "terra.es",
            "telefonica.net",
            "libero.it",
            "alice.it",
            "tiscali.it",

            "uol.com.br",
            "bol.com.br",
            "ig.com.br",
            "terra.com.br",

            "seznam.cz",
            "centrum.cz",
            "wp.pl",
            "o2.pl",
            "interia.pl",

            "inbox.com",
            "fastmail.com",
            "rocketmail.com",
            "aim.com",
        }

        self.disposable_domains = ["mailinator.com", "guerrillamail.com", "10minutemail.com", "temp-mail.org",
                              "emailondeck.com", "throwawaymail.com", "yopmail.com", "mohmal.com",
                              "burnermail.io", "inboxkitten.com", "fakemail.net", "emailfake.com",
                              "maildrop.cc", "getnada.com"]

    def validate_email(self, email, action=None):
        

        # Check cached results
        try:
            email_data = EmailData.objects.get(email=email)
            if (email_data.modify_date and (email_data.modify_date >= (timezone.now() - timedelta(days=30)))) or email_data.email_type == EmailData.SCRAPED:
                time.sleep(random.uniform(2, 3))
                errors = ''
                # result = (email_data.email, email_data.role_based, email_data.has_domain_mx, email_data.has_spf, email_data.has_dmarc, email_data.status, email_data.quality, email_data.email_result, email_data.valid, email_data.email_source, email_data.catch_all, email_data.email_type, email_data.code, email_data.message, errors, email_data.retry_later, email_data.permanent_failure, email_data.needs_manual_review, email_data.has_smtp)
               
                # return result
        except EmailData.DoesNotExist:
            email_data = None

        # Basic syntax check
        # if not is_valid_syntax(email):
        #     result["check"]["type"]["code"] = EmailData.SYNTAX_ERROR 
            
        #     return result
        domain = email.split('@')[1].lower()

        # Role-based check
        is_role_based = self.check_role_based(email)
        has_domain_mx = False
        has_spf = False
        has_dmarc = False
        status = EmailData.UNKNOWN
        quality = EmailData.UNKNOWN

        email_result = 'Do Not Send - Disposable'
        valid = True
        email_source = EmailData.SMTP
        catch_all = False
        email_type = EmailData.UNKNOWN
        code =  204
        message = ''
        errors = ''
        retry_later = False
        permanent_failure = False
        needs_manual_review = False
        has_smtp = False

        

        # import pdb;pdb.set_trace()
        # whois_info = whois.whois(domain)
        # MX check
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_hosts = [str(r.exchange).strip('.') for r in sorted(mx_records, key=lambda r: r.preference)]
            mx_hosts = [host for host in mx_hosts if host.strip()]
            if mx_hosts:
                has_domain_mx = True
        except Exception as e:
            logger.debug(f"MX check failed for {domain}: {e}")
            pass

        # SPF check
        try:
            answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT", lifetime=3)
            for r in answers:
                for txt in r.strings:
                    if txt.decode().lower().startswith("v=dmarc1"):
                        has_spf = True
        except Exception as e:
            logger.debug(f"SPF check failed for {domain}: {e}")
            pass
        
        #DMARC check
        try:
            answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT", lifetime=3)
            for r in answers:
                for txt in r.strings:
                    if txt.decode().lower().startswith("v=dmarc1"):
                        has_dmarc = True
        except Exception:
            pass


        # Disposable check
        if domain in self.disposable_domains:
            status = EmailData.DISPOSABLE
            quality = EmailData.RISKY
            email_result = 'Do Not Send - Disposable'
            valid = False
            email_source = EmailData.SMTP
            catch_all = True
            email_type = EmailData.DISPOSABLE
            code = 999
            message = str('Disposable domain')
            errors = ''
            retry_later = False
            permanent_failure = False
            needs_manual_review = False
            
        else:
            result = (email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp)
            # SMTP validation
            result = self.update_response_validate(email, result)


            email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp = result
        
        # Save to EmailData
        email_data, _ = EmailData.objects.get_or_create(email=email)
        
        email_data.has_domain_mx = has_domain_mx
        email_data.has_spf = has_spf
        email_data.has_dmarc = has_dmarc
        email_data.professional = True if domain not in self.FREE_EMAIL_PROVIDERS and ( has_dmarc or has_spf) else False
        email_data.professional = False if domain in self.disposable_domains else email_data.professional
        email_data.retry_later = retry_later
        email_data.valid = valid
        email_data.message = message
        email_data.catch_all = catch_all 
        email_data.role_based = is_role_based
        email_data.disposable = status == EmailData.DISPOSABLE
        email_data.status = status
        email_data.quality = quality
        email_data.email_source = email_source
        email_data.email_type = email_type
        email_data.code = code
        email_data.needs_manual_review = needs_manual_review
        email_data.permanent_failure = permanent_failure
        email_data.email_result = email_result
        
        if self.request:
            email_data.added_by = self.request.user
        if self.user_id and not self.request:
            email_data.added_by_id = self.user_id
        email_data.save()

        
        result = (email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp)
        return result
    
    def check_role_based(self, email: str) -> tuple[bool, str]:
        """Check if email is role-based (info@, admin@, etc.)"""
        local_part = email.split('@')[0].lower()
        role_accounts = {
            'admin', 'administrator', 'info', 'contact', 'support', 'help',
            'sales', 'marketing', 'noreply', 'no-reply', 'postmaster',
            'webmaster', 'hostmaster', 'root', 'mailer-daemon'
        }
        
        if local_part in role_accounts:
            return True
        return False

    def get_system_ipv6_list(self):
        """Return all system-assigned IPv6 addresses (excluding loopback and link-local)."""
        ipv6_list = []
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET6:
                        ip = addr.address.split('%')[0]
                        if not ip.startswith("fe80") and ip != "::1":
                            ipv6_list.append(ip)
        except Exception as e:
            logger.error(f"Failed to get IPv6 addresses: {e}")
        logger.debug(f"IPv6 addresses found: {ipv6_list}")
        return ipv6_list

    def supports_ipv6(self, host):
        """Check if host supports IPv6 via AAAA records."""
        try:
            addr_info = socket.getaddrinfo(host, None, socket.AF_INET6)
            if addr_info:
                logger.debug(f"Host {host} supports IPv6: {[info[4][0] for info in addr_info]}")
                return True
        except socket.gaierror as e:
            logger.debug(f"Host {host} does not support IPv6: {e}")
        return False

    def resolve_mx_ip(self, mx_host):
        """Resolve MX host to both IPv6 and IPv4 addresses."""
        ip_addresses = set()

        ip_addresses.update(self.get_system_ipv6_list())
        # Try IPv6 first
        try:
            addr_info = socket.getaddrinfo(mx_host, 25, socket.AF_INET6, socket.SOCK_STREAM)
            ipv6_addresses = [info[4][0] for info in addr_info]
            ip_addresses.update(ipv6_addresses)
            logger.debug(f"Resolved {mx_host} to IPv6: {ipv6_addresses}")
        except socket.gaierror as e:
            logger.debug(f"No IPv6 for {mx_host}: {e}")

        # Then IPv4
        try:
            addr_info = socket.getaddrinfo(mx_host, 25, socket.AF_INET, socket.SOCK_STREAM)
            ipv4_addresses = [info[4][0] for info in addr_info]
            ip_addresses.update(ipv4_addresses)
            logger.debug(f"Resolved {mx_host} to IPv4: {ipv4_addresses}")
        except socket.gaierror as e:
            logger.error(f"Failed to resolve {mx_host} to IPv4: {e}")

        return list(ip_addresses)

    def validate_email_smtp_dns(self, email, result, max_retries=1):

        email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp = result
        base_sender_emails = [
            "sandysoorma407@gmail.com", "reachalex009@gmail.com", "reachalex332@gmail.com",
            "alexatreach@gmail.com", "alexuserus002@gmail.com", "reachalex333@gmail.com",
            "reachalex078@gmail.com", "reachalex10@gmail.com"
        ]
        base_sender = random.choice(base_sender_emails)
        username, domain = base_sender.split('@')
        random_number = random.randint(1, 100)
        sender_email = f"{username}+{random_number}@{domain}"
        email_account, email_domain = email.split('@')


        # Resolve all MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_hosts = [str(r.exchange).strip('.') for r in sorted(mx_records, key=lambda r: r.preference)]
            mx_hosts = [host for host in mx_hosts if host.strip()]
            logger.debug(f"MX hosts for {domain}: {mx_hosts}")
        except Exception as e:
            logger.error(f"MX lookup failed for {domain}: {e}")
            return 500, str(e), result
        for mx_host in mx_hosts:

            # Resolve MX host to IP addresses
            ip_addresses = self.resolve_mx_ip(mx_host)
            logger.debug(f"Resolved IP addresses for {mx_host}: {ip_addresses}")
            attempt = 0
            # for attempt in range(max_retries):
            for ip in ip_addresses:
                port = 25
                # server = None
                try:
                    server = smtplib.SMTP(timeout=10)
                    if ip:
                        logger.debug(f"Attempting connection to {mx_host} ({ip}:{port})")
                        server._host = mx_host
                        server.sock = socket.create_connection(
                            (mx_host, 25),
                            source_address=(ip, 0),   # pick source IPv6
                            timeout=10
                        )
                        # server.sock = socket.create_connection(
                        #     (ip, port), timeout=30
                        # )
                        server.file = server.sock.makefile("rb")
                    else:
                        logger.debug(f"Attempting direct connection to {mx_host}:{port}")
                        server.connect(mx_host, port)

                    # Enable verbose SMTP logging
                    # server.set_debuglevel(1)

                    # EHLO with your domain (replace with your actual domain)
                    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                    server.ehlo(name="valid-" + random_string)

                    # Enable STARTTLS if available
                    # if server.has_extn('STARTTLS'):
                    #     logger.debug(f"STARTTLS supported by {mx_host}:{port}, enabling")
                    #     server.starttls()
                    #     server.ehlo(f"{ehlo_host}-{random_string}")

                    # Real email test
                    server.mail(sender_email)
                    code, message = server.rcpt(email)
                    if code == 250:
                        code, message = server.rcpt(email)
                    logger.debug(f"Real RCPT {email}: Code={code}, Message={message.decode() if isinstance(message, bytes) else message}")

                    real_valid = code in [250, 251]
                    if real_valid:
                        # Reset session
                        try:
                            server.rset()
                        except Exception as e:
                            logger.debug(f"RSET failed: {e}")
                            server.quit()
                            server = smtplib.SMTP(timeout=10)
                            # server.set_debuglevel(1)
                            if ip:
                                server._host = mx_host
                                server.sock = socket.create_connection(
                                (mx_host, 25),
                                    source_address=(ip, 0),   # pick source IPv6
                                    timeout=10
                                )
                                server.file = server.sock.makefile("rb")
                            else:
                                server.connect(mx_host, port)
                        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                        server.ehlo(name="verify-" + random_string)
                        # if server.has_extn('STARTTLS'):
                        #     server.starttls()
                        #     server.ehlo(f"{ehlo_host}-{random_string}")
                    
                        # Fake email test for catch-all
                        base_sender = random.choice(base_sender_emails)
                        username, domain = base_sender.split('@')
                        random_number = random.randint(1, 100)
                        sender_email = f"{username}+{random_number}@{domain}"
                        server.mail(sender_email)  # Re-issue MAIL FROM
                        random_user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                        fake_email = f"{random_user}@{email_domain}"
                        code_fake, message_fake = server.rcpt(fake_email)
                        if code_fake == 250:
                            code_fake, message_fake = server.rcpt(fake_email)
                        logger.debug(f"Fake RCPT {fake_email}: Code={code_fake}, Message={message_fake.decode() if isinstance(message_fake, bytes) else message_fake}")

                        server.quit()
                    
                        catch_all = code_fake in [250, 251]
                        
                    email_source = EmailData.SMTP
                    has_smtp = True
                    if code in [250, 251]:
                        valid = True
                        status = EmailData.VALID
                        quality = EmailData.VALID
                        email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL

                    elif code == 550:
                        valid = False
                        status = EmailData.INVALID
                        quality = EmailData.INVALID
                        email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
                    elif code in [551, 552, 553, 554]:
                        permanent_failure = True
                        status = EmailData.INVALID
                        quality = EmailData.INVALID
                        email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
                    elif str(code).startswith('421') or code in [450, 451, 452]:
                        retry_later = True
                        status = EmailData.RISKY
                        quality = EmailData.RISKY
                        email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
                    else:
                        needs_manual_review = True
                        status = EmailData.UNKNOWN
                        email_type = EmailData.UNKNOWN
                        quality = EmailData.UNKNOWN
                    if catch_all:
                        needs_manual_review = False
                        status = EmailData.RISKY
                        quality = EmailData.RISKY
                        status = EmailData.RISKY
                        email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
                    

                    result = (email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp)
                    return code, message, result

                except Exception as e:
                    error_msg = str(e).lower()
                    logger.error(f"Attempt {attempt+1}, IP {ip or 'direct'}, MX {mx_host}:{port}: {e}")
                    # Detect blocklist or connection errors
                    if '554' in error_msg or '421' in error_msg or 'too many errors' in error_msg:
                        logger.debug(f"Blocklist or connection error detected for {mx_host}:{port}, skipping retries")
                        break  # Skip to next MX host or fallback
                    if attempt < max_retries - 1 and ('421' in error_msg or '450' in error_msg):
                        logger.debug("Greylisting detected, retrying after 30s")
                        time.sleep(30)
                    continue
            if '554' in error_msg or '421' in error_msg or 'too many errors' in error_msg:
                break  # Break IP loop
            # if '554' in error_msg or '421' in error_msg or 'too many errors' in error_msg:
            #     break  # Break MX host loop

        logger.error("All SMTP attempts failed across all MX hosts")
        needs_manual_review = True
        result = (email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp)
        return 500, "All SMTP attempts failed", result

    def get_dynamic_headers(self):
        
        USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1",
        ]

        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8", "fr-FR,fr;q=0.7"]),
            "Connection": "keep-alive"
        }

    def extract_emails_from_domain(self, domain):
        """Extract emails from the domain's website by dynamically discovering relevant pages."""
        emails = set()
        base_pages = ['', '/contact', '/privacy-policy','/career', '/about', '/team', '/info', '/support']
        priority_keywords = ['contact', 'privacy', 'career',  'about', 'team', 'support', 'info']
        max_pages = 10
        visited = set()
        to_visit = ['']
        crawled_pages = 0
        
        if domain in self.FREE_EMAIL_PROVIDERS:
            return []

        # Fetch homepage to discover links
        try:
            resp = requests.post(
                    "https://api.zyte.com/v1/extract",
                    auth=(ZYTE_API_KEY, ''),
                    json={
                        "url": f"https://{domain}",
                        "httpResponseBody": True,
                        "followRedirect": True,
                    },
                )
            if resp.status_code == 200:
                http_response_body: bytes = b64decode(
                resp.json()["httpResponseBody"])
                html = http_response_body.decode()
                soup = BeautifulSoup(html, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    href = urljoin(f"https://{domain}", href)
                    if domain in href and href not in visited and crawled_pages < max_pages:
                        path = href.replace(f"https://{domain}", '').split('?')[0].split('#')[0]
                        if path and not path.startswith('/'):
                            path = f"/{path}"
                        if path not in to_visit and any(keyword in path.lower() for keyword in priority_keywords):
                            to_visit.append(path)
        except Exception as e:
            pass
            logger.debug(f"Failed to fetch homepage https://{domain}: {e}")

        # Combine base_pages with discovered pages
        to_visit = list(set(to_visit + base_pages))[:max_pages]
        for path in to_visit:
            for protocol in ['https', 'http']:
                url = f"{protocol}://{domain}{path}"
                if url in visited or crawled_pages >= max_pages:
                    continue
                try:
                    resp = requests.post(
                        "https://api.zyte.com/v1/extract",
                        auth=(ZYTE_API_KEY, ''),
                        json={
                            "url": f"{url}",
                            "httpResponseBody": True,
                            "followRedirect": True,
                        },
                    )
                    if resp.status_code == 200:
                        http_response_body: bytes = b64decode(
                        resp.json()["httpResponseBody"])
                        html = http_response_body.decode()
                        found = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', html)
                        emails.update(found)
                        crawled_pages += 1
                        visited.add(url)
                        # Extract additional links
                        # soup = BeautifulSoup(html, 'html.parser')
                        # links = soup.find_all('a', href=True)
                        # for link in links:
                        #     href = link['href']
                        #     href = urljoin(f"https://{domain}", href)
                        #     if domain in href and href not in visited and crawled_pages < max_pages:
                        #         path = href.replace(f"https://{domain}", '').split('?')[0].split('#')[0]
                        #         if path and not path.startswith('/'):
                        #             path = f"/{path}"
                        #         if path not in to_visit and any(keyword in path.lower() for keyword in priority_keywords):
                        #             to_visit.append(path)
                except Exception as e:
                    pass
                    logger.debug(f"Failed to fetch {url}: {e}")
            time.sleep(random.uniform(1, 3))
        logger.debug(f"Extracted emails from {domain}: {list(emails)}")
        filtered_emails = list(filter(lambda e: domain in e, emails))
        return filtered_emails

    def update_response_validate(self, email, result):
        email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp = result

        if has_domain_mx:
            code, message, result = self.validate_email_smtp_dns(email, result)
            email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp = result
            verified = code in [250, 251]
        else:
            code, message = 500, 'MX check failed'
            
        if has_domain_mx and not verified:
            retry_later = False
            verified = False
            permanent_failure = False
            needs_manual_review = False
            has_smtp = False
            email_account, email_domain = email.split('@')
            
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            server_name="verify-" + random_string
            code, message, result =  self.run_probe('swaks', email, result=result, helo=server_name)

            email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp = result
            
            if code == 500:
                verified = False
                
                is_role_based = self.check_role_based(email)
                has_domain_mx = False
                has_spf = False
                has_dmarc = False
                status = EmailData.UNKNOWN
                quality = EmailData.UNKNOWN

                email_result = 'Do Not Send - Disposable'
                valid = True
                email_source = EmailData.SMTP
                catch_all = False
                email_type = EmailData.UNKNOWN
                code =  204
                message = ''
                errors = ''
                retry_later = False
                permanent_failure = False
                needs_manual_review = False
                has_smtp = False
                found_emails = self.extract_emails_from_domain(email_domain)
                if email.lower() in [e.lower() for e in found_emails]:
                    verified = True
                    code = 250
                    message = "Recipient OK"
                    email_source = EmailData.SCRAPED
                    valid = True
                    has_domain_mx = True
                    has_spf = True
                    has_dmarc = True
                    status = EmailData.RISKY
                    quality = EmailData.RISKY
                    email_type = EmailData.PROFESSIONAL if email_domain not in self.FREE_EMAIL_PROVIDERS else EmailData.WEBMAIL
                else:
                    profiles = self.find_linkedin_profile(email)
                    if profiles:
                        verified = True
                        code = 111
                        message = "Recipient OK"
                        email_source = EmailData.SOCIAL
                        valid = True
                        status = EmailData.RISKY
                        quality = EmailData.RISKY
                        needs_manual_review = True
                        email_type = EmailData.PROFESSIONAL if email_domain not in self.FREE_EMAIL_PROVIDERS else EmailData.WEBMAIL
                if found_emails:
                    for found_email in found_emails:
                        new_email_data, created = EmailData.objects.get_or_create(email=found_email)
                        if created:
                            new_email_data.has_domain_mx = True
                            new_email_data.has_dmarc = True
                            new_email_data.professional = True if email_domain not in self.FREE_EMAIL_PROVIDERS else False
                            new_email_data.professional = False if email_domain in self.disposable_domains else new_email_data.professional
                            new_email_data.role_based = self.check_role_based(found_email)
                            new_email_data.status = EmailData.VALID
                            new_email_data.quality = EmailData.VALID
                            new_email_data.email_type = EmailData.PROFESSIONAL if new_email_data.professional  else EmailData.WEBMAIL
                            new_email_data.has_spf = True
                            new_email_data.valid = True
                            new_email_data.email_source = EmailData.SCRAPED
                            new_email_data.code = 250
                            new_email_data.catch_all = False
                            new_email_data.has_smtp = False
                            new_email_data.needs_manual_review = False
                            new_email_data.permanent_failure = False
                            if self.request:
                                new_email_data.added_by = self.request.user
                            if self.user_id and not self.request:
                                new_email_data.added_by_id = self.user_id
                            new_email_data.save()     
        email_result = 'Do Not Send - Unable to Confirm'
        if valid:
            email_result = 'Safe to Send - Deliverable'
        else:
            email_result = 'Do Not Send - Undeliverable'
        if status == EmailData.RISKY:
            email_result = 'Risky - Use with Caution'
        if status == EmailData.DISPOSABLE:
            email_result = 'Do Not Send - Disposable'
        if status == EmailData.UNKNOWN:
            email_result = 'Do Not Send - Unable to Confirm'

        result = (email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp)
        return result

    def validate_email_bulk(self, email_list):
        response = []
        for email in email_list:
            result = self.validate_email(email)
            result.pop('message', None)
            result.pop('errors', None)
            response.append(result)
            time.sleep(random.uniform(2, 3))
        return response
        
    def resolve_mx(self, domain):
        """Resolve MX using dig."""
        try:
            result = subprocess.run(['dig', '+short', 'MX', domain], capture_output=True, text=True)
            if result.returncode == 0:
                mx = result.stdout.strip().split('\n')[0].split()[-1]  # Last field of first line
                return mx.rstrip('.')
        except:
            pass
        return None

    def run_probe(self, tool, email, result, helo='verify'):

        email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp = result
        domain = email.split('@')[1]
        mx = self.resolve_mx(domain)
        if not mx:
            return 500, str('No MX for {email}'), result
        base_sender_emails = [
            "sandysoorma407@gmail.com", "reachalex009@gmail.com", "reachalex332@gmail.com",
            "alexatreach@gmail.com", "alexuserus002@gmail.com", "reachalex333@gmail.com",
            "reachalex078@gmail.com", "reachalex10@gmail.com"
        ]
        base_sender = random.choice(base_sender_emails)
        username, domain = base_sender.split('@')
        random_number = random.randint(1, 100)
        sender_email = f"{username}+{random_number}@{domain}"
        cmd = ['swaks', '--to', email,'--from', sender_email, '--server', f'{mx}:25', '--helo', helo, '--quit-after', 'RCPT']
        subprocessresult = subprocess.run(cmd, capture_output=True, text=False)  # Keep as bytes for decode
    
        # Decode stdout (handle empty)
        if subprocessresult.stdout:
            stdout = subprocessresult.stdout
        else:
            stdout = ''
        
        code = self.get_rcpt_code(stdout)
        # Determine message and return
        if code == 250 or code in [450, 451, 452]:
            msg = f'✓ Recipient OK - ' + tool
            message = msg
            # Fake email test for catch-all
            base_sender = random.choice(base_sender_emails)
            username, domain = email.split('@')
            random_number = random.randint(1, 100)
            sender_email = f"{username}+{random_number}@{domain}"
            random_user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            fake_email = f"{random_user}@{domain}"
            cmd = ['swaks', '--to', fake_email,'--from', sender_email, '--server', f'{mx}:25', '--helo', helo, '--quit-after', 'RCPT']
            subprocessresult = subprocess.run(cmd, capture_output=True, text=False)  # Keep as bytes for decode

            # Decode stdout (handle empty)
            if subprocessresult.stdout:
                stdout = subprocessresult.stdout
            else:
                stdout = ''
            code_fake = self.get_rcpt_code(stdout)
            catch_all = code_fake in [250, 251]
        else:
            msg = f"⚠️ Recipient not accepted – SMTP server returned an error - " + tool
            message = msg
        email_source = EmailData.SWAKS
        if code in [250, 251]:
            valid = True
            status = EmailData.VALID
            quality = EmailData.VALID
            email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL

        elif code == 550:
            valid = False
            status = EmailData.INVALID
            quality = EmailData.INVALID
            email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
        elif code in [551, 552, 553, 554]:
            permanent_failure = True
            status = EmailData.INVALID
            quality = EmailData.INVALID
            email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
        elif str(code).startswith('421') or code in [450, 451, 452]:
            retry_later = True
            status = EmailData.RISKY
            quality = EmailData.RISKY
            email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
        else:
            needs_manual_review = True
            status = EmailData.UNKNOWN
            email_type = EmailData.UNKNOWN
            quality = EmailData.UNKNOWN
        if catch_all:
            needs_manual_review = False
            status = EmailData.RISKY
            quality = EmailData.RISKY
            status = EmailData.RISKY
            email_type = EmailData.PROFESSIONAL if domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf) else EmailData.WEBMAIL
        
        result = (email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp)
        return code, msg, result
        
    def get_rcpt_code(self, stdout_bytes):
        """
        Parse Swaks stdout to extract the SMTP response code for the RCPT TO command.
        
        Special handling:
        - Spamhaus / IP reputation blocks → return 500 (temporary)
        - Other common blocks (Barracuda, SpamCop, policy, greylisting) → 450
        - Hard rejections (user unknown, etc.) → 550
        - Parsing failure → 500
        """
        if not stdout_bytes:
            print("[DEBUG] Empty stdout → returning 500")
            return 500

        try:
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"[ERROR] Decode failed: {e} → returning 500")
            return 500

        lines = stdout.splitlines()
        in_rcpt_block = False
        response_lines = []

        for line in lines:
            stripped = line.strip()

            # Start of RCPT command block
            if 'RCPT TO' in line:
                in_rcpt_block = True
                response_lines = []
                continue

            if in_rcpt_block:
                # End of RCPT response block
                if stripped.startswith('-> ') or stripped.startswith('=== '):
                    break

                # Capture any line that looks like a server response
                if stripped.startswith(('<** ', '<- ')) or '5' in stripped[:4] or '4' in stripped[:4]:
                    response_lines.append(stripped)

        if not response_lines:
            print("[DEBUG] No RCPT response lines found → returning 500")
            return 500

        # Join for easier pattern matching
        full_response = ' '.join(response_lines).lower()

        # ────────────────────────────────────────────────
        #  Detect known block / defer patterns → 450
        # ────────────────────────────────────────────────
        block_keywords_500 = [
            # Spamhaus family
            'spamhaus', 'zen.spamhaus.org', 'pbl.spamhaus.org', 'xbl.spamhaus.org',
            # Microsoft / Outlook common phrases
            'service unavailable', 'client host', 'blocked using',
            # Other major RBLs
            'barracudacentral', 'spamcop.net', 'uceprotect', 'sorbs.net',
            # Policy / reputation
            'policy violation', 'not authorized', 'low reputation',
            'access denied', 'bad reputation',
            # Greylisting / temp defer
            'greylisted', 'try again', 'temporary failure', 'defer',
        ]

        for kw in block_keywords_500:
            if kw in full_response:
                print(f"[INFO] Detected block pattern '{kw}' → returning 450 (temporary)")
                return 500

        # ────────────────────────────────────────────────
        #  Try to extract the numeric SMTP code
        # ────────────────────────────────────────────────
        for line in response_lines:
            # Look for lines like: <- 550 5.7.1 ... or <** 550 ...
            parts = line.split()
            if len(parts) >= 2:
                code_str = parts[1] if parts[0].startswith('<') else parts[0]
                if code_str.isdigit() and len(code_str) == 3:
                    try:
                        code = int(code_str)
                        if 200 <= code <= 599:
                            print(f"[DEBUG] Parsed SMTP code: {code}")
                            # Optional: treat 421/450/451 as defer even if not keyword-matched
                            if 420 <= code <= 459:
                                return 450
                            return code
                    except ValueError:
                        pass

        # Fallback if we couldn't parse anything meaningful
        print(f"[WARNING] No parsable SMTP code found in response:\n{full_response[:200]}...")
        return 500
    
    def is_name_match(self, email_local, snippet_name):
        """
        Returns True if email_local matches snippet_name approximately.
        """
        email_local = email_local.lower()
        snippet_name = snippet_name.lower()
        
        # Compare email local-part with snippet name using similarity ratio
        person_name = re.match(r"([a-z]+ [a-z]+)", snippet_name, re.IGNORECASE)
        if person_name:
            person_name = person_name.group(1)
            ratio = SequenceMatcher(None, email_local, person_name).ratio()
            return ratio > 0.6
        return False

    def find_linkedin_profile(self, email):
        try:
            # Extract domain or name part from email
            local_part, domain = email.split("@")
            
            company = domain.split(".")[0]
            query = f'site:linkedin.com/in {local_part} {company} {email}'
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            logger.debug(f"Fetching LinkedIn profiles for {email} with URL: {url}")
            resp = requests.post(
                "https://api.zyte.com/v1/extract",
                auth=(ZYTE_API_KEY, ""),
                json={
                    "url": url,
                    "browserHtml": True,
                },
            )
            resp.raise_for_status()  
            browser_html: str = resp.json()["browserHtml"]          
            soup = BeautifulSoup(browser_html, "html.parser")
            linkedin_urls = []
            url_snippet_pairs = []  # To store (url, snippet) pairs
            
            # Parse Google results
            for div_tag in soup.find_all(attrs={"data-rpos": True}):
                # Get div text (snippet or context)
                div_text = div_tag.get_text(strip=True).lower()
                # Find all <a> tags inside this div
                for a_tag in div_tag.find_all("a"):
                    href = a_tag.get("href")
                    if href and "linkedin.com/in/" in href:
                        # Clean Google redirect URL if needed
                        if href.startswith("/url?q="):
                            href = href.split("/url?q=")[1].split("&")[0]
                        
                        # Append tuple (linkedin URL, snippet/div text)
                        url_snippet_pairs.append((href, div_text))
            for url, snippet in url_snippet_pairs:
                
                div_text = "".join(snippet.split()).replace("\xa0", "")
                if self.is_name_match(local_part, snippet.lower()) and company.lower().replace(" ", "") in div_text:
                    linkedin_urls.append(url)
            # Remove duplicates and log
            linkedin_urls = list(set(linkedin_urls))
            logger.debug(f"Found {len(linkedin_urls)} LinkedIn profiles for {email}: {linkedin_urls}")
            if len(linkedin_urls) == 0:
                local_part, domain = email.split("@")
                
                # Build a DuckDuckGo search query
                company = domain.split(".")[0]
                query = f'site:linkedin.com/in {local_part} {company}'
                url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                resp = requests.get(url, headers=self.get_dynamic_headers(), timeout=15)
                resp.raise_for_status()       
                soup = BeautifulSoup(resp.text, "html.parser")
                linkedin_urls = []
                url_snippet_pairs = []  # To store (url, snippet) pairs
                
                # Parse DuckDuckGo results
                for a_tag in soup.find_all("a", class_=["result__url", "result__a"]):
                    href = a_tag.get("href")
                    if href and "www.linkedin.com/in/" in href:
                        url = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                        if url.startswith("https://www.linkedin.com/in/"):
                            # Find corresponding snippet
                            next_tag = a_tag.find_next(class_="result__snippet")
                            snippet = next_tag.get_text() if next_tag else ""
                            url_snippet_pairs.append((url, snippet))
                    elif href is None and a_tag.get_text().startswith("www.linkedin.com/in/"):
                        url = f"https://{a_tag.get_text()}"
                        if url.startswith("https://www.linkedin.com/in/"):
                            next_tag = a_tag.find_next(class_="result__snippet")
                            snippet = next_tag.get_text() if next_tag else ""
                            url_snippet_pairs.append((url, snippet))
                    elif href and "linkedin.com/in/" in href:
                        # Clean Google redirect URL if needed
                        if href.startswith("/url?q="):
                            href = href.split("/url?q=")[1].split("&")[0]
                        
                        div_text = a_tag.get_text(strip=True).lower()
                        # Append tuple (linkedin URL, snippet/div text)
                        url_snippet_pairs.append((href, div_text))
                for url, snippet in url_snippet_pairs:
                    div_text = "".join(snippet.split()).replace("\xa0", "")
                    if self.is_name_match(local_part, snippet.lower()) and company.lower().replace(" ", "") in div_text:
                        linkedin_urls.append(url)
                
                # Remove duplicates and log
                linkedin_urls = list(set(linkedin_urls))
                logger.debug(f"Found {len(linkedin_urls)} LinkedIn profiles for {email}: {linkedin_urls}")
            return linkedin_urls

        except Exception as e:
            logger.error(f"Failed to find LinkedIn profile for {email}: {e}") 
            return []