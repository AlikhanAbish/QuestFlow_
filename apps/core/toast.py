import json

from django.contrib.messages import get_messages
from django.template.loader import render_to_string


def htmx_toast_trigger(message: str, type_: str = 'success', duration: int | None = None) -> str:
    """Build an HX-Trigger JSON value for client-side toast display."""
    payload: dict = {'message': message, 'type': type_}
    if duration is not None:
        payload['duration'] = duration
    return json.dumps({'showToast': payload})


def render_toasts_oob(request) -> str:
    """Render out-of-band toast HTML for pending Django messages."""
    messages = list(get_messages(request))
    if not messages:
        return ''
    return render_to_string('partials/_toasts_oob.html', {'messages': messages})
