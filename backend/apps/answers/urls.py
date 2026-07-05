from django.urls import path

from apps.answers.views import AskView


app_name = "answers"

urlpatterns = [
    path("", AskView.as_view(), name="ask"),
]
