from django.utils.decorators import method_decorator

try:
    from account.decorators import login_required
except ImportError:
    from django.contrib.auth.decorators import login_required

from .actions import customers
from .conf import settings

STRIP_USER_MODEL = __import__(settings.STRIP_USER_MODEL)


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)


class CustomerMixin(object):

    @property
    def customer(self):
        if not hasattr(self, "_customer"):
            self._customer = customers.get_customer_for_user(
                STRIP_USER_MODEL.objects.get(
                    pk=self.kwargs.get(settings.STRIPE_USER_MODEL_KWARGS_ID)))
        return self._customer

    def get_queryset(self):
        return super(CustomerMixin, self).get_queryset().filter(
            customer=self.customer
        )


class PaymentsContextMixin(object):

    def get_context_data(self, **kwargs):
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        context.update({
            "PINAX_STRIPE_PUBLIC_KEY": settings.PINAX_STRIPE_PUBLIC_KEY
        })
        return context
