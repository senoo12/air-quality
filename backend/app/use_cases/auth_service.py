from sqlalchemy.orm import Session
from app.infrastructure.repositories import UserRepository
from app.infrastructure.security import verify_password, create_access_token, get_password_hash
from fastapi import HTTPException, status

class AuthService:
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
        self.user_repo = self.repository # Alias untuk konsistensi dengan kode lain yang sudah ada

    # Tambahkan parameter email di sini agar sesuai dengan ERD dan endpoint kamu
    def register_user(self, username: str, password: str, email: str):
        # Validasi apakah username sudah ada
        if self.repository.get_by_username(username):
            raise HTTPException(status_code=400, detail="Username sudah terdaftar")
        
        # Validasi apakah email sudah ada (Sesuai ERD baru)
        if self.repository.get_by_email(email):
            raise HTTPException(status_code=400, detail="Email sudah terdaftar")
        
        hashed = get_password_hash(password)
        
        # Pastikan repository.create juga menerima email (sudah kita perbarui tadi)
        return self.repository.create(username=username, hashed_password=hashed, email=email)

    def authenticate_user(self, username: str, password: str):
        user = self.repository.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Buat token JWT dengan payload sub (username) dan id
        access_token = create_access_token(data={
            "sub": user.username, 
            "id": user.id,
            "is_admin": user.is_admin  # <--- WAJIB ADA INI
        })
        return {"access_token": access_token, "token_type": "bearer"}
    
    def verify_user(self, username, password):
        """Fungsi untuk mengecek kredensial login"""
        # Sekarang self.user_repo sudah terdefinisi
        user = self.user_repo.get_by_username(username)
        if not user:
            return None
        
        # Verifikasi password (plain vs hashed)
        if not verify_password(password, user.hashed_password):
            return None
            
        return user