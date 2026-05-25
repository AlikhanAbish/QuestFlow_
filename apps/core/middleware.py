class SecurityHeadersMiddleware:
    """
    Adds missing security headers to HTTP responses.
    Useful as an extra layer of defense, even if Nginx already sets some.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # In a real setup, CSP is best managed by django-csp,
        # but you can add basic ones here if django-csp is not configured fully yet.
        return response
