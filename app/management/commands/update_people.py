'''
commands to create default branding for OS Admin
'''

# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand

from app.models import People, Company
import itertools


class Command(BaseCommand):
    ''' Command '''
    help = 'Update People'


    def handle(self, *args, **options):
        self.stdout.write("================ Updation Starts ===============")
        data_queryset = Company.objects.all().values('web_address','uuid','modify_date')
        grouping_data = sorted(data_queryset, key=lambda room: room['web_address'])
        grouping_data = itertools.groupby(grouping_data, lambda d: d.get('web_address'))
        for index, data in grouping_data:
            data_list = list(data)
            grouping_data_set = [daset for daset in data_list]
            if len(grouping_data_set) > 1:
                grouping_data_set = sorted(grouping_data_set, key=lambda room: room['modify_date'])
                peopleset = People.objects.filter(company__in=Company.objects.filter(uuid__in=[gi.get('uuid') for gi in grouping_data_set[:len(grouping_data_set)-1]]))                
                peopleset.update(company=Company.objects.filter(uuid__in=[gi.get('uuid') for gi in grouping_data_set[-1:]]).get())
                Company.objects_with_deleted.filter(uuid__in=[gi.get('uuid') for gi in grouping_data_set[:len(grouping_data_set)-1]]).delete()
        self.stdout.write("=================== Updation ended ====================")

    
