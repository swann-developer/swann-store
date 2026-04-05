from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import render, get_object_or_404,redirect
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from .models import (
    Product,
    Category,
    ProductVariant,
    CartItem,
    Order,
    OrderItem,
    ContactMessage,
    CProduct,
    AnnouncementBar,
    HeroBanner,
)
from django.urls import reverse
from .cart import get_or_create_cart
from .models import CartItem
from .cart import get_or_create_cart
from decimal import Decimal
from .models import Coupon
from django.utils import timezone
import random
import json
from datetime import timedelta
from django.http import JsonResponse
from django.db.models import F
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import send_mail
from xhtml2pdf import pisa
from io import BytesIO
from django.http import HttpResponse
from twilio.rest import Client
from django.conf import settings
from django.db.models import Q
from django.core import signing
from django.http import FileResponse, Http404
from django.core.cache import cache
from django.utils._os import safe_join
import os
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage




def product_list(request, category_slug=None):
    products = (
    Product.objects
    .filter(is_active=True, category__isnull=False)
    .select_related("category")
    .prefetch_related("images", "tags")
    .distinct()
    )

    search_query = request.GET.get("search")

    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    categories = Category.objects.filter(is_active=True)

    # --- CATEGORY FILTER (from URL first) ---
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # --- fallback: query param (keeps backward compatibility) ---
    query_category = request.GET.get("category")
    if query_category:
        products = products.filter(category__slug=query_category)

    # --- TAG FILTER ---
    tag_slug = request.GET.get("tag")
    if tag_slug:
        products = products.filter(tags__slug=tag_slug)

    # --- SORT ---
    sort = request.GET.get("sort")

    if sort == "price_low":
        products = products.order_by("price")
    elif sort == "price_high":
        products = products.order_by("-price")
    elif sort == "latest":
        products = products.order_by("-created_at")

    paginator = Paginator(products, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "core/products.html",
        {
            "page_obj": page_obj,
            "categories": categories,
            "total_count": paginator.count,
            "current_category": category_slug or query_category,
            "current_tag": tag_slug,
            "current_sort": sort,
        },
    )


def product_detail(request, category_slug, product_slug):
    product = get_object_or_404(
        Product.objects.select_related("category")
        .prefetch_related("images", "tags", "variants"),
        slug=product_slug,
        is_active=True,
    )

    if product.category and product.category.slug != category_slug:
        return redirect(
            "product_detail",
            category_slug=product.category.slug,
            product_slug=product.slug,
        )

    # ⭐ cart awareness
    cart = get_or_create_cart(request)
    in_cart_variant_ids = set(
        CartItem.objects.filter(cart=cart, variant__product=product)
        .values_list("variant_id", flat=True)
    )

    relative_url = reverse(
        "product_detail",
        kwargs={
            "category_slug": product.category.slug,
            "product_slug": product.slug,
        },
    )
    variants = product.variants.filter(is_active=True)

    all_out_of_stock = True
    for v in variants:
        if v.stock_qty > 0:
            all_out_of_stock = False
            break

    product_url = request.build_absolute_uri(relative_url)
    default_variant = product.variants.filter(is_active=True).order_by("id").first()

    return render(
        request,
        "core/product-details.html",
        {
            "product": product,
            "product_url": product_url,
            "default_variant": default_variant,
            "in_cart_variant_ids": in_cart_variant_ids,
            "all_out_of_stock": all_out_of_stock,
        },
    )

@require_POST
def add_to_cart(request):
    variant_id = request.POST.get("variant_id")
    quantity = int(request.POST.get("quantity", 1))

    if not variant_id:
        return JsonResponse({"status": "error", "message": "Select size."})

    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        is_active=True,
    )

    # STOCK GUARD
    if variant.stock_qty < quantity:
        return JsonResponse({
            "status": "out_of_stock",
            "message": "Out of stock"
        })

    cart = get_or_create_cart(request)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={"quantity": quantity},
    )

    if not created:
        return JsonResponse({
            "status": "exists",
            "message": "Item already in cart"
        })

    return JsonResponse({
        "status": "added",
        "message": "Added to cart"
    })

