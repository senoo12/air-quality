import sys
import os
from datetime import datetime, timedelta
import random

# Fix Path agar bisa import app
sys.path.append(os.getcwd())

from app.infrastructure.database import SessionLocal
from app.use_cases.sensor_service import SensorService
from app.domain import models

def seed_complete_data():
    db = SessionLocal()
    # Panggil Service agar logic ML (save_prediction) ikut jalan
    service = SensorService(db)
    
    device_id = 1
    user_id = 2
    
    print(f"🏗️  Memulai Smart Seeding untuk User {user_id}...")

    try:
        # 1. Masukkan 24 data sensor ke masa lalu
        now = datetime.utcnow()
        for i in range(24, 0, -1):
            timestamp = now - timedelta(hours=i)
            new_log = models.SensorLog(
                device_id=device_id,
                temperature=round(random.uniform(28, 33), 2),
                humidity=round(random.uniform(50, 70), 2),
                mq_value=round(random.uniform(100, 200), 2),
                timestamp=timestamp
            )
            db.add(new_log)
        
        db.commit()
        print("✅ 24 Data Sensor berhasil masuk.")

        # 2. TRIGGER PREDIKSI (Simulasi memanggil logic ML)
        print("🧠 Menjalankan logic Machine Learning...")
        
        # Jalankan TSC (Status Saat Ini) untuk data terakhir
        latest_log = db.query(models.SensorLog).filter_by(device_id=device_id).order_by(models.SensorLog.id.desc()).first()
        service.predict_tsc_single_point(user_id, latest_log)
        
        # Jalankan Forecasting (Prediksi Besok)
        service.predict_next_day(user_id, device_id)
        
        print("✅ Tabel 'predictions' berhasil terisi hasil ML!")

    except Exception as e:
        print(f"❌ Gagal: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_complete_data()