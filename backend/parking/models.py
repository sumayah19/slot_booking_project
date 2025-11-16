from django.db import models
from django.conf import settings

class Slot(models.Model):
    name = models.CharField(max_length=64)
    is_occupied = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = [
        ('reserved','Reserved'),
        ('arrived','Arrived'),
        ('cancelled','Cancelled'),
    ]
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name='bookings')
    vehicle_no = models.CharField(max_length=32, blank=True)
    eta = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='reserved')

    def __str__(self):
        return f"{self.slot} - {self.status} - {self.vehicle_no}"

class Gate(models.Model):
    status = models.CharField(max_length=16, default='closed')
    last_toggled = models.DateTimeField(auto_now=True)
