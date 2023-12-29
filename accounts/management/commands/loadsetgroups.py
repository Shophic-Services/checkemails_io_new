'''
commands to load groups and permissions
'''

# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    ''' Command '''
    help = 'Load Groups with permissions into database'


    def handle(self, *args, **options):
        self.stdout.write("================ Update Tables Start ===============")
        self.load_groups()            
        self.stdout.write("=================== Update Tables End ====================")

    @staticmethod
    def load_groups():
        '''
        Load groups and permissions
        '''
        from checkemails.core.permission_config import PermissionConfig
        PermissionConfig().set_permissions()
        PermissionConfig().set_groups()
