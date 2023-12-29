from django.utils import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.encoding import force_str
from django.db.models import Q
from accounts.models import User, UserRole
from app.middleware import get_current_user
from subscription.admin_forms import ClientCreditSubscriptionForm
from subscription.models import ClientCreditSubscription, ClientRecord, SubscriptionPackage, SubscriptionTransaction, PackageDescription
from subscription.utils import CreateSubscriptionData
from checkemails.core.admin import CheckEmailsBaseModelAdmin
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta

class SubscriptionBaseAdmin(CheckEmailsBaseModelAdmin):
    '''
    Customer Subscription Base Admin
    '''

    # form = AdminSubscriptionForm

    autocomplete_fields = ('client', )

    search_fields = ('client__full_name',  'client__full_name')

    ordering = ('activated_on', 'id')

    list_display = ('plan', 'client', 'activated_on')

    readonly_fields = (
        'plan_name', 'plan_price', 
        'plan_descriptions', 'activated_on',
        'expire_date', 'is_current','is_activated')

    def plan_name(self, obj):
        _ = self.class_error
        return obj.plan_data.get('name') if obj.plan_data else '-'
    plan_name.short_description = 'Plan Name'

    def plan_price(self, obj):
        _ = self.class_error
        return obj.plan_data.get('price') if obj.plan_data else '-'
    plan_price.short_description = 'Plan Price in USD'

    
    def plan_descriptions(self, obj):
        _ = self.class_error
        return ", ".join(obj.plan_data.get('plan_descriptions'))
    plan_descriptions.short_description = 'Plan Description'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = self.readonly_fields
        if obj and obj.id:
            readonly_fields += (
                'client', 'plan', 'payment_method', 
                'payment_receipt', 'acknowledgement',
            )
        return readonly_fields

    @staticmethod
    def has_permission_check(request):
        return True

    def has_add_permission(self, request):
        return self.has_permission_check(request)

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return self.has_permission_check(request)

    def has_view_permission(self, request, obj=None):
        return self.has_permission_check(request)

    def has_module_permission(self, request):
        return self.has_permission_check(request)

    def save_model(self, request, obj, form, change):
        '''
        Save JSON for object
        '''
        data_created = False
        if not obj.id:
            data_created = True
            helper_class = CreateSubscriptionData(obj, request)
            obj = helper_class.create_data()    
        super(SubscriptionBaseAdmin, self).save_model(request, obj, form, change)
        if data_created:
            helper_class.create_sub_transactions()
        return obj

    class Media:
        pass



class ClientCreditSubscriptionModelAdmin(SubscriptionBaseAdmin):
    
    fieldsets = (
        (None, {'fields': ("client",
        "is_activated",)}),
        (_('Info'), {'fields': (
            'plan_name', 'plan_price', 
        'plan_descriptions',
        "payment_method",
        "activated_on",
        "expire_date")}),
    )
    add_fieldsets = (
        (None, {'fields': ("client",
        "plan",
        "payment_method",
        "is_activated",)}),
    )
    empty_value_display = '-'
    autocomplete_fields = ['client']
    
    list_display = (
        "client",
        'plan_name', 'plan_price','activated_on',
        'expire_date', 'is_current','is_activated',
        "action_button"
    )
    readonly_fields = (
        'plan_name', 'plan_price', 
        'plan_descriptions', 'activated_on',
        'expire_date', 'is_current',
    )
    # form = ClientCreditSubscriptionForm

    actions = None
    list_display_links = None
    
    ordering = ('-activated_on','-is_activated')

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(ClientCreditSubscriptionModelAdmin, self).get_fieldsets(request, obj)
        
    def action_button(self, obj):
        change_url = reverse(
                'admin:%s_%s_change' % (ClientCreditSubscription._meta.app_label, ClientCreditSubscription._meta.model_name), 
                args=[force_str(obj.pk)]
            )
        return format_html('<a class="changelink" href="{}"></a>', change_url)

    action_button.short_description = 'Action'

    def save_model(self, request, obj, form, change):
        if not change:
            if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_TWELVE_MONTH:
                obj.expire_date = timezone.now() + relativedelta(months=12)
            if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_ONE_MONTH:
                obj.expire_date = timezone.now() + relativedelta(months=1)
            if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_ONE_WEEK:
                obj.expire_date = timezone.now() + timezone.timedelta(days=6)
            ClientCreditSubscription.objects.filter(client=obj.client).update(is_current=False, is_activated=False, expire_date=timezone.now())
        result = super(ClientCreditSubscriptionModelAdmin, self).save_model(request, obj, form, change)
        
        return result
    
    def has_change_permission(self, request, obj=None):
        return True 
    
class InlinePackageDescriptionAdmin(admin.TabularInline):
    class_error = None
    fields = ('description',)    
    model = PackageDescription
    extra = 0
    ordering = ('create_date',)

class SubscriptionPackageAdmin(CheckEmailsBaseModelAdmin):
    fields = ("name",
        "price",
        "subscription_period",
        "is_active",
        "is_custom",
        "can_change",
        "information",
        )
    empty_value_display = '-'
    
    list_display = (
        "name","price",
        "subscription_period",
        "is_active",
        "is_custom",
        "can_change",
        "action_button"
    )
    actions = None
    list_display_links = None
    
    ordering = ('-subscription_period',)

    readonly_fields = ('can_change',)

    inlines = [InlinePackageDescriptionAdmin,]

        
    def action_button(self, obj):
        change_url = reverse(
                'admin:%s_%s_change' % (SubscriptionPackage._meta.app_label, SubscriptionPackage._meta.model_name), 
                args=[force_str(obj.pk)]
            )
        return format_html('<a class="changelink" href="{}"></a>', change_url)

    action_button.short_description = 'Action'

    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = self.readonly_fields
        if obj and not obj.can_change:
            readonly_fields += (
                'subscription_period', 'is_active', 'is_custom', 'price'
            )
        return readonly_fields

    
    def has_delete_permission(self, request, obj=None):
        if obj and not obj.can_change:
            return False 
        return True


admin.site.register(ClientCreditSubscription, ClientCreditSubscriptionModelAdmin)
admin.site.register(ClientRecord)
admin.site.register(SubscriptionPackage, SubscriptionPackageAdmin)
admin.site.register(SubscriptionTransaction)