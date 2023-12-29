'''
commands to create default branding for OS Admin
'''

# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand

from app.models import People, Company, ManagementLevel, Revenue, Employee
import itertools


class Command(BaseCommand):
    ''' Command '''
    help = 'Update Level revenue employee'


    def handle(self, *args, **options):
        self.stdout.write("================ Updation Starts ===============")
        data_queryset = People.objects.all()
        for data in data_queryset:
            management_level2, created = ManagementLevel.objects.get_or_create(title=data.management_level2)
            data.management_level = management_level2
            data.save()
        queryset = Company.objects.all()
        for data in queryset:
            revenue2, created = Revenue.objects.get_or_create(title=data.revenue2)
            data.revenue = revenue2
            employees2, created = Employee.objects.get_or_create(title=data.employees2)
            data.employees = employees2
            data.save()
        
        self.stdout.write("=================== Updation ended ====================")

    
