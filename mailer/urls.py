from rest_framework.routers import DefaultRouter

from .views import DeliveryLogViewSet, MessageViewSet, ScheduleViewSet

router = DefaultRouter()
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"schedule", ScheduleViewSet, basename="schedule")
router.register(r"history", DeliveryLogViewSet, basename="history")

urlpatterns = router.urls
