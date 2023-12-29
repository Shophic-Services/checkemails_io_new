'''
Web views for accounts
'''
import json
import math
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http.response import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import (FormView, RedirectView, TemplateView,
                                  UpdateView, View)

from accounts.forms import (UserAuthenticationForm, UserForgotPasswordForm, UserProfileForm,
                            UserResetPasswordForm,CreateUserForm, OTPUserForm,
                            UserSetPasswordForm)
from accounts.models import UserProfile, UserToken, User, UserRole
from accounts import constant, message
from django.shortcuts import resolve_url
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import authenticate, login
from accounts.utils import CreditQuery

from subscription.models import ClientCreditSubscription, SubscriptionPackage        
from subscription.utils import CreateSubscriptionData
from dateutil.relativedelta import relativedelta


class UserLoginView(LoginView):
    """
    Login View for user
    """
    template_name='accounts/web/login.html'
    redirect_authenticated_user=True
    form_class=UserAuthenticationForm

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        login(self.request, form.get_user(), backend="django.contrib.auth.backends.ModelBackend")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        url = resolve_url(settings.LOGIN_REDIRECT_URL)
        
        # if self.request.user.is_authenticated and self.request.user.is_superuser:
        #     return reverse_lazy('admin:index')
        return url 


class HomeView(LoginRequiredMixin, RedirectView):
    '''
    Home View
    '''
    template_name = "accounts/web/under_construction.html"
    
    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated and not self.request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy('app:home'))
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy('admin:index'))
        return super(HomeView, self).get(request, *args, **kwargs)





class SetPasswordTemplateView(TemplateView):
    '''
    Redirects after successfully sending password resend email
    '''

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('accounts:home'))
        return super(SetPasswordTemplateView, self).dispatch(request, *args, **kwargs)

    def get_template_names(self):
        template_type = self.kwargs.get('template_type')
        if template_type == 'done':
            template_name = 'accounts/web/set-password-success.html'
        else:
            template_name = 'accounts/web/set-password-error.html'
        return template_name


class ForgotPasswordTemplateView(TemplateView):
    '''
    Redirects after successfully sending password resend email
    '''

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('accounts:home'))
        return super(ForgotPasswordTemplateView, self).dispatch(request, *args, **kwargs)

    def get_template_names(self):
        template_type = self.kwargs.get('template_type')
        if template_type == 'done':
            template_name = 'accounts/web/reset-success.html'
        elif template_type == 'email-sent':
            template_name = 'accounts/web/reset-email-sent.html'
        else:
            template_name = 'accounts/web/reset-error.html'
        return template_name


class SetPasswordView(FormView):
    '''
    View for setting password
    '''
    template_name = 'accounts/web/set-password.html'
    form_class = UserResetPasswordForm
    success_url = reverse_lazy(
        'accounts:set_password_template', kwargs={'template_type': 'done'})
    error_url = reverse_lazy(
        'accounts:set_password_template', kwargs={'template_type': 'expired'})

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('accounts:home'))
        return super(SetPasswordView, self).dispatch(request, *args, **kwargs)

    def get_token(self):
        try:
            token = UserToken.objects.get(
                token=self.kwargs.get('token'), is_active=True, 
                expire_date__gte=timezone.now(),
                user__is_deleted=False
            )
        except UserToken.DoesNotExist:
            token = None
        return token

    def get(self, request, *args, **kwargs):
        token = self.get_token()
        if token:
            return super(SetPasswordView, self).get(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(self.error_url)

    def get_form_kwargs(self):
        data = super(SetPasswordView, self).get_form_kwargs()
        token = self.get_token()
        data.update({'token': token})
        return data

    def form_valid(self, form):
        if not form.user:
            return HttpResponseRedirect(self.error_url)
        else:
            form.save()
        return super(SetPasswordView, self).form_valid(form)


class PasswordResetView(FormView):
    '''
    View for setting password
    '''
    template_name = 'accounts/web/reset.html'
    form_class = UserResetPasswordForm
    success_url = reverse_lazy(
        'accounts:forgot_password_template', kwargs={'template_type': 'done'})
    error_url = reverse_lazy(
        'accounts:forgot_password_template', kwargs={'template_type': 'expired'})

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('accounts:home'))
        return super(PasswordResetView, self).dispatch(request, *args, **kwargs)

    def get_token(self):
        try:
            token = UserToken.objects.get(
                token=self.kwargs.get('token'), is_active=True, 
                expire_date__gte=timezone.now(),
                user__is_active=True, user__is_deleted=False
            )
        except UserToken.DoesNotExist:
            token = None
        return token

    def get(self, request, *args, **kwargs):
        token = self.get_token()
        if token:
            return super(PasswordResetView, self).get(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(self.error_url)

    def get_form_kwargs(self):
        data = super(PasswordResetView, self).get_form_kwargs()
        token = self.get_token()
        data.update({'token': token})
        return data

    def form_valid(self, form):
        if not form.user:
            return HttpResponseRedirect(self.error_url)
        else:
            form.save()
        return super(PasswordResetView, self).form_valid(form)


class ForgotPasswordRequestView(FormView):
    ''' ForgotPasswordRequestView '''
    form_class = UserForgotPasswordForm
    template_name = 'accounts/web/forgot.html'
    class_error = None
    success_url = reverse_lazy(
        'accounts:forgot_password_template', kwargs={'template_type': 'email-sent'})

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('accounts:home'))
        return super(ForgotPasswordRequestView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        data = super(ForgotPasswordRequestView, self).get_form_kwargs()
        data.update({'request': self.request})
        return data

    def form_valid(self, form):
        form.save()
        return super(ForgotPasswordRequestView, self).form_valid(form)


class AccountView(LoginRequiredMixin, TemplateView):
    '''
    Profile View for client
    '''
    template_name = 'accounts/web/partials/profile.html'

    def get_context_data(self, **kwargs):
        context = super(AccountView, self).get_context_data(**kwargs)
        
        credit_list = ClientCreditSubscription.objects.filter(client=self.request.user).order_by('-create_date')
        credit_activated = credit_list.filter(is_activated=True).first()
        context['credit_activated'] = credit_activated
        return context

    

class AccountUpdateView(LoginRequiredMixin, UpdateView):
    '''
    Profile Edit for client
    '''
    template_name = 'accounts/web/partials/edit-account.html'
    model = UserProfile
    form_class = UserProfileForm
    success_url = reverse_lazy('accounts:account_view')

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def get_context_data(self, **kwargs):
        context = super(AccountUpdateView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

    def get_form_kwargs(self):
        kwargs = super(AccountUpdateView, self).get_form_kwargs()
        kwargs.update({
            'user':self.request.user
        })
        return kwargs

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        for key, value in cleaned_data.items():
            if hasattr(self.request.user, key):
                setattr(self.request.user, key, value)
        if cleaned_data.get('change_password') and self.request.user.check_password(cleaned_data.get('old_password')):
            self.request.user.set_password(cleaned_data.get('new_password1'))
        self.request.user.save()
        update_session_auth_hash(self.request, self.request.user)
        form.user = self.request.user
        self.object = form.save()
        return super().form_valid(form)

  
class ChangePasswordRequestView(LoginRequiredMixin, FormView):
    template_name = 'customers/account-section.html'
    form_class = UserSetPasswordForm
    
    def get_form_kwargs(self):
        kwargs = super(ChangePasswordRequestView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(ChangePasswordRequestView, self).get_context_data(**kwargs)
        context['partial_template_name'] = 'accounts/web/partials/change-password.html'
        context['page_title'] = 'Change Password'
        context['active_tab_class'] = 'profile'
        context['user'] = self.request.user
        return context

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        return super().form_valid(form)
    
    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS, message.PASSWORD_CHANGE_SUCCESS)
        return reverse_lazy('accounts:account_view')

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'under_construction.html'

class AccountSettingTemplateView(LoginRequiredMixin, TemplateView):
    template_name = 'under_construction.html'


        
    
class UserSignupView(FormView):
    template_name = 'accounts/web/signup.html'

    form_class = CreateUserForm
    class_error = None
    success_url = reverse_lazy(
        'accounts:otp')

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('accounts:home'))
        return super(UserSignupView, self).dispatch(request, *args, **kwargs)


    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        user = User.objects.create_user(cleaned_data.get('email'), cleaned_data.get('password1'), False)
        user.first_name=cleaned_data.get('first_name')
        user.last_name=cleaned_data.get('last_name')
        user.phone=cleaned_data.get('phone')
        user.set_password(cleaned_data.get('password1'))
        user.is_active = False
        user.save()
        token_link = UserToken.create_token(
                UserToken.RANDOM_OTP_WEB, 
                user=user, 
                extras=user.email
            )
        token_link.send_forgot_password_email(self.request)
        self.request.session['token'] = str(token_link.uuid)
        plan = SubscriptionPackage.objects.filter(can_change=False, subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK).first()
        obj = ClientCreditSubscription.objects.create(client=user, plan=plan)
        if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_TWELVE_MONTH:
            obj.expire_date = timezone.now() + relativedelta(months=12)
        if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_ONE_MONTH:
            obj.expire_date = timezone.now() + relativedelta(months=1)
        if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_ONE_WEEK:
            obj.expire_date = timezone.now() + timezone.timedelta(days=6)
        obj.is_activated = True
        ClientCreditSubscription.objects.filter(client=obj.client).update(is_activated=False, expire_date=timezone.now())
        helper_class = CreateSubscriptionData(obj, self.request)
        obj = helper_class.create_data()    
        obj.save()
        helper_class.create_sub_transactions()

        return super().form_valid(form)


class UserOTPView(FormView):
    form_class = OTPUserForm
    
    template_name = 'accounts/web/otp.html'
    success_url = reverse_lazy(
        'emailtool:app_dashboard')


    def get(self, request, *args, **kwargs):
        token = self.get_token(self.request.session.get('token'))
        if token:
            return super(UserOTPView, self).get(request, *args, **kwargs)
        else:
            return HttpResponseRedirect( reverse_lazy(
        'accounts:login'))
    
    def get_token(self, uuid):
        try:
            token = UserToken.objects.get(
                uuid=uuid, is_active=True, 
                expire_date__gte=timezone.now(),
                user__is_deleted=False
            )
        except UserToken.DoesNotExist:
            token = None
        return token


    def get_context_data(self, **kwargs):
        context = super(UserOTPView, self).get_context_data(**kwargs)
        token = self.request.session.get('token')
        context.update({'token':token})
        if token:
            del self.request.session['token']
        return context

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        uuid = cleaned_data.get('token')
        token = self.get_token(uuid)
        if token:
            user = token.user
            user.is_active = True
            user.user_role = UserRole.objects.get(role=constant.CLIENT)
            user.save()
            login(self.request, token.user, backend='django.contrib.auth.backends.ModelBackend')
            update_session_auth_hash(self.request, token.user)
            UserToken.objects.filter(
            user=token.user, expire_date__gte=timezone.now(),
            is_active=True, token_type=UserToken.RANDOM_OTP_WEB).update(
                expire_date=timezone.now())
            
            token.user.send_email_to_admins(self.request)
            return super().form_valid(form)
        else:
            return super().form_invalid(form)




class CreditAccountsView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/web/credit.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super(CreditAccountsView, self).get_context_data(**kwargs)
        credit_list = ClientCreditSubscription.objects.filter(client=self.request.user).order_by('-create_date')
        credit_activated = credit_list.filter(is_activated=True).first()
        credit_list = credit_list.exclude(is_activated=True)
        credit_count = credit_list.count()
        page_num = 1
        credit_list_obj = credit_list[:self.paginate_by]
        total_page_num = math.ceil(credit_count / self.paginate_by)
        
        if self.request.GET.get('page_num'):
            page_num = int(self.request.GET.get('page_num'))

            if credit_list.count() > 0 and page_num:
                start_index = (page_num - 1) * self.paginate_by
                end_index = start_index + self.paginate_by
                credit_list = credit_list[start_index:end_index]
            credit_list_obj = credit_list
        context = {
            'credit_list': credit_list_obj,
            'credit_count': credit_count ,
            'credit_activated': credit_activated,
            'total_num_pages': total_page_num,
            'page_count': range(1, total_page_num + 1) if total_page_num > 1 else range(0),
            'page_dropdown_count': range(1, total_page_num + 1) if total_page_num > 1 else range(0),
            'current_page': page_num,
            'next_page': page_num + 1 if total_page_num > page_num else None,
            'prev_page': None,
            'paginate_by': self.paginate_by,
        }
        if page_num and page_num > 1:
            context.update({
                'prev_page': page_num - 1 
                })
        else:
            context.update({
                'prev_page': None
            })
        if total_page_num > 5:
            context['page_count'] = range(min([total_page_num -4, page_num]), min(page_num + 4, total_page_num) + 1)
        if self.request.is_ajax():
            ajax_params = json.loads(self.request.GET.get('search_pagination_data'))
            record_result = CreditQuery(ajax_params, self.paginate_by).get_queryset_result(credit_list)
            context.update(record_result)
        return context

        
    def get_template_names(self):
        
        if self.request.is_ajax():
            return 'accounts/web/partials/credit-listing.html'
        else:
            return self.template_name
    


class CreditStatusView(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        response = {'data': None, 'success': True}
        credit_info = ClientCreditSubscription.objects.filter(client=request.user, is_activated=True).order_by('-activated_date').first()
        response['data'] = credit_info.credit_balance if credit_info else 0
        return JsonResponse(response)
        