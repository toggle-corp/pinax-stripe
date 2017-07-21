from django.apps import apps as django_apps
from django.utils.encoding import smart_str
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


def delete(plan, account_id):
    """
    delete a plan

    Args:
        plan: the plan to cancel
    """
    sub = plan.stripe_plan.delete()
    sync_plan_from_stripe_data(sub, account_id)


def create(id, name, amount, interval, account_id, currency="usd"):
    """
    Creates a plan for the given account id

    Args:
        account_id: the customer to create the subscription for
        id: plan id
        amount: should be a decimal.Decimal amount
        interval: interval for charge

    Returns:
        the data representing the plan object that was created
    """
    plan_params = {
        'amount': utils.convert_amount_for_api(amount, currency),
        'interval': interval,
        'name': name,
        'currency': "usd",
        'id': id,
        'stripe_account': account_id,
    }
    plan = stripe.Plan.create(**plan_params)

    return sync_plan_from_stripe_data(plan, account_id)


def retrieve(plan_id, account_id):
    if not plan_id:
        return
    try:
        return stripe.Plan.retrieve(
            plan_id,
            stripe_account=account_id)
    except stripe.InvalidRequestError as e:
        if smart_str(e).find("No such plan") == -1:
            raise


def sync_plan_from_stripe_data(plan, account_id):
    """
    Syncronizes data from the Stripe API for a subscription

    Args:
        customer: the customer who's subscription you are syncronizing
        subscription: data from the Stripe API representing a subscription

    Returns:
        the pinax.stripe.models.Subscription object created or updated
    """
    defaults = dict(
        amount=utils.convert_amount_for_db(plan["amount"], plan["currency"]),
        currency=plan["currency"] or "",
        interval=plan["interval"],
        interval_count=plan["interval_count"],
        name=plan["name"],
        statement_descriptor=plan["statement_descriptor"] or "",
        trial_period_days=plan["trial_period_days"],
        metadata=plan["metadata"],
    )
    pn, created = models.Plan.objects.get_or_create(
        stripe_id=plan["id"],
        account_id=account_id,
        defaults=defaults
    )
    pn = utils.update_with_defaults(pn, defaults, created)
    return pn
