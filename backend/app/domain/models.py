from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base # Import Base yang asli
import sqlalchemy as sa
from datetime import datetime

# 1. Tabel Users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True) # Tambahkan email sesuai ERD
    hashed_password = Column(String)
    is_admin = Column(sa.Boolean, default=False)
    
    # Relasi
    devices = relationship("Device", back_populates="owner")
    predictions = relationship("Prediction", back_populates="user")

# 2. Tabel Devices
class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_name = Column(String)
    
    # Relasi
    owner = relationship("User", back_populates="devices")
    logs = relationship("SensorLog", back_populates="device")
    features = relationship("UserFeature", back_populates="device")

# 3. Tabel Sensor_Logs
class SensorLog(Base):
    __tablename__ = "sensor_logs"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id")) # FK ke devices, bukan users langsung
    temperature = Column(Float)
    humidity = Column(Float)
    mq_value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device", back_populates="logs")

# 4. Tabel User_Features (Untuk data yang sudah di-preprocess)
class UserFeature(Base):
    __tablename__ = "user_features"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    date = Column(Date)
    mq_lag_24h = Column(Float)
    mq_mean_24h = Column(Float)
    is_weekend = Column(Integer)
    hour = Column(Integer)
    # Tambahkan fitur lainnya di sini sesuai list kamu (mq_std, global_slope, dll)
    
    device = relationship("Device", back_populates="features")

# 5. Tabel Predictions
class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    predicted_label = Column(String)
    target_date = Column(Date)
    confidence = Column(Float)
    
    user = relationship("User", back_populates="predictions")