class HtmxTemplateResponseMixin:
    """
    Mixin to handle HTMX requests dynamically.
    If `request.htmx` is True and `htmx_template_name` is set,
    it returns the `htmx_template_name`. Otherwise, it returns the standard template.
    """
    htmx_template_name = None

    def get_template_names(self):
        if getattr(self.request, 'htmx', False) and self.htmx_template_name:
            return [self.htmx_template_name]
        return super().get_template_names()


class CompanyIsolationMixin:
    """
    Mixin to filter QuerySets based on the current user's company.
    Assumes `self.request.user.company` exists.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if hasattr(self.request.user, 'company') and self.request.user.company:
                return qs.filter(company=self.request.user.company)
        return qs.none()
