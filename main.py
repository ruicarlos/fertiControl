from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np

# Carrega o modelo treinado
modelo = joblib.load("modelo_dosagem.pkl")

# Define o app
app = FastAPI(title="API de Validação FertiControl IA - Deway")

# Define os dados esperados
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
