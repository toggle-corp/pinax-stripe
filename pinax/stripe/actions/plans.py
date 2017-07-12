from django.apps import apps as django_apps
from django.conf import settings
import stripe

from .. import utils
from .. import models


def sync_plans():
    """
    Syncronizes all plans from the Stripe API
    """

    OrgModel = django_apps.get_model(settings.STRIPE_ORG_MODEL)
    for org in OrgModel.objects.all():
        account_id = getattr(org, settings.PINAX_USER_ACCT_VAR.split('.')[-1])
        if account_id:
            try:
                plans = stripe.Plan().auto_paging_iter(stripe_account=account_id)
            except AttributeError:
                plans = iter(stripe.Plan().all(stripe_account=account_id).data)

            for plan in plans:
                defaults = dict(
                    amount=utils.convert_amount_for_db(plan["amount"], plan["currency"]),
                    currency=plan["currency"] or "",
                    interval=plan["interval"],
                    interval_count=plan["interval_count"],
                    name=plan["name"],
                    statement_descriptor=plan["statement_descriptor"] or "",
                    trial_period_days=plan["trial_period_days"],
                    metadata=plan["metadata"]
                )
                obj, created = models.Plan.objects.get_or_create(
                    stripe_id=plan["id"],
                    account_id=account_id,
                    defaults=defaults
                )
                utils.update_with_defaults(obj, defaults, created)
