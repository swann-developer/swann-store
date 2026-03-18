from django.db import models
from django.utils.text import slugify
import uuid
from django.utils import timezone
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os
from PIL import ImageOps



class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    image = models.ImageField(
        upload_to="categories/images/",
        null=True,
        blank=True,
    )
    icon = models.ImageField(
        upload_to="categories/icons/",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class ProductTag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)

    # 🔥 Product attributes (marketing-facing)
    fabric = models.CharField(max_length=120, blank=True, null=True)
    length = models.CharField(max_length=120, blank=True, null=True)
    style = models.CharField(max_length=12000, blank=True, null=True)
    color = models.CharField(max_length=120, blank=True, null=True)

    wash_care = models.TextField(blank=True, null=True)
    return_rules = models.TextField(blank=True, null=True)
    additional_information = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(
        ProductTag,
        related_name="products",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


    @property
    def discount_percent(self):
        if self.price and self.discount_price and self.price > 0:
            return round((self.price - self.discount_price) / self.price * 100, 2)
        return 0
    @property
    def final_price(self):
        return self.discount_price or self.price

    @property
    def primary_image(self):
        primary = self.images.filter(is_primary=True).first()
        return primary or self.images.first()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="images",
        on_delete=models.CASCADE
    )

    image = models.ImageField(upload_to="products/")
    thumbnail = models.ImageField(upload_to="products/thumbs/", blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.title} Image"
    @property
    def image_url(self):
        from django.conf import settings
        if settings.MEDIA_CDN_URL:
            return settings.MEDIA_CDN_URL + self.image.url
        return self.image.url
    def save(self, *args, **kwargs):

        if self.image and not self.image.name.lower().endswith(".webp"):

            img = Image.open(self.image)
            # convert to RGB (required for webp)
            img = ImageOps.exif_transpose(img)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # resize (product page uses ~624x600)
            MAX_SIZE = (1200, 1200)
            img.thumbnail(MAX_SIZE, Image.LANCZOS)
            # create thumbnail copy
            thumb_img = img.copy()
            thumb_img.thumbnail((600, 600), Image.LANCZOS)

            thumb_buffer = BytesIO()

            thumb_img.save(
                thumb_buffer,
                format="WEBP",
                quality=85,
                method=6
            )

            # SEO filename
            base_slug = slugify(self.product.slug)[:20]  # prevent long filename
            unique_id = uuid.uuid4().hex[:6]

            filename = f"{base_slug}-{unique_id}.webp"

            buffer = BytesIO()

            img.save(
                buffer,
                format="WEBP",
                quality=90,
                method=6
            )

            self.image.save(
                filename,
                ContentFile(buffer.getvalue()),
                save=False
            )
            thumb_filename = f"{base_slug}-{unique_id}-t.webp"

            self.thumbnail.save(
                thumb_filename,
                ContentFile(thumb_buffer.getvalue()),
                save=False
            )

        super().save(*args, **kwargs)
class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="variants",
        on_delete=models.CASCADE
    )
    size = models.CharField(max_length=20)
    sku = models.CharField(max_length=100, unique=True)
    stock_qty = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.title} - {self.size}"



class Cart(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.session_key}"

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name="items",
        on_delete=models.CASCADE,
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "variant")

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    @property
    def line_total(self):
        return (self.variant.product.final_price or 0) * self.quantity



class Order(models.Model):

    ORDER_STATUS = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    PAYMENT_METHOD = (
        ("cod", "Cash On Delivery"),
        ("online", "Online Payment"),
    )

    PAYMENT_STATUS = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    )

    order_number = models.CharField(max_length=20, unique=True, editable=False)

    # customer details
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # address
    area = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    po_box = models.CharField(max_length=50)
    emirate = models.CharField(max_length=100)

    # pricing
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    product_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=7.50)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # coupon
    coupon_code = models.CharField(max_length=50, blank=True, null=True)

    # status
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS, default="pending")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="pending")
    transaction_id = models.CharField(max_length=120, blank=True, null=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if not self.order_number:
            self.order_number = "SWN-INV-" + str(uuid.uuid4().hex[:6]).upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True
    )

    product_title = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    size = models.CharField(max_length=20)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_title} x {self.quantity}"

class Coupon(models.Model):

    DISCOUNT_TYPE = (
        ("percent", "Percent"),
        ("fixed", "Fixed Amount"),
    )

    code = models.CharField(max_length=50, unique=True)

    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE
    )

    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    is_active = models.BooleanField(default=True)

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    is_global = models.BooleanField(
        default=False,
        help_text="Auto applied coupon (festival offers)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

class ContactMessage(models.Model):

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.email}"
