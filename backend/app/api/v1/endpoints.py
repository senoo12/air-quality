from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.infrastructure.repositories import UserRepository
from typing import List

from app.infrastructure.security import create_access_token, create_refresh_token
from app.domain import models
from app.infrastructure.database import get_db
from app.api.v1 import schemas
from app.use_cases.auth_service import AuthService
from app.use_cases.sensor_service import SensorService
from app.infrastructure.security import oauth2_scheme, decode_token
from app.infrastructure.repositories import DeviceRepository, PredictionRepository # Tambahkan ini

router = APIRouter()

# --- AUTH ENDPOINTS ---

@router.post("/register", response_model=dict)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    user = auth_service.register_user(user_data.username, user_data.password, user_data.email)
    return {"message": "User berhasil didaftarkan", "username": user.username}

@router.post("/token", response_model=dict) # Ubah response_model ke dict agar fleksibel
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    # Kita ambil user object untuk mendapatkan ID-nya
    user = auth_service.verify_user(form_data.username, form_data.password) 
    if not user:
        raise HTTPException(status_code=401, detail="Username atau password salah")

    # Generate dua jenis token
    access_token = create_access_token(data={"sub": user.username, "id": user.id})
    refresh_token = create_refresh_token(data={"sub": user.username, "id": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=dict)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    """Pintu masuk untuk menukar refresh token lama dengan access token baru"""
    try:
        # Gunakan decode_token yang sudah kamu buat
        payload = decode_token(refresh_token)
        username = payload.get("sub")
        user_id = payload.get("id")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Berikan Access Token baru (napas baru 2 menit)
        new_access_token = create_access_token(data={"sub": username, "id": user_id})
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token kadaluwarsa, silakan login ulang")

def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_info = decode_token(token) # Sekarang isinya full payload
    user_repo = UserRepository(db)
    
    # Ambil 'sub' karena di JWT payload standar, username ada di 'sub'
    username = user_info.get("sub") 
    user = user_repo.get_by_username(username)
    
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")

    print(f"DEBUG: User {user.username} - Admin Status di DB: {user.is_admin}")
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Akses ditolak! Anda bukan Administrator."
        )
    return user

@router.get("/users", response_model=List[schemas.UserResponse])
def list_all_users(
    admin: models.User = Depends(get_current_admin), 
    db: Session = Depends(get_db)
):
    user_repo = UserRepository(db)
    return user_repo.get_all_users()

# --- DEVICE ENDPOINTS ---
@router.post("/devices", response_model=schemas.DeviceResponse)
def create_device(
    device_data: schemas.DeviceCreate, 
    user_target_id: int,
    admin: models.User = Depends(get_current_admin), 
    db: Session = Depends(get_db)
):
    # Kita tidak butuh lagi decode_token(token) di sini 
    # karena 'admin' sudah didapat dari dependency get_current_admin
    
    device_repo = DeviceRepository(db)
    
    # Gunakan user_target_id agar device tertaut ke user yang dimaksud, bukan ke admin
    return device_repo.create_device(user_target_id, device_data.device_name)

@router.get("/devices", response_model=List[schemas.DeviceResponse])
def list_my_devices(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_info = decode_token(token)
    device_repo = DeviceRepository(db)
    return device_repo.get_user_devices(user_info['id'])

# --- SENSOR & PREDICTION ENDPOINTS ---

@router.post("/sensors/log", response_model=dict)
def log_sensor_data(
    data: schemas.SensorLogCreate, 
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    user_info = decode_token(token)
    sensor_service = SensorService(db)
    
    # Service sekarang menangani validasi apakah device_id tsb milik user_id tsb
    result = sensor_service.log_data(
        user_id=user_info.get("id"),
        device_id=data.device_id,
        temp=data.temperature,
        hum=data.humidity,
        mq=data.mq_value
    )
    
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=403, detail=result["message"])
        
    return {"status": "success", "log_id": result.id}

@router.get("/sensors/history/{device_id}", response_model=List[schemas.SensorLogResponse])
def get_device_history(
    device_id: int,
    limit: int = 50, 
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    user_info = decode_token(token)
    sensor_service = SensorService(db)
    # Tambahkan logika pengecekan akses di service agar user tak bisa intip device orang lain
    return sensor_service.get_history_by_device(user_info.get("id"), device_id, limit)

@router.post("/predictions", response_model=schemas.PredictionResponse)
def save_new_prediction(
    data: schemas.PredictionCreate,
    admin: models.User = Depends(get_current_admin), # Hanya admin/system yang bisa post
    db: Session = Depends(get_db)
):
    pred_repo = PredictionRepository(db)
    
    # Cek apakah sudah ada prediksi untuk user & tanggal tersebut
    # (Opsional: agar tidak ada double data di tanggal yang sama)
    
    new_prediction = pred_repo.save_prediction(
        user_id=data.user_id,
        label=data.predicted_label,
        target_date=data.target_date,
        conf=data.confidence
    )
    return new_prediction

@router.get("/sensors/predict/{device_id}", response_model=schemas.PredictionResponse)
def get_personalized_prediction(
    device_id: int,
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) :
    user_info = decode_token(token)
    sensor_service = SensorService(db)
    
    prediction = sensor_service.predict_next_day(user_info.get("id"), device_id)
    
    if isinstance(prediction, dict) and prediction.get("status") == "error":
        raise HTTPException(status_code=400, detail=prediction["message"])
        
    return prediction

@router.get("/predictions/latest", response_model=schemas.PredictionResponse)
def get_latest_status(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    user_info = decode_token(token)
    pred_repo = PredictionRepository(db)
    latest = pred_repo.get_latest_by_user(user_info.get("id"))
    
    if not latest:
        raise HTTPException(status_code=404, detail="Belum ada data prediksi")
    return latest