def cart_detail(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product")

    subtotal_mrp = 0
    total_discount = 0
    final_total = 0

    for item in items:
        product = item.variant.product
        qty = item.quantity

        mrp = product.price or 0
        final = product.final_price or 0

        subtotal_mrp += mrp * qty
        final_total += final * qty
        total_discount += (mrp - final) * qty

    discount_percent = 0
    if subtotal_mrp > 0:
        discount_percent = round((total_discount / subtotal_mrp) * 100, 2)

    return render(
        request,
        "core/cart.html",
        {
            "cart": cart,
            "items": items,
            "subtotal_mrp": subtotal_mrp,
            "total_discount": total_discount,
            "final_total": final_total,
            "discount_percent": discount_percent,
        },
    )

@require_POST
def remove_from_cart(request, item_id):
    cart = get_or_create_cart(request)

    CartItem.objects.filter(id=item_id, cart=cart).delete()

    return redirect("cart_detail")


@require_POST
def update_cart_quantity(request, item_id):

    cart = get_or_create_cart(request)

    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    data = json.loads(request.body)
    quantity = int(data.get("quantity", 1))

    if quantity < 1:
        quantity = 1

    if quantity > 10:
        quantity = 10

    stock = item.variant.stock_qty
    if quantity > stock:
        quantity = stock

    item.quantity = quantity
    item.save()

    return JsonResponse({"status": "updated"})


def checkout_view(request):
    request.session.setdefault("otp_verified", False)
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product")

    # prevent checkout if cart empty
    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart_detail")

    subtotal_mrp = Decimal("0")
    product_discount = Decimal("0")

    for item in items:
        product = item.variant.product
        qty = item.quantity

        mrp = product.price or Decimal("0")
        final = product.final_price or Decimal("0")

        subtotal_mrp += mrp * qty
        product_discount += (mrp - final) * qty

    cart_total = subtotal_mrp - product_discount

    # --------------------------
    # COUPON
    # --------------------------

    coupon_discount = Decimal("0")
    applied_coupon = None

    coupon_code = request.session.get("applied_coupon")

    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()

        if coupon:
            applied_coupon = coupon

            if coupon.discount_type == "percent":
                coupon_discount = cart_total * Decimal(coupon.discount_value) / 100
            else:
                coupon_discount = Decimal(coupon.discount_value)

    taxable_amount = max(cart_total - coupon_discount, Decimal("0"))

    shipping = Decimal("7.50")

    # ✅ VAT AFTER SHIPPING
    vat = (taxable_amount + shipping) * Decimal("0.05")

    grand_total = taxable_amount + shipping + vat

    return render(
        request,
        "core/checkout.html",
        {
            "items": items,
            "subtotal_mrp": subtotal_mrp,
            "product_discount": product_discount,
            "cart_total": cart_total,
            "coupon_discount": coupon_discount,
            "vat": vat,
            "shipping": shipping,
            "grand_total": grand_total,
            "applied_coupon": applied_coupon,
        },
    )

def apply_coupon(request):

    code = request.GET.get("coupon_code", "").strip()

    try:
        coupon = Coupon.objects.get(code__iexact=code, is_active=True)

        request.session["applied_coupon"] = coupon.code

        return JsonResponse({
            "status":"success"
        })

    except Coupon.DoesNotExist:

        return JsonResponse({
            "status":"invalid"
        })


@require_POST
def send_otp(request):

    data = json.loads(request.body)
    phone = data.get("phone", "").strip()

    if not phone:
        return JsonResponse({"status": "error"})

    # normalize phone
    phone = phone.replace(" ", "")
    if not phone.startswith("+"):
        phone = "+" + phone

    ip = request.META.get("REMOTE_ADDR")

    # ---- MAX 5 OTP REQUESTS PER IP ----
    key = f"otp_attempts_{ip}"
    attempts = cache.get(key, 0)

    if attempts >= 5:
        return JsonResponse({"status": "blocked"})

    # ---- 30 SECOND COOLDOWN ----
    last_sent = request.session.get("otp_last_sent")

    if last_sent:
        last_sent = timezone.datetime.fromisoformat(last_sent)

        if timezone.now() - last_sent < timedelta(seconds=30):
            return JsonResponse({"status": "wait"})

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    try:

        client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(
            to=phone,
            channel="sms"
        )

        # store phone + timestamps
        request.session["otp_phone"] = phone
        request.session["otp_last_sent"] = timezone.now().isoformat()

        # increase attempt counter
        cache.set(key, attempts + 1, timeout=3600)

        return JsonResponse({"status": "sent"})

    except Exception as e:

        print("Twilio error:", e)

        return JsonResponse({"status": "error"})

@require_POST
def verify_otp(request):

    data = json.loads(request.body)
    otp = data.get("otp", "").strip()

    phone = request.session.get("otp_phone")

    if not phone:
        return JsonResponse({"status": "error"})

    attempts = request.session.get("otp_verify_attempts", 0)

    # block brute force attempts
    if attempts >= 5:
        return JsonResponse({"status": "blocked"})

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    try:

        verification_check = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(
            to=phone,
            code=otp
        )

        if verification_check.status == "approved" or verification_check.valid:

            request.session["otp_verified"] = True

            # reset counters
            request.session["otp_verify_attempts"] = 0

            ip = request.META.get("REMOTE_ADDR")
            cache.delete(f"otp_attempts_{ip}")

            return JsonResponse({"status": "verified"})

        request.session["otp_verify_attempts"] = attempts + 1

        return JsonResponse({"status": "invalid"})

    except Exception as e:

        print("Twilio error:", e)

        return JsonResponse({"status": "error"})

@require_POST
@transaction.atomic
def place_order(request):

    if not request.POST.get("phone") or len(request.POST.get("phone")) < 8:
        messages.error(request, "Invalid phone number")
        return redirect("checkout")

    if request.session.get("otp_verified") != True:
        messages.error(request, "Please verify your phone number first.")
        return redirect("checkout")

    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product").select_for_update()

    subtotal = Decimal("0")
    product_discount = Decimal("0")

    for item in items:
        product = item.variant.product

        mrp = product.price or Decimal("0")
        final = product.final_price or Decimal("0")

        subtotal += mrp * item.quantity
        product_discount += (mrp - final) * item.quantity

    cart_total = subtotal - product_discount

    if not items.exists():
        messages.error(request, "Cart empty")
        return redirect("cart_detail")
    coupon_discount = Decimal("0")
    coupon_code = request.session.get("applied_coupon")

    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()

        if coupon:
            if coupon.discount_type == "percent":
                coupon_discount = cart_total * coupon.discount_value / 100
            else:
                coupon_discount = coupon.discount_value
    taxable = cart_total - coupon_discount

    shipping = Decimal("7.50")

    # ✅ VAT AFTER SHIPPING
    vat = (taxable + shipping) * Decimal("0.05")

    grand_total = taxable + shipping + vat
    order = Order.objects.create(
    first_name=request.POST.get("first_name"),
    last_name=request.POST.get("last_name"),
    email=request.POST.get("email"),
    phone=request.POST.get("phone"),
    area=request.POST.get("area"),
    landmark=request.POST.get("landmark"),
    po_box=request.POST.get("po_box"),
    emirate=request.POST.get("emirate"),

    subtotal=subtotal,
    product_discount=product_discount,
    coupon_discount=coupon_discount,
    vat_amount=vat,
    shipping_cost=shipping,
    total=grand_total,

    coupon_code=coupon_code,
    payment_method=request.POST.get("payment_method", "cod"),
    payment_status="pending",
    )

    for item in items:

        # 🔒 FINAL STOCK CHECK
        if item.variant.stock_qty < item.quantity:
            messages.error(request, f"{item.variant.product.title} is out of stock.")
            return redirect("cart_detail")

        OrderItem.objects.create(
            order=order,
            product=item.variant.product,
            variant=item.variant,
            product_title=item.variant.product.title,
            sku=item.variant.sku,
            size=item.variant.size,
            price=item.variant.product.final_price,
            quantity=item.quantity,
            line_total = item.variant.product.final_price * item.quantity,
        )

        # reserve stock → mark but don't deduct yet
        item.variant.stock_qty = F("stock_qty") - item.quantity
        item.variant.save()
# items will be deleted AFTER successful payment (webhook)
    request.session.pop("applied_coupon", None)
    token = signing.dumps({"order_id": order.id})

    stripe.api_key = settings.STRIPE_SECRET_KEY

    payment_method = order.payment_method
    print("PAYMENT METHOD:", payment_method)

    # =========================
    # COD FLOW (UNCHANGED)
    # =========================
    if payment_method == "cod":

        # clear cart immediately
        CartItem.objects.filter(cart=cart).delete()

        success_url = reverse("order_success", args=[order.id])
        return redirect(f"{success_url}?token={token}")

    # =========================
    # STRIPE FLOW
    # =========================

    # prevent duplicate session
    if order.stripe_session_id:
        return redirect("checkout")


    print("ITEM COUNT:", items.count())
    line_items = []

    order_items = OrderItem.objects.filter(order=order)

    for item in order_items:
        price = item.price
        quantity = item.quantity or 0

        if not price or price <= 0:
            continue

        if quantity < 1:
            continue

        unit_amount = int(price * 100)

        if unit_amount < 1:
            continue

        line_items.append({
            "price_data": {
                "currency": "aed",
                "product_data": {
                    "name": item.variant.product.title,
                },
                "unit_amount": unit_amount,
            },
            "quantity": quantity,
        })

    # ✅ ADD SHIPPING AS LINE ITEM
    if shipping > 0:
        line_items.append({
            "price_data": {
                "currency": "aed",
                "product_data": {
                    "name": "Shipping",
                },
                "unit_amount": int(float(shipping) * 100),
            },
            "quantity": 1,
        })

    # ✅ ADD VAT AS LINE ITEM
    if vat > 0:
        line_items.append({
            "price_data": {
                "currency": "aed",
                "product_data": {
                    "name": "VAT (5%)",
                },
                "unit_amount": int(float(vat) * 100),
            },
            "quantity": 1,
        })

    if not line_items:
        print("❌ EMPTY LINE ITEMS → DEBUG ORDER ITEMS:", list(order_items.values()))
        messages.error(request, "Unable to process payment.")
        return redirect("checkout")

    print("LINE ITEMS:", line_items)

    for oi in order_items:
        print("ORDER ITEM:", oi.quantity, oi.price)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("order_success", args=[order.id])
        ) + f"?token={token}",
        cancel_url=request.build_absolute_uri(
            reverse("payment_cancel", args=[order.id])
        ),
        metadata={
            "order_id": order.id
        }
    )

    order.stripe_session_id = session.id
    order.save()

    return redirect(session.url)

@never_cache
def order_success(request, order_id):

    token = request.GET.get("token")

    if not token:
        raise Http404()

    try:
        data = signing.loads(token, max_age=3600)  # token valid for 1 hour
    except signing.BadSignature:
        raise Http404()

    if data.get("order_id") != order_id:
        raise Http404()

    order = get_object_or_404(Order, id=order_id)

    # ✅ FIX: ensure payment status is updated (fallback if webhook is slow)
    if order.payment_method == "online" and order.payment_status != "paid" and order.stripe_session_id:
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY

            session = stripe.checkout.Session.retrieve(order.stripe_session_id)

            if session.payment_status == "paid":

                # idempotency
                if order.payment_status != "paid":
                    order.payment_status = "paid"
                    order.transaction_id = session.payment_intent
                    order.order_status = "confirmed"
                    order.save()

        except Exception as e:
            print("Stripe verify error:", e)

    request.session["otp_verified"] = False
    request.session.pop("otp_phone", None)

    # ✅ clear cart after success (correct place)
    cart = get_or_create_cart(request)
    CartItem.objects.filter(cart=cart).delete()

    items = order.items.select_related("product")

    return render(
        request,
        "core/order-success.html",
        {
            "order": order,
            "items": items,
            "token": token,
        }
    )
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404

