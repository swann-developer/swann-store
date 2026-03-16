from django.http import Http404
from django.conf import settings

class HideAdminMiddleware:
    admin_path = f"/{settings.ADMIN_URL}"
    # allow admin login page
    if request.path.startswith(admin_path):
        if request.path == admin_path + "login/":
            return self.get_response(request)
        if not request.user.is_authenticated:
            raise Http404()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(f"/{settings.ADMIN_URL}"):
            if not request.user.is_authenticated:
                raise Http404()

        return self.get_response(request)


from django.http import HttpResponseForbidden

class BlockAdminBotsMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith(f"/{settings.ADMIN_URL}"):
            ua = request.META.get("HTTP_USER_AGENT", "").lower()

            bad_bots = ["bot", "crawler", "spider", "scan"]

            if any(b in ua for b in bad_bots):
                return HttpResponseForbidden("Blocked")

        return self.get_response(request)
