# schemas.py
from pydantic import BaseModel

class UsuarioLogin(BaseModel):
    username: str
    senha: str
