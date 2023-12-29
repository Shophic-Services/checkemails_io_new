
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, TemplateView, View


class PlanRequiredView(LoginRequiredMixin, TemplateView):
    template_name = "subscription/plan_required.html"