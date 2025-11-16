from django.contrib import admin
from .models import ParkingSlot, SlotStatus, Booking, VehicleLog, SensorEvent

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ('label','zone','max_vehicle_type','is_active')
    search_fields = ('label','zone')

@admin.register(SlotStatus)
class SlotStatusAdmin(admin.ModelAdmin):
    list_display = ('slot','status','last_update')
    list_filter = ('status',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id','user','vehicle_number','slot','eta','status','created_at')
    list_filter = ('status',)
    search_fields = ('vehicle_number','user__username')

@admin.register(VehicleLog)
class VehicleLogAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number','slot','entry_ts','exit_ts','booking')
    search_fields = ('vehicle_number',)

@admin.register(SensorEvent)
class SensorEventAdmin(admin.ModelAdmin):
    list_display = ('slot','sensor_type','value','ts')
    list_filter = ('sensor_type',)
