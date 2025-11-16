from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ParkingSlot, SlotStatus, Booking, VehicleLog, SensorEvent

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username','email','first_name','last_name']

class ParkingSlotSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    class Meta:
        model = ParkingSlot
        fields = ['id','label','zone','max_vehicle_type','is_active','status']

    def get_status(self, obj):
        try:
            return obj.status.status
        except:
            return 'free'

class SlotStatusSerializer(serializers.ModelSerializer):
    slot = ParkingSlotSerializer(read_only=True)
    class Meta:
        model = SlotStatus
        fields = ['id','slot','status','last_update']

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    slot_label = serializers.CharField(source='slot.label', read_only=True)
    class Meta:
        model = Booking
        fields = ['id','user','slot','slot_label','vehicle_number','eta','reserved_from','reserved_until','status','created_at']
        read_only_fields = ['user','created_at','reserved_from','reserved_until','status','slot']

class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['vehicle_number','eta','slot']  # slot optional; allocation logic in view

class VehicleLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleLog
        fields = ['id','vehicle_number','slot','entry_ts','exit_ts','booking','plate_image','ocr_text']

class SensorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorEvent
        fields = ['id','slot','sensor_type','value','ts']
