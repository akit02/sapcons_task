from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import uuid
from datetime import datetime, timezone

app = FastAPI()

# --- In-Memory Storage ---
# We will use a simple list to store booking objects.
bookings_db = []

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
    for booking in bookings_db:
        if booking.room_id == room_id:
            # Overlap logic: (StartA <= EndB) and (EndA >= StartB)
            # Generally: max(start1, start2) < min(end1, end2)
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

    bookings_db.append(new_booking)
    return new_booking

@app.get("/bookings/{room_id}", response_model=List[Booking])
def view_bookings(room_id: str):
    """
    List all bookings for a specific room.
    """
    room_bookings = [b for b in bookings_db if b.room_id == room_id]
    return room_bookings

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    """
    Remove an existing booking by ID.
    """
    global bookings_db
    # Filter out the booking with the matching ID
    original_count = len(bookings_db)
    bookings_db = [b for b in bookings_db if b.booking_id != booking_id]
    
    if len(bookings_db) == original_count:
        raise HTTPException(status_code=404, detail="Booking not found.")
        
    return {"message": "Booking canceled successfully."}
