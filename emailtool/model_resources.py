from datetime import datetime
from import_export import resources
from import_export.fields import Field
from emailtool.models import EmailSearch
from accounts.models import User
from emailtool.utils import ForeignKeyWidgetWithCreation

class EmailSearchResource(resources.ModelResource):
    
    email_address = Field(attribute='email_address', column_name='Email Address')
    verified = Field(attribute='verified', column_name='Verified')
    message = Field(attribute='message', column_name='Message')
    code = Field(attribute='code', column_name='Code')
    added_by = Field(attribute='added_by', column_name='Added By')
    
    class Meta:
        model = EmailSearch
        fields = ('email_address',
        'verified',
        'message',
        'code',
        'added_by',
        )
        export_order = ('email_address',
        'verified',
        'message',
        'code',
        'added_by',
        )
        

    def after_export(self, queryset, data, *args, **kwargs):
        data.title = "Email Data"