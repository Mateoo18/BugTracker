from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and user.must_change_password:
            allowed_paths = {
                reverse("web:force_password_change"),
                reverse("web:logout"),
            }
            if request.path not in allowed_paths and not request.path.startswith("/admin/logout/"):
                return redirect("web:force_password_change")
        return self.get_response(request)
