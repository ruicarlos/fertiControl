# criar_usuario.py

from models import Usuario
from database import SessionLocal
from passlib.context import CryptContext

# Criptografia da senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Inicia sessão com o banco
db = SessionLocal()

# Cria um novo usuário
novo_usuario = Usuario(
    username="admin",
    senha_hash=pwd_context.hash("senha123")
)

# Adiciona ao banco e salva
db.add(novo_usuario)
db.commit()
db.close()

print("✅ Usuário criado com sucesso!")
