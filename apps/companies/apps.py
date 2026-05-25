from django.apps import AppConfig

class CompaniesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.companies'
    label = 'companies'

    def ready(self):
        from . import checks  # noqa: F401
