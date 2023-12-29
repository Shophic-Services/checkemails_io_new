from django.contrib import admin
from django.db.models import Q
from django import forms
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from django.utils.translation import gettext_lazy as _

class BaseInputFilter(admin.SimpleListFilter):
    template = 'admin/filters/input_filter.html'
    parameter_name = None
    title = None
    
    def __init__(self, request, params, model, model_admin):
        self.lookup_kwarg = '%s__iexact' % self.parameter_name
        super().__init__(request, params, model, model_admin)
    
    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice
    
    def queryset(self, request, queryset):
        term = self.value()

        if term is None:
            return

        any_name = Q()
        
        # for bit in term.split():
        #     any_name &= (
        #         Q(**{self.lookup_kwarg:bit}) 
        #     )
        any_name &= (
                Q(**{self.lookup_kwarg:term}) 
            )
        return queryset.filter(any_name)

# class PeopleCompanyNameInputFilter(BaseInputFilter):
#     parameter_name = 'company__company_name'
#     title = 'Company Name'
    
# class CompanyNameInputFilter(BaseInputFilter):
#     parameter_name = 'company_name'
#     title = 'Company Name'


# class ContactNameInputFilter(BaseInputFilter):
#     parameter_name = 'contact_name'
#     title = 'Contact Name'

# class JobTitleInputFilter(BaseInputFilter):
#     parameter_name = 'job_title'
#     title = 'Job Title'

# class EmailAddressInputFilter(BaseInputFilter):
#     parameter_name = 'email_address'
#     title = 'Email Address'

# class CountryInputFilter(BaseInputFilter):
#     parameter_name = 'country'
#     title = 'Country'

# class IndustryInputFilter(BaseInputFilter):
#     parameter_name = 'industry'
#     title = 'Industry'

# class SubIndustryInputFilter(BaseInputFilter):
#     parameter_name = 'sub_industry'
#     title = 'SubIndustry'

# class EmployeesInputFilter(BaseInputFilter):
#     parameter_name = 'employees'
#     title = 'Employees'
    
# class WebAddressInputFilter(BaseInputFilter):
#     parameter_name = 'web_address'
#     title = 'Web Address'


# class PhoneNumberInputFilter(BaseInputFilter):
#     parameter_name = 'direct_phone_number'
#     title = 'Direct Phone Number'

# class DepartmentInputFilter(BaseInputFilter):
#     parameter_name = 'job_function'
#     title = 'Department'

class CustomRelatedDropdownFilter(RelatedDropdownFilter):
    def choices(self, changelist):
        yield {
            'selected': self.lookup_val is None and not self.lookup_val_isnull,
            'query_string': changelist.get_query_string(remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        for pk_val, val in self.lookup_choices:
            yield {
                'selected': self.lookup_val == str(pk_val),
                'query_string': changelist.get_query_string({self.lookup_kwarg: pk_val}, [self.lookup_kwarg_isnull]),
                'display': val,
            }
    
# class CompanyEmployeesInputFilter(BaseInputFilter):
#     parameter_name = 'company__employees'
#     title = 'Employees'

# class CompanyRevenueInputFilter(BaseInputFilter):
#     parameter_name = 'company__revenue'
#     title = 'Revenue'
    
# class PhysicalAddressInputFilter(BaseInputFilter):
#     parameter_name = 'physical_address'
#     title = 'Physical Address'

# class CityInputFilter(BaseInputFilter):
#     parameter_name = 'city'
#     title = 'City'
# class StateInputFilter(BaseInputFilter):
#     parameter_name = 'state'
#     title = 'State'
# class ZipCodeInputFilter(BaseInputFilter):
#     parameter_name = 'zip_code'
#     title = 'ZipCode'
# class CompanyWebAddressInputFilter(BaseInputFilter):
#     parameter_name = 'company__web_address'
#     title = 'Web Address'


# class CompanyIndustryInputFilter(BaseInputFilter):
#     parameter_name = 'company__industry'
#     title = 'Industry'

# ##
# class RecordTypeInputFilter(BaseInputFilter):
#     parameter_name = 'record_type'
#     title = 'Type'
# class RevenueInputFilter(BaseInputFilter):
#     parameter_name = 'revenue'
#     title = 'Revenue'
    
# class PeopleCompanyPhysicalAddressInputFilter(BaseInputFilter):
#     parameter_name = 'people_company__physical_address'
#     title = 'Physical Address'

# class PeopleCompanyCityInputFilter(BaseInputFilter):
#     parameter_name = 'people_company__city'
#     title = 'City'
# class PeopleCompanyStateInputFilter(BaseInputFilter):
#     parameter_name = 'people_company__state'
#     title = 'State'
# class PeopleCompanyZipCodeInputFilter(BaseInputFilter):
#     parameter_name = 'people_company__zip_code'
#     title = 'ZipCode'
# class PeopleCompanyCountryInputFilter(BaseInputFilter):
#     parameter_name = 'people_company__country'
#     title = 'Country'