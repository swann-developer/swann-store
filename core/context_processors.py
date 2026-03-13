from .cart import get_or_create_cart
from .models import CartItem

def cart_counter(request):

    try:
        cart = get_or_create_cart(request)

        count = CartItem.objects.filter(cart=cart).count()

    except:
        count = 0

    return {
        "cart_count": count
    }
