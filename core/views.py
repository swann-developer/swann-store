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
from xhtml2pdf import pisa
from django.http import HttpResponse
from twilio.rest import Client
from django.conf import settings
from django.db.models import Q
from django.core import signing
from django.http import Http404





def product_list(request, category_slug=None):
    products = (
    Product.objects
    .filter(is_active=True)
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

    # VAT
    vat = taxable_amount * Decimal("0.05")

    # SHIPPING
    shipping = Decimal("7.50")

    grand_total = taxable_amount + vat + shipping

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

    # normalize phone format
    phone = phone.replace(" ", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    print("Sending OTP to:", phone)

    if not phone:
        return JsonResponse({"status": "error"})

    # ---- RATE LIMIT (30 seconds) ----
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

        request.session["otp_phone"] = phone.strip()
        request.session["otp_last_sent"] = timezone.now().isoformat()

        return JsonResponse({"status": "sent"})

    except Exception as e:

        print("Twilio error:", e)

        return JsonResponse({"status": "error"})

@require_POST
def verify_otp(request):
    data = json.loads(request.body)

    otp = data.get("otp", "").strip()

    phone = request.session.get("otp_phone")

    print("OTP entered:", otp)
    print("VERIFYING PHONE FROM SESSION:", phone)
    if not phone:
        return JsonResponse({"status": "error"})

    attempts = request.session.get("otp_attempts", 0)

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

        print("TWILIO CHECK STATUS:", verification_check.status)
        print("TWILIO VALID:", verification_check.valid)
        print("TWILIO SID:", verification_check.sid)

        if verification_check.status == "approved" or verification_check.valid:

            request.session["otp_verified"] = True
            request.session["otp_attempts"] = 0

            return JsonResponse({"status": "verified"})

        request.session["otp_attempts"] = attempts + 1

        return JsonResponse({"status": "invalid"})

    except Exception as e:
        print("Twilio error:", e)
        return JsonResponse({"status": "error"})

@require_POST
@transaction.atomic
def place_order(request):

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
    vat = taxable * Decimal("0.05")
    shipping = Decimal("7.50")

    grand_total = taxable + vat + shipping

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
    payment_method="cod"
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
            line_total=item.line_total
        )

        item.variant.stock_qty = F("stock_qty") - item.quantity
        item.variant.save()
        item.variant.refresh_from_db()
    items.delete()

    request.session.pop("applied_coupon", None)
    token = signing.dumps({"order_id": order.id})

    success_url = reverse("order_success", args=[order.id])

    return redirect(f"{success_url}?token={token}")

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

    request.session["otp_verified"] = False

    return render(
        request,
        "core/order-success.html",
        {"order": order}
    )

def download_invoice(request, order_id):

    token = request.GET.get("token")

    if not token:
        raise Http404()

    try:
        data = signing.loads(token, max_age=3600)
    except signing.BadSignature:
        raise Http404()

    if data.get("order_id") != order_id:
        raise Http404()

    order = get_object_or_404(Order, id=order_id)

    template = render_to_string(
        "core/invoice.html",
        {"order": order}
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.id}.pdf"'

    pisa.CreatePDF(template, dest=response)

    return response

def contact(request):

    if request.method != "POST":
        return render(request, "legal/contact.html")

    # honeypot bot trap
    if request.POST.get("website"):
        return JsonResponse({"status": "blocked"})

    name = request.POST.get("name", "").strip()
    email = request.POST.get("email", "").strip()
    phone = request.POST.get("phone", "").strip()
    message = request.POST.get("message", "").strip()
    print(name, email, message)

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
