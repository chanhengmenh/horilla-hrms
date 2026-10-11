from django.apps import AppConfig
from django.conf import settings


class LeaveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "leave"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns
        from leave import signals

        settings.APPS.append("leave")
        # ``horilla.methods.remove_dynamic_url`` only searches the url modules
        # listed in ``settings.APP_URLS``, so without this entry the one-shot
        # error-report routes appended to ``leave.urls.urlpatterns`` can never
        # be found and dropped again (asset/attendance/project all register).
        settings.APP_URLS.append("leave.urls")
        urlpatterns.append(
            path("leave/", include("leave.urls")),
        )
        super().ready()
