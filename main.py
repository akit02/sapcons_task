from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Dict, Optional
import uuid

app = FastAPI(title="Meeting Room Booking API")

# --- Models ---

class BookingRequest(BaseModel):
    room_id: str = Field(..., example="conference-room-1")
    start_time: datetime
    end_time: datetime

class Booking(BookingRequest):
    booking_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# --- Logic Manager ---

class BookingManager:
    """Handles the business logic and in-memory storage."""
    
    def __init__(self):
        # Room ID maps to a List of Booking objects
        self._storage: Dict[str, List[Booking]] = {}

    def check_overlap(self, room_id: str, start: datetime, end: datetime) -> bool:
        """
        Logic: Two intervals overlap if Max(Starts) < Min(Ends).
        """
        for existing in self._storage.get(room_id, []):
            if max(start, existing.start_time) < min(end, existing.end_time):
                return True
        return False

    def add_booking(self, request: BookingRequest) -> Booking:
        # 1. Basic Time Validation
        if request.start_time >= request.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Start time must be before end time."
            )

        # 2. Past Date Validation
        if request.start_time < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Cannot book in the past."
            )

        # 3. Overlap Validation
        if self.check_overlap(request.room_id, request.start_time, request.end_time):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Room is already booked for this time slot."
            )

        # 4. Storage
        new_booking = Booking(**request.model_dump())
        if request.room_id not in self._storage:
            self._storage[request.room_id] = []
        
        self._storage[request.room_id].append(new_booking)
        return new_booking

    def get_room_bookings(self, room_id: str) -> List[Booking]:
        return self._storage.get(room_id, [])

    def delete_booking(self, booking_id: str) -> bool:
        for room_id, bookings in self._storage.items():
            for b in bookings:
                if b.booking_id == booking_id:
                    bookings.remove(b)
                    return True
        return False

# Initialize the manager
manager = BookingManager()

# --- Endpoints ---

@app.post("/bookings", response_model=Booking, status_code=status.HTTP_201_CREATED)
def create_booking(booking_data: BookingRequest):
    """Create a new reservation for a specific room."""
    return manager.add_booking(booking_data)

@app.get("/bookings/{room_id}", response_model=List[Booking])
def list_bookings(room_id: str):
    """Retrieve all bookings for a specific room."""
    return manager.get_room_bookings(room_id)

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    """Delete a booking using its unique ID."""
    success = manager.delete_booking(booking_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Booking ID not found."
        )
    return {"message": "Booking successfully cancelled."}
