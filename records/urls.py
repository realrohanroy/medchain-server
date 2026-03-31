from django.urls import path
from .views import RecordUploadView, RecordTimelineView

urlpatterns = [
    path('', RecordTimelineView.as_view(), name='record_timeline'),
    path('upload/', RecordUploadView.as_view(), name='record_upload'),
]
