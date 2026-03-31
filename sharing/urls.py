from django.urls import path
from .views import GenerateShareTokenView, AccessSharedRecordsView

urlpatterns = [
    path('generate/', GenerateShareTokenView.as_view(), name='share_generate'),
    path('<str:token>/', AccessSharedRecordsView.as_view(), name='share_access'),
]
