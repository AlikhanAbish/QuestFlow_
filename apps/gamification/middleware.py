from __future__ import annotations

from django.utils import timezone


class DailyLoginXPMiddleware:
    """
    TZ 2.1.3 / Fix for Пункт 3:
    Awards 'daily_login' XP on the FIRST authenticated request of each calendar
    day, not only on the login signal.

    This solves the case where a user stays logged-in for multiple days without
    explicitly logging out (e.g., session persists across days).

    Session key used:  '_daily_xp_date'  →  stores the ISO date string of the
    last day XP was awarded so we award it at most once per UTC day.

    Placed AFTER AuthenticationMiddleware so request.user is available.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._maybe_award_daily_xp(request)
        return self.get_response(request)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _maybe_award_daily_xp(self, request) -> None:
        """Check session; award XP at most once per day per authenticated user."""
        if not getattr(request, 'user', None):
            return
        if not request.user.is_authenticated:
            return

        today_str = timezone.now().date().isoformat()  # e.g. "2026-05-09"
        session_key = '_daily_xp_date'

        if request.session.get(session_key) == today_str:
            # Already awarded today — skip
            return

        # Mark in session immediately to prevent duplicate awards from
        # concurrent requests (the XP write itself is atomic in the engine).
        request.session[session_key] = today_str

        # Import lazily to avoid circular imports at module load time.
        try:
            from apps.gamification.engine import GamificationEngine
            engine = GamificationEngine(request.user)
            engine.handle_login()   # updates streak + awards daily_login XP
        except Exception:
            # Non-critical path — never crash the request pipeline.
            pass
