def get_client_ip(request) -> str:
    """
    Retrieves the client's IP address from a Django request object.
    Supports HTTP_X_FORWARDED_FOR.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip
