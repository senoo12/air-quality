import joblib
import pandas as pd
import numpy as np
import os
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.infrastructure.repositories import SensorRepository, DeviceRepository, PredictionRepository

class SensorService:
    def __init__(self, db: Session):
        self.db = db
        self.sensor_repo = SensorRepository(db)
        self.device_repo = DeviceRepository(db)
        self.pred_repo = PredictionRepository(db)
        
        # Path dinamis ke folder model
        BASE_DIR = Path(__file__).resolve().parents[3]
        self.tsc_model = joblib.load(BASE_DIR / "model" / "xgb_tsc_model.joblib")
        self.forecast_model = joblib.load(BASE_DIR / "model" / "xgb_forecasting_model.joblib")

    def log_data(self, user_id: int, device_id: int, temp: float, hum: float, mq: float):
        # 1. Validasi Device
        device = self.device_repo.get_device_by_id(device_id)
        if not device or device.user_id != user_id:
            return {"status": "error", "message": "Unauthorized device"}
        
        # 2. Simpan log sensor ke database
        log = self.sensor_repo.create_log(device_id, temp, hum, mq)

        # 3. Prediksi Langsung dari 1 data log yang baru disimpan
        self.predict_tsc_single_point(user_id, log)

        return log

    def get_history_by_device(self, user_id: int, device_id: int, limit: int = 50):
        """Mengambil data history sensor dengan validasi kepemilikan device"""
        # 1. Validasi: Pastikan device ini milik user yang request
        device = self.device_repo.get_device_by_id(device_id)
        if not device or device.user_id != user_id:
            # Jika user is_admin, kita beri akses (opsional, tapi bagus buat admin)
            # user_repo = UserRepository(self.db)
            # requester = user_repo.get_by_id(user_id)
            # if not requester.is_admin:
            return [] # Atau raise HTTPException 403

        # 2. Ambil data dari repository
        return self.sensor_repo.get_device_history(device_id, limit)

    def predict_tsc_single_point(self, user_id: int, log):
        """Prediksi menggunakan hanya 1 data poin terbaru"""
        now = datetime.now()
        
        # Karena hanya 1 data, fitur variasi/statistik diset ke 0 atau nilai statis
        features = {
            "temperature": log.temperature,
            "humidity": log.humidity,
            "hour": now.hour,
            "is_weekend": 1 if now.weekday() >= 5 else 0,
            "mq_mean": log.mq_value,      # Mean dari 1 data = data itu sendiri
            "mq_std": 0.0,                # Tidak ada variasi
            "mq_q75": log.mq_value,
            "global_slope": 0.0,          # Tidak ada kemiringan
            "mq_delta": 0.0,
            "acceleration": 0.0,
            "mq_cv": 0.0,
            "crossing_rate": 0.0,
            "mq_range": 0.0,
            "mq_temp_ratio": log.mq_value / (log.temperature + 0.1),
            "mq_hum_ratio": log.mq_value / (log.humidity + 0.1)
        }
        
        # Buat DataFrame dengan urutan kolom yang sama saat training
        df = pd.DataFrame([features])
        
        try:
            label_idx = self.tsc_model.predict(df)[0]
            labels = ["bad", "moderate", "good"]
            current_label = labels[label_idx]
            
            # UPDATE DI SINI: Tambahkan log.device_id
            self.pred_repo.save_prediction(
                user_id=user_id, 
                device_id=log.device_id, # Kirim ID alatnya
                label=current_label, 
                target_date=datetime.now().date(), 
                conf=0.99
            )
            print(f"DEBUG: Prediksi Berhasil (Single Point): {current_label}")
        except Exception as e:
            print(f"DEBUG: Gagal Prediksi - {e}")

    def _extract_basic_features(self, history):
        """Helper untuk ekstraksi fitur statistik dari history"""
        latest = history[0]
        now = datetime.now()
        mq_values = np.array([h.mq_value for h in history])
        
        return {
            "temperature": latest.temperature,
            "humidity": latest.humidity,
            "hour": now.hour,
            "is_weekend": 1 if now.weekday() >= 5 else 0,
            "mq_values": mq_values,
            "latest": latest
        }

    def predict_next_day(self, user_id: int, device_id: int):
        """Model Forecasting: Prediksi kondisi untuk BESOK"""
        # Ambil history 48 log terakhir untuk hitung fitur lag & mean
        history = self.sensor_repo.get_device_history(device_id, limit=48)
        if len(history) < 24:
            return {"status": "error", "message": "Data 24 jam terakhir belum lengkap"}

        base = self._extract_basic_features(history)
        mqs = base["mq_values"][:24] # Jendela 24 jam terakhir
        
        # Feature Engineering sesuai spesifikasi model Forecasting kamu
        features = {
            "temperature": base["temperature"],
            "humidity": base["humidity"],
            "hour": base["hour"],
            "is_weekend": base["is_weekend"],
            "mq_lag_24h": history[23].mq_value,
            "mq_mean_24h": np.mean(mqs),
            "mq_std_24h": np.std(mqs),
            "mq_range_24h": np.ptp(mqs),
            "daily_slope": (mqs[0] - mqs[-1]) / 24,
            "crossing_rate_24h": ((np.diff(mqs > np.mean(mqs)) != 0).sum()) / 24
        }
        
        df = pd.DataFrame([features])
    
        # Ambil hasil prediksi
        raw_prediction = self.forecast_model.predict(df)[0]
        label_idx = int(raw_prediction)
        
        # DEBUG: Cek angka yang keluar dari model di terminal
        print(f"DEBUG: Forecasting Model Output Index -> {label_idx}")

        # Urutan Alphabetical LabelEncoder: [0: bad, 1: good, 2: moderate]
        labels = ["bad", "good", "moderate"] 
        
        # PROTEKSI: Cek apakah index masuk dalam range list
        if 0 <= label_idx < len(labels):
            prediction_label = labels[label_idx]
        else:
            print(f"WARNING: Model menebak index {label_idx} yang tidak terdaftar!")
            prediction_label = "moderate"
        
        # Simpan hasil prediksi besok ke database
        target_date = (datetime.now() + timedelta(days=1)).date()
        self.pred_repo.save_prediction(
            user_id=user_id, 
            device_id=device_id, 
            label=prediction_label, 
            target_date=target_date, 
            conf=0.90
        )

        return {
            "prediction": prediction_label,
            "target_date": target_date
        }