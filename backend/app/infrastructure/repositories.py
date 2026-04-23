from sqlalchemy.orm import Session
from app.domain import models
from datetime import date

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str):
        return self.db.query(models.User).filter(models.User.username == username).first()

    # --- TAMBAHKAN INI (Pastikan Indentasinya Sama) ---
    def get_all_users(self):
        return self.db.query(models.User).all()
    # ------------------------------------------------

    def get_by_email(self, email: str):
        return self.db.query(models.User).filter(models.User.email == email).first()

    def create(self, username: str, hashed_password: str, email: str):
        db_user = models.User(
            username=username, 
            hashed_password=hashed_password, 
            email=email
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def admin_assign_device(self, user_id: int, device_name: str): # Ganti device_id jadi device_name
        device = models.Device(user_id=user_id, device_name=device_name)
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device) # Tambahkan refresh agar datanya update
        return device

class DeviceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_device(self, user_id: int, name: str):
        device = models.Device(user_id=user_id, device_name=name)
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_user_devices(self, user_id: int):
        return self.db.query(models.Device).filter(models.Device.user_id == user_id).all()

    def get_device_by_id(self, device_id: int):
        return self.db.query(models.Device).filter(models.Device.id == device_id).first()

class SensorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_log(self, device_id: int, temp: float, hum: float, mq: float):
        db_log = models.SensorLog(
            device_id=device_id, 
            temperature=temp, 
            humidity=hum, 
            mq_value=mq
        )
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return db_log

    def get_device_history(self, device_id: int, limit: int = 100):
        return self.db.query(models.SensorLog)\
            .filter(models.SensorLog.device_id == device_id)\
            .order_by(models.SensorLog.timestamp.desc())\
            .limit(limit).all()

class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_prediction(self, user_id: int, device_id: int, label: str, target_date: date, conf: float):
        pred = models.Prediction(
            user_id=user_id,
            device_id=device_id, # Masukkan ke sini
            predicted_label=label,
            target_date=target_date,
            confidence=conf
        )
        self.db.add(pred)
        self.db.commit()
        self.db.refresh(pred)
        return pred
    
    def get_latest_by_user(self, user_id: int):
        return self.db.query(models.Prediction)\
            .filter(models.Prediction.user_id == user_id)\
            .order_by(models.Prediction.id.desc())\
            .first()

