from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SlotViewSet, BookingViewSet, sensor_event, ocr_plate, vehicle_entry, vehicle_exit, LoginView, LogoutView

router = DefaultRouter()
router.register(r'slots', SlotViewSet, basename='slots')
router.register(r'bookings', BookingViewSet, basename='bookings')

urlpatterns = [
    path('', include(router.urls)),
    path('sensors/event/', sensor_event, name='sensor_event'),
    path('ocr/plate/', ocr_plate, name='ocr_plate'),
    path('vehicle/entry/', vehicle_entry, name='vehicle_entry'),
    path('vehicle/exit/', vehicle_exit, name='vehicle_exit'),
    path('auth/login/', LoginView.as_view(), name='api_login'),
    path('auth/logout/', LogoutView.as_view(), name='api_logout'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

