def _append_toast_oob(response, oob_html: str):
    if not oob_html:
        return response

    def inject(resp):
        charset = getattr(resp, 'charset', 'utf-8') or 'utf-8'
        resp.content = resp.content + oob_html.encode(charset)
        return resp

    if hasattr(response, 'add_post_render_callback'):
        response.add_post_render_callback(inject)
    else:
        inject(response)
    return response


class HtmxToastMiddleware:
    """
    Append toast OOB fragments to HTMX HTML responses when Django messages are queued.
    Lets views keep using messages.success/error without duplicating toast markup.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not getattr(request, 'htmx', False):
            return response
        if response.status_code >= 400:
            return response

        content_type = response.get('Content-Type', '')
        if content_type and 'text/html' not in content_type:
            return response

        from apps.core.toast import render_toasts_oob

        return _append_toast_oob(response, render_toasts_oob(request))


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
