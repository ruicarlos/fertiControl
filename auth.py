# auth.py
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from models import Usuario
from passlib.context import CryptContext
from database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def autenticar_usuario(username: str, senha: str, db: Session):
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if not usuario or not pwd_context.verify(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return usuario
