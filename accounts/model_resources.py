from import_export import resources
from import_export.fields import Field

from accounts.models import User


class CustomUserResource(resources.ModelResource):
    name = Field(attribute='first_name', column_name='Name')
    email = Field(attribute='email', column_name='Email')
    user_role = Field(attribute='user_role__get_role_display',
                     column_name='User Role')
    contact_number = Field(attribute='phone', column_name='Contact Number')
    is_active = Field(column_name='Active')

    class Meta:
        model = User
        fields = ('name', 'email', 'user_role', 'contact_number',
                    'is_active', )
        export_order = ('name', 'email', 'user_role', 'contact_number',
                    'is_active',)
    
    def dehydrate_is_active(self, user):
        _ = self.__class__.__name__    
        return 'Enabled' if user.is_active else 'Disabled'
