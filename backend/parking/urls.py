from django.urls import path
from . import views

urlpatterns = [
    path('slots/', views.slots_list),
    path('bookings/', views.create_booking),
    path('slots/<int:pk>/sensor/', views.sensor_update),
    path('bookings/<int:booking_id>/arrive/', views.mark_arrived),
]
