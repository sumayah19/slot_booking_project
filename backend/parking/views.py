from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Slot, Booking, Gate
from .serializers import SlotSerializer, BookingSerializer
from django.utils import timezone

@api_view(['GET'])
def slots_list(request):
    slots = Slot.objects.all()
    return Response(SlotSerializer(slots, many=True).data)

@api_view(['POST'])
def create_booking(request):
    slot_id = request.data.get('slot')
    eta = request.data.get('eta')  # ISO datetimestamp string
    vehicle_no = request.data.get('vehicle_no','')
    if not slot_id or not eta:
        return Response({"detail":"slot and eta required"}, status=400)

    with transaction.atomic():
        slot = Slot.objects.select_for_update().get(pk=slot_id)
        if slot.is_occupied:
            return Response({"detail":"slot occupied"}, status=409)
        slot.is_occupied = True
        slot.save()
        booking = Booking.objects.create(slot=slot, eta=eta, vehicle_no=vehicle_no, status='reserved')
    return Response(BookingSerializer(booking).data, status=201)

@api_view(['POST'])
def sensor_update(request, pk):
    """
    Simulated sensor update: { "distance": 6.5 }
    """
    dist = request.data.get('distance')
    if dist is None:
        return Response({"detail":"distance needed"}, status=400)
    slot = get_object_or_404(Slot, pk=pk)
    threshold = 10.0
    slot.is_occupied = float(dist) < threshold
    slot.save()
    return Response({"slot":slot.id,"is_occupied":slot.is_occupied})

@api_view(['POST'])
def mark_arrived(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    booking.status = 'arrived'
    booking.save()
    # optionally open gate
    gate, _ = Gate.objects.get_or_create(pk=1)
    gate.status = 'open'
    gate.save()
    return Response({"ok":True,"booking":BookingSerializer(booking).data})
