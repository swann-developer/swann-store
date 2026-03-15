from django.urls import path
from django.views.generic import TemplateView
from .views import (
product_list,
product_detail,
add_to_cart,
cart_detail,
remove_from_cart,
checkout_view,
apply_coupon,
send_otp,
verify_otp,
place_order,
order_success,
download_invoice,
contact,
search_suggestions,
update_cart_quantity,
)
urlpatterns = [
    # product listing
    path("products/", product_list, name="product_list"),
    path("products/<slug:category_slug>/", product_list, name="product_list_by_category"),

    # product detail (SEO friendly)
    path(
        "products/<slug:category_slug>/<slug:product_slug>/",
        product_detail,
        name="product_detail",
    ),
    path("cart/", cart_detail, name="cart_detail"),
    path("cart/add/", add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", remove_from_cart, name="remove_from_cart"),
    path("cart/update/<int:item_id>/", update_cart_quantity, name="update_cart_quantity"),
    path("checkout/", checkout_view, name="checkout"),
    path("apply-coupon/", apply_coupon, name="apply_coupon"),
    path("send-otp/", send_otp, name="send_otp"),
    path("verify-otp/", verify_otp, name="verify_otp"),
    path("place-order/", place_order, name="place_order"),
    path("order-success/<int:order_id>/", order_success, name="order_success"),
    path("invoice/<str:token>/", download_invoice, name="download_invoice"),
    path("privacy-policy/", TemplateView.as_view(template_name="legal/privacy-policy.html")),
    path("terms-and-conditions/", TemplateView.as_view(template_name="legal/terms.html")),
    path("refund-policy/", TemplateView.as_view(template_name="legal/refund.html")),
    path("shipping-policy/", TemplateView.as_view(template_name="legal/shipping.html")),
    path("contact/", contact, name="contact"),
    path("search-suggestions/", search_suggestions, name="search_suggestions"),
]
