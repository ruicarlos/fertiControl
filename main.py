"""
from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np

# Carrega o modelo treinado
modelo = joblib.load("modelo_dosagem.pkl")

# Define o app
app = FastAPI(title="API de Validação FertiControl IA - Deway")

class FertilizanteInput(BaseModel):
    N: int
    P: int
    K: int
    volume: float

# Rota principal de predição
@app.post("/prever_dosagem")
def prever_dosagem(dados: FertilizanteInput):
    entrada = np.array([[dados.N, dados.P, dados.K, dados.volume]])
    pred = modelo.predict(entrada)[0]
    return {
        "amonia (g)": round(pred[0], 2),
        "fosfato (g)": round(pred[1], 2),
        "potassio (g)": round(pred[2], 2)
    }
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np

from auth import autenticar_usuario, get_db
from schemas import UsuarioLogin
from sqlalchemy.orm import Session

# Carrega o modelo treinado
modelo = joblib.load("modelo_dosagem.pkl")

# Define o app
app = FastAPI(title="API de Validação FertiControl IA - Deway")

# Modelo de entrada
class FertilizanteInput(BaseModel):
    N: int
    P: int
    K: int
    volume: float

# Login
@app.post("/login")
def login(dados: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = autenticar_usuario(dados.username, dados.senha, db)
    return {"mensagem": f"Usuário {usuario.username} autenticado com sucesso."}

# Rota protegida
@app.post("/prever_dosagem")
def prever_dosagem(
    dados: FertilizanteInput,
    usuario: UsuarioLogin = Depends(),  # Para fins simples, usamos o mesmo modelo
    db: Session = Depends(get_db)
):
    # Verifica credenciais antes da predição
    autenticar_usuario(usuario.username, usuario.senha, db)

    entrada = np.array([[dados.N, dados.P, dados.K, dados.volume]])
    pred = modelo.predict(entrada)[0]
    return {
        "amonia (g)": round(pred[0], 2),
        "fosfato (g)": round(pred[1], 2),
        "potassio (g)": round(pred[2], 2)
    }
