from django.urls import path
from . import views

app_name = "telegram_bot"

urlpatterns = [
    # Webhook — receives Updates from Telegram (POST + GET health-check)
    path("webhook/", views.TelegramWebhookView.as_view(), name="webhook"),

    # Account linking widget (HTMX, loaded inside /profile/)
    path("connect/", views.TelegramConnectView.as_view(), name="connect"),
]
