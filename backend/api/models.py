from django.db import models
from django.contrib.auth.models import User

class ParkingSlot(models.Model):
    label = models.CharField(max_length=20, unique=True)
    zone = models.CharField(max_length=50, blank=True)
    max_vehicle_type = models.CharField(max_length=20, default='car')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.label} ({'active' if self.is_active else 'inactive'})"

class SlotStatus(models.Model):
    STATUS_CHOICES = [
        ('free', 'Free'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
    ]
    slot = models.OneToOneField(ParkingSlot, on_delete=models.CASCADE, related_name='status')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='free')
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.slot.label} - {self.status}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('active','Active'),
        ('completed','Completed'),
        ('cancelled','Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    slot = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_number = models.CharField(max_length=20)
    eta = models.DateTimeField()
    reserved_from = models.DateTimeField(null=True, blank=True)
    reserved_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.id} - {self.vehicle_number} - {self.status}"

class VehicleLog(models.Model):
    vehicle_number = models.CharField(max_length=20)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True, blank=True)
    entry_ts = models.DateTimeField(null=True, blank=True)
    exit_ts = models.DateTimeField(null=True, blank=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    plate_image = models.ImageField(upload_to='plates/', null=True, blank=True)
    ocr_text = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        status = "in" if self.entry_ts and not self.exit_ts else "out"
        return f"{self.vehicle_number} ({status})"

class SensorEvent(models.Model):
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='sensor_events')
    sensor_type = models.CharField(max_length=20)   # e.g., 'ultrasonic'
    value = models.FloatField()
    ts = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SensorEvent {self.slot.label} {self.sensor_type} {self.value} at {self.ts}"
