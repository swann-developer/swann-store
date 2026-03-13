def get_or_create_cart(request):
    session_key = request.session.session_key

    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    from .models import Cart

    cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart