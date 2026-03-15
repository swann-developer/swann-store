from django.http import Http404

class HideAdminMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/swann-control-panel-7491/"):
            if not request.user.is_authenticated:
                raise Http404()

        return self.get_response(request)


from django.http import HttpResponseForbidden

class BlockAdminBotsMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/admin"):
            ua = request.META.get("HTTP_USER_AGENT", "").lower()

            bad_bots = ["bot", "crawler", "spider", "scan"]

            if any(b in ua for b in bad_bots):
                return HttpResponseForbidden("Blocked")

        return self.get_response(request)
