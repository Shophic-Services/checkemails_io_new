from django.contrib import admin
import operator

from accounts.models import UserRole

class CustomBaseListFilterFilter(admin.SimpleListFilter):
    '''
    Custom base filter which implements generic lookups and
    queryset methods based on field_model, title,
    and parameter name parameters
    '''

    def lookups(self, request, model_admin):
        object_list = self.field_model.objects.all()
        filter_options = [(obj.id, str(obj), ) for obj in object_list]
        # Sort list according to the string displayed
        sorted_filter_options = filter_options.sort(key=operator.itemgetter(1))
        return filter_options
    
    def queryset(self, request, queryset):
        if self.value():
            query_dict = {
                self.parameter_name: self.value()
            }
            return queryset.filter(**query_dict)




class UserRoleListFilter(CustomBaseListFilterFilter):
    title = 'User Role'
    parameter_name = 'user_role__id__exact'
    field_model = UserRole

    def lookups(self, request, model_admin):
        object_list = self.field_model.objects.exclude(role__in=[UserRole.SUPERADMIN, UserRole.CLIENT])
        filter_options = [(obj.id, str(obj), ) for obj in object_list]
        # Sort list according to the string displayed
        sorted_filter_options = filter_options.sort(key=operator.itemgetter(1))
        return filter_options

