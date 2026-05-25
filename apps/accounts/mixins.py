from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.shortcuts import redirect
from django.contrib import messages


class RoleRequiredMixin(LoginRequiredMixin, AccessMixin):
    """
    Mixin to enforce a specific role (or list of roles) to access a view.

    Usage:
        class MyView(RoleRequiredMixin, View):
            required_roles = ['manager', 'admin']
    """
    required_roles: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        user_role = getattr(request.user, 'role', None)
        if self.required_roles and user_role not in self.required_roles:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('accounts:profile')

        return super().dispatch(request, *args, **kwargs)