def download_invoice(request, token):

    try:
        data = signing.loads(token, max_age=3600)
        order_id = data["order_id"]
    except signing.BadSignature:
        raise Http404()

    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        id=order_id
    )

    html = render_to_string(
        "core/invoice.html",
        {
            "order": order,
            "items": order.items.all(),
            "request": request
        }
    )

    buffer = BytesIO()

    pisa_status = pisa.CreatePDF(
        html,
        dest=buffer
    )

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_number}.pdf"'

    return response

def contact(request):

    if request.method != "POST":
        return render(request, "legal/contact.html")

    # honeypot bot trap
    if request.POST.get("website"):
        return JsonResponse({"status": "blocked"})

    # RATE LIMIT (max 5 messages per hour per IP)

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")

    key = f"contact_attempts_{ip}"
    attempts = cache.get(key, 0)

    if attempts >= 5:
        return JsonResponse({"status": "blocked"})

    cache.set(key, attempts + 1, timeout=3600)

    name = request.POST.get("name", "").strip()
    email = request.POST.get("email", "").strip()
    phone = request.POST.get("phone", "").strip()
    message = request.POST.get("message", "").strip()

    if not name or not email or not message:
        return JsonResponse({"status": "error"})

    ContactMessage.objects.create(
        name=name,
        email=email,
        phone=phone,
        message=message
    )

    return JsonResponse({"status": "success"})


def search_suggestions(request):

    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse({"results": []})

    products = (
        Product.objects
        .filter(is_active=True)
        .filter(
            Q(title__icontains=query) |
            Q(category__name__icontains=query)
        )
        .select_related("category")
        .prefetch_related("images")
        [:6]
    )

    results = []

    for product in products:

        image = None
        first_image = product.images.first()

        if first_image:
            image = first_image.image.url

        results.append({
            "title": product.title,
            "url": reverse(
                "product_detail",
                kwargs={
                    "category_slug": product.category.slug,
                    "product_slug": product.slug
                }
            ),
            "image": image
        })

    return JsonResponse({"results": results})


def serve_media(request, path):
    try:
        file_path = safe_join(settings.MEDIA_ROOT, path)
    except ValueError:
        raise Http404()

    if not os.path.exists(file_path):
        raise Http404()

    return FileResponse(open(file_path, "rb"))


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return HttpResponse(status=400)

    # ✅ PAYMENT SUCCESS
    if event["type"] == "checkout.session.completed":

        session = event["data"]["object"]

        order_id = session["metadata"]["order_id"]

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return HttpResponse(status=200)

        # 🔒 idempotency (avoid duplicate webhook)
        if order.payment_status == "paid":
            return HttpResponse(status=200)
# 🔒 safety: prevent double stock deduction issues

        order.payment_status = "paid"
        order.transaction_id = session.get("payment_intent")
        order.order_status = "confirmed"
        order.save()

        # ✅ clear cart AFTER payment success
        # ✅ clear only current user's cart
        cart = None

        # try to find cart via session (if available)
        session_key = request.session.session_key

        if session_key:
            from core.models import Cart
            cart = Cart.objects.filter(session_key=session_key).first()

        if cart:
            CartItem.objects.filter(cart=cart).delete()
        # ✅ SEND EMAIL
        subject = f"Order Confirmed - {order.order_number}"

        message = f"""
        Hi {order.first_name},

        Your payment was successful.

        Order ID: {order.order_number}
        Amount Paid: AED {order.total}

        Thank you for shopping with Swann ❤️
        """

        html = render_to_string(
            "core/invoice.html",
            {
                "order": order,
                "items": order.items.all(),
            }
        )

        buffer = BytesIO()
        pisa.CreatePDF(html, dest=buffer)
        buffer.seek(0)

        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
        )

        email.attach(
            f"invoice_{order.order_number}.pdf",
            buffer.read(),
            "application/pdf"
        )

        email.send(fail_silently=False)
    # ❌ PAYMENT FAILED / EXPIRED
    if event["type"] == "checkout.session.expired":

        session = event["data"]["object"]
        order_id = session["metadata"]["order_id"]

        order = Order.objects.filter(id=order_id).first()

        if order:
            order.payment_status = "failed"
            order.save()

            # ✅ RESTORE STOCK
            for item in order.orderitem_set.all():
                item.variant.stock_qty = F("stock_qty") + item.quantity
                item.variant.save()

    return HttpResponse(status=200)

def run_retry_payments(request):

    # 🔒 protect endpoint
    secret = request.GET.get("key")
    if secret != os.getenv("CRON_SECRET"):
        return HttpResponse("Unauthorized", status=403)

    from django.core.management import call_command
    call_command("retry_payments")

    return HttpResponse("OK")

def payment_cancel(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    # restore stock
    for item in order.items.all():
        item.variant.stock_qty = F("stock_qty") + item.quantity
        item.variant.save()

    order.payment_status = "failed"
    order.save()

    messages.error(request, "Payment cancelled")

    return redirect("checkout")


def home(request):
    banners = HeroBanner.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)[:8]
    announcement = AnnouncementBar.objects.filter(is_active=True).first()
    collections = CProduct.objects.filter(is_active=True).select_related("product__category").prefetch_related("product__images")

    return render(request, "core/home.html", {
        "banners": banners,
        "categories": categories,
        "announcement": announcement,
        "collections": collections,
    })