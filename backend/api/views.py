import os
import io
import json
from datetime import timedelta, datetime
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile

from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from .models import ParkingSlot, SlotStatus, Booking, VehicleLog, SensorEvent
from .serializers import (ParkingSlotSerializer, SlotStatusSerializer,
                          BookingSerializer, BookingCreateSerializer,
                          VehicleLogSerializer, SensorEventSerializer, UserSerializer)
from django.contrib.auth.models import User

# ---- Simple Auth endpoints (session-based)
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return Response(UserSerializer(user).data)
        return Response({'detail':'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail':'Logged out'})

# ---- Slots
class SlotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ParkingSlot.objects.all().order_by('label')
    serializer_class = ParkingSlotSerializer
    permission_classes = [permissions.AllowAny]

# ---- Bookings
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer

    def get_permissions(self):
        if self.action in ['create','list','retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        user = self.request.user
        vehicle = serializer.validated_data.get('vehicle_number')
        eta = serializer.validated_data.get('eta')

        # allocation logic: find first free slot (status.free) and reserve it
        slotstatus = SlotStatus.objects.filter(status='free').select_related('slot').first()
        if not slotstatus:
            raise serializers.ValidationError({'detail':'No free slots available'})

        slot = slotstatus.slot
        # mark reserved
        slotstatus.status = 'reserved'
        now = timezone.now()
        slotstatus.save()
        # reserved_from = eta - 10 minutes (or now)
        reserved_from = eta - timedelta(minutes=15) if eta else now
        reserved_until = eta + timedelta(minutes=15) if eta else now + timedelta(minutes=30)
        booking = Booking.objects.create(user=user, slot=slot, vehicle_number=vehicle,
                                         eta=eta, reserved_from=reserved_from,
                                         reserved_until=reserved_until)
        return booking

    def list(self, request, *args, **kwargs):
        qs = Booking.objects.filter(user=request.user).order_by('-created_at')
        serializer = BookingSerializer(qs, many=True)
        return Response(serializer.data)

# ---- Sensor ingestion with debounce logic
# simple device token validation
SENSOR_DEVICE_TOKEN = getattr(settings, 'SENSOR_DEVICE_TOKEN', 'DEVKEY12345')
OCCUPIED_THRESHOLD_CM = getattr(settings, 'OCCUPIED_THRESHOLD_CM', 40)  # <40cm => occupied

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def sensor_event(request):
    # require a header x-device-key
    token = request.headers.get('x-device-key') or request.data.get('device_key')
    if token != SENSOR_DEVICE_TOKEN:
        return Response({'detail':'invalid device token'}, status=401)

    slot_id = request.data.get('slot_id')
    sensor_type = request.data.get('sensor_type', 'ultrasonic')
    value = request.data.get('value')
    if slot_id is None or value is None:
        return Response({'detail':'slot_id and value required'}, status=400)

    try:
        slot = ParkingSlot.objects.get(pk=slot_id)
    except ParkingSlot.DoesNotExist:
        return Response({'detail':'slot not found'}, status=404)

    # save sensor event
    SensorEvent.objects.create(slot=slot, sensor_type=sensor_type, value=float(value))

    # debounce logic: check last N events
    last_events = SensorEvent.objects.filter(slot=slot, sensor_type=sensor_type).order_by('-ts')[:5]
    occupied_count = sum(1 for e in last_events if float(e.value) < OCCUPIED_THRESHOLD_CM)
    status_to_set = 'occupied' if occupied_count >= 3 else 'free'
    # If there's an active reservation overlapping now and vehicle is approaching, might remain reserved
    ss, _ = SlotStatus.objects.get_or_create(slot=slot)
    if ss.status != status_to_set:
        ss.status = status_to_set
        ss.save()
    return Response({'status': ss.status})

# ---- OCR upload endpoint (accepts multipart/form-data file)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def ocr_plate(request):
    # accepts 'image' file
    f = request.FILES.get('image')
    if f is None:
        return Response({'detail':'image file required'}, status=400)
    # save temporarily
    folder = os.path.join(settings.MEDIA_ROOT, 'plates')
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{int(timezone.now().timestamp())}_{f.name}")
    with open(file_path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)
    # attempt OCR
    from .utils.ocr_utils import extract_plate_text
    plate = extract_plate_text(file_path)
    # return plate and stored path
    rel_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
    return Response({'plate_text': plate, 'plate_image': f"/media/{rel_path}"})

# ---- Vehicle entry/exit endpoints
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def vehicle_entry(request):
    """
    called when camera captures plate at entry or when system wants to record entry
    expects: image (optional), slot_id (optional), ts (optional)
    """
    image = request.FILES.get('image')
    slot_id = request.data.get('slot_id')
    ts = request.data.get('ts')  # optional ISO
    plate_text = request.data.get('plate_text')

    stored_path = None
    if image:
        folder = os.path.join(settings.MEDIA_ROOT, 'plates')
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, f"{int(timezone.now().timestamp())}_{image.name}")
        with open(file_path, 'wb') as out:
            for chunk in image.chunks():
                out.write(chunk)
        stored_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
        if not plate_text:
            from .utils.ocr_utils import extract_plate_text
            plate_text = extract_plate_text(file_path)

    # create vehicle log entry
    booking = None
    matched_booking = None
    if plate_text:
        # find active booking for this vehicle
        matched_booking = Booking.objects.filter(vehicle_number__icontains=plate_text, status='active').order_by('-created_at').first()
        booking = matched_booking

    slot = None
    if slot_id:
        try:
            slot = ParkingSlot.objects.get(pk=slot_id)
        except ParkingSlot.DoesNotExist:
            slot = None

    entry_ts = timezone.now() if not ts else timezone.make_aware(datetime.fromisoformat(ts))
    vl = VehicleLog.objects.create(vehicle_number=plate_text or 'UNKNOWN', slot=slot, entry_ts=entry_ts, booking=booking, plate_image=f"plates/{os.path.basename(stored_path)}" if stored_path else None, ocr_text=plate_text)
    # if booking exists, mark slot as occupied
    if booking:
        booking.status = 'active'
        booking.save()
        if booking.slot:
            ss, _ = SlotStatus.objects.get_or_create(slot=booking.slot)
            ss.status = 'occupied'
            ss.save()
    return Response(VehicleLogSerializer(vl).data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def vehicle_exit(request):
    """
    Called when vehicle leaves: expects plate_text or vehicle_log id
    """
    plate_text = request.data.get('plate_text')
    vl_id = request.data.get('vehicle_log_id')
    exit_ts = request.data.get('ts')
    if vl_id:
        try:
            vl = VehicleLog.objects.get(pk=vl_id)
        except VehicleLog.DoesNotExist:
            return Response({'detail':'vehicle log not found'}, status=404)
    elif plate_text:
        vl = VehicleLog.objects.filter(vehicle_number__icontains=plate_text).order_by('-entry_ts').first()
        if not vl:
            return Response({'detail':'vehicle log not found'}, status=404)
    else:
        return Response({'detail':'vehicle_log_id or plate_text required'}, status=400)

    vl.exit_ts = timezone.now() if not exit_ts else timezone.make_aware(datetime.fromisoformat(exit_ts))
    vl.save()
    # free the slot if it was occupied
    if vl.slot:
        ss, _ = SlotStatus.objects.get_or_create(slot=vl.slot)
        ss.status = 'free'
        ss.save()
    # if booking linked, mark completed
    if vl.booking:
        vl.booking.status = 'completed'
        vl.booking.save()
    return Response(VehicleLogSerializer(vl).data)
