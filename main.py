from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List
import uuid

app = FastAPI()

# --- In-Memory Storage ---
# We will use a dictionary to store bookings by room_id for quicker lookups.
bookings_db = {}

# --- Data Models ---
class BookingRequest(BaseModel):
    room_id: str
    start_time: datetime
    end_time: datetime

class Booking(BookingRequest):
    booking_id: str

# --- Helper Functions ---

def is_overlapping(room_id: str, start: datetime, end: datetime) -> bool:
    """Checks if the requested time slot overlaps with existing bookings for the room."""
    room_bookings = bookings_db.get(room_id, [])
    for booking in room_bookings:
        if max(start, booking.start_time) < min(end, booking.end_time):
            return True
    return False

# --- Endpoints ---

@app.post("/bookings/", response_model=Booking)
def create_booking(booking: BookingRequest):
    """
    Creates a new booking. 
    Validates: Start < End, No Past Bookings, No Overlaps.
    """
    now = datetime.now(timezone.utc)

    if booking.start_time >= booking.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time.")

    if booking.start_time < now:
        raise HTTPException(status_code=400, detail="Cannot create bookings in the past.")

    # Rule: Bookings cannot overlap for the same room
    if is_overlapping(booking.room_id, booking.start_time, booking.end_time):
        raise HTTPException(status_code=409, detail="Time slot already booked for this room.")

    # Create the booking object
    new_booking = Booking(
        booking_id=str(uuid.uuid4()), # Generate a unique ID
        room_id=booking.room_id,
        start_time=booking.start_time,
        end_time=booking.end_time
    )

    # Store the booking in the dictionary
    if booking.room_id not in bookings_db:
        bookings_db[booking.room_id] = []
    
    bookings_db[booking.room_id].append(new_booking)
    return new_booking

@app.get("/bookings/{room_id}", response_model=List[Booking])
def view_bookings(room_id: str):
    """
    List all bookings for a specific room.
    """
    room_bookings = bookings_db.get(room_id, [])
    return room_bookings

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    """
    Remove an existing booking by ID.
    """
    booking = next((b for b in [booking for room in bookings_db.values() for booking in room] if b.booking_id == booking_id), None)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    
    # Remove the booking
    for room_bookings in bookings_db.values():
        room_bookings.remove(booking)

    return {"message": "Booking canceled successfully."}

