from django.contrib import admin
from .models import Product, ProductImage, Category, ProductTag, ProductVariant, CProduct, AnnouncementBar, HeroBanner
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Order, OrderItem, Coupon, ContactMessage
from django.contrib import admin


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("size", "sku", "stock_qty", "is_active")
    show_change_link = True

class ProductResource(resources.ModelResource):
    category = fields.Field(
        column_name="category",
        attribute="category",
        widget=ForeignKeyWidget(Category, "name"),
    )

    def before_import_row(self, row, **kwargs):
        # --- ensure safe text fields ---
        if not row.get("description"):
            row["description"] = ""

        if not row.get("additional_information"):
            row["additional_information"] = ""

        if not row.get("wash_care"):
            row["wash_care"] = ""

        # --- AUTO SLUG (critical for import_id_fields) ---
        if not row.get("slug") and row.get("title"):
            row["slug"] = slugify(row["title"])

        # --- price validation ---
        price = row.get("price")
        discount = row.get("discount_price")

        if price and discount:
            try:
                if float(discount) > float(price):
                    raise ValidationError(
                        "Discount price cannot be greater than price."
                    )
            except ValueError:
                raise ValidationError("Invalid price format.")

    class Meta:
        model = Product
        import_id_fields = ("slug",)
        fields = (
            "title",
            "slug",
            "category",
            "description",
            "fabric",
            "style",
            "color",
            "length",
            "wash_care",
            "additional_information",
            "price",
            "discount_price",
            "is_active",
        )
        skip_unchanged = True
        report_skipped = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "icon_preview", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")

    def icon_preview(self, obj):
        if obj.icon:
            return format_html(
                '<img src="{}" style="height:40px;" />',
                obj.icon.url
            )
        return "-"
    icon_preview.short_description = "Icon"


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductImageInline, ProductVariantInline]

    list_display = ("title", "category", "price", "is_active", "display_order")
    list_editable = (
        "display_order",
        "is_active",
    )

    list_filter = ("category", "tags", "is_active")
    ordering = ['display_order']

    search_fields = (
    "title",
    "slug",
    "description",
    "category__name",
    "variants__sku",
    )

    filter_horizontal = ("tags",)


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "is_active")
    search_fields = ("name", "slug")

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "sku", "stock_qty", "is_active")
    list_filter = ("size", "is_active")
    search_fields = ("product__title", "sku")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0



@admin.action(description="Mark selected orders as PAID")
def mark_as_paid(modeladmin, request, queryset):
    updated = queryset.update(
        payment_status="paid",
        order_status="confirmed"
    )
    modeladmin.message_user(request, f"{updated} orders marked as PAID")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_number",
        "first_name",
        "phone",
        "total",
        "order_status",
        "payment_status",
        "created_at",
    )

    list_filter = (
        "order_status",
        "payment_status",
        "payment_method",
        "created_at",
    )

    search_fields = (
        "order_number",
        "phone",
        "email",
        "first_name",
    )

    inlines = [OrderItemInline]

    actions = [mark_as_paid]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "is_active",
        "is_global",
    )

@admin.register(ContactMessage)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email")

admin.site.site_header = "Swann Admin"
admin.site.site_title = "Swann Control"
admin.site.index_title = "Swann Store Management"

@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")
    list_editable = ("is_active", "order")

@admin.register(CProduct)
class CProductAdmin(admin.ModelAdmin):
    list_display = ("product", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("product__title",)

@admin.register(AnnouncementBar)
class AnnouncementBasrAdmin(admin.ModelAdmin):
    list_display = ("text", "is_active")