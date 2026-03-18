from django.core.management.base import BaseCommand
from core.models import Order
import stripe
from django.conf import settings


class Command(BaseCommand):
    help = "Retry pending Stripe payments"

    def handle(self, *args, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        orders = Order.objects.filter(
            payment_method="online",
            payment_status="pending",
            stripe_session_id__isnull=False
        )

        self.stdout.write(f"Checking {orders.count()} pending orders...")

        for order in orders:
            try:
                session = stripe.checkout.Session.retrieve(order.stripe_session_id)

                if session.payment_status == "paid":

                    if order.payment_status == "paid":
                        continue

                    order.payment_status = "paid"
                    order.transaction_id = session.payment_intent
                    order.order_status = "confirmed"
                    order.save()

                    self.stdout.write(f"✅ Fixed order {order.id}")

            except Exception as e:
                self.stdout.write(f"❌ Error for order {order.id}: {e}")
