from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from typing import List, Optional

# --- Auth Schemas ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr # Sesuai ERD terbaru
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool

    class Config:
        from_attributes = True

# --- Device Schemas ---
class DeviceCreate(BaseModel):
    device_name: str

class DeviceResponse(DeviceCreate):
    id: int
    user_id: int
    class Config:
        from_attributes = True

# --- Sensor Schemas ---
class SensorLogCreate(BaseModel):
    device_id: int # Wajib dikirim oleh ESP32
    temperature: float
    humidity: float
    mq_value: float

class SensorLogResponse(BaseModel):
    id: int
    device_id: int
    temperature: float
    humidity: float
    mq_value: float
    timestamp: datetime
    class Config:
        from_attributes = True

# --- Prediction Schemas ---
class PredictionCreate(BaseModel):
    user_id: int
    predicted_label: str 
    target_date: date    
    confidence: float   

class PredictionResponse(BaseModel):
    id: int
    user_id: int
    device_id: Optional[int] = None # Buat jadi opsional dengan default None
    predicted_label: str
    target_date: date
    confidence: float
    
    class Config:
        from_attributes = True