'''
commands to create default branding for OS Admin
'''

# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand

import itertools


class Command(BaseCommand):
    ''' Command '''
    help = 'Create OS branding'


    def handle(self, *args, **options):
        from validate_email import validate_email
        testEmail = input('Email: ')
        import smtplib
        import dns.resolver
        server = smtplib.SMTP()
        splitAddress = testEmail.split('@')
        domain = str(splitAddress[1])
        print('Domain:', domain)
        fromAddress = testEmail
        # MX record lookup
        records = dns.resolver.resolve(domain, 'MX')
        mxRecord = records[0].exchange
        mxRecord = str(mxRecord)
        server.connect(mxRecord)
        server.helo(server.local_hostname) ### server.local_hostname(Get local server hostname)
        server.mail(fromAddress)
        code, message = server.rcpt(str(testEmail))
        server.quit()

        print("code:",code)
        print("message:",message)
        validate_email(email_address=testEmail,check_format=True,check_blacklist=True,check_dns=True,dns_timeout=10,check_smtp=True,smtp_timeout=10,smtp_skip_tls=False,smtp_tls_context=None,smtp_debug=True,)

    
