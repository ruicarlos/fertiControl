# main.py

# ⚠️ AVISO DE SEGURANÇA: Esta implementação não valida o usuário em cada
# endpoint. Dados podem ser acessados ou criados para qualquer empresa se o
# 'empresa_id' for conhecido. Considere adicionar uma camada de segurança (ex: token)
# em um ambiente de produção.

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import joblib
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from auth import autenticar_usuario, get_db
from models import Usuario, Empresa, Producao, Fertilizante, Sensor, Rastreio, Laudo
from schemas import (
    UsuarioLogin, UsuarioOut, EmpresaCreate, EmpresaOut, EmpresaUpdate, ProducaoCreate,
    ProducaoOut, FertilizanteCreate, FertilizanteOut, SensorCreate, SensorOut,
    RastreioCreate, RastreioOut, LaudoCreate, LaudoOut
)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Autenticação e Empresa ---

@app.post("/login", response_model=UsuarioOut)
def login(dados: UsuarioLogin, db: Session = Depends(get_db)):
    """
    Autentica o usuário e retorna seus dados, incluindo o ID da empresa.
    """
    usuario = autenticar_usuario(dados.username, dados.senha, db)
    return usuario

@app.post("/empresas", response_model=EmpresaOut)
def criar_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    # ... (código mantido, já está correto)
    usuario_existente = db.query(Usuario).filter(Usuario.username == empresa.responsavel_email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="O e-mail do responsável já está em uso.")
    db_empresa = Empresa(**empresa.dict())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    novo_usuario = Usuario(
        username=empresa.responsavel_email,
        name=empresa.responsavel_nome,
        senha_hash='$2b$12$RnK.cn1LVyaqrbCnfhaUw.1l7FRHRTD8LotahOUYPTvzyA7VZz8Pe',
        role='client',
        empresa=db_empresa.id
    )
    db.add(novo_usuario)
    db.commit()
    return db_empresa

@app.get("/empresas", response_model=List[EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    # Esta rota geralmente é para administradores, então mantemos sem filtro.
    return db.query(Empresa).all()


@app.get("/empresas/{empresa_id}", response_model=EmpresaOut)
def obter_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """
    Obtém os detalhes de uma empresa específica pelo seu ID.
    """
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa
# --- Predição ---

@app.post("/prever_dosagem")
def prever_dosagem(dados: FertilizanteInput, db: Session = Depends(get_db)):
    # A autenticação insegura foi removida. Esta rota agora é pública.
    entrada = np.array([[dados.N, dados.P, dados.K, dados.volume]])
    pred = modelo.predict(entrada)[0]
    return {
        "amonia (g)": round(pred[0], 2),
        "fosfato (g)": round(pred[1], 2),
        "potassio (g)": round(pred[2], 2)
    }

# --- Produção ---

@app.get("/producao", response_model=List[ProducaoOut])
def listar_producoes(empresa_id: int, db: Session = Depends(get_db)):
    """Lista todas as produções de uma empresa específica."""
    return db.query(Producao).filter(Producao.empresa == empresa_id).all()

@app.post("/producao", response_model=ProducaoOut)
def criar_producao(producao: ProducaoCreate, db: Session = Depends(get_db)):
    """Cria uma nova produção (o 'empresa_id' deve vir no corpo da requisição)."""
    db_producao = Producao(**producao.dict())
    db.add(db_producao)
    db.commit()
    db.refresh(db_producao)
    return db_producao

@app.get("/producao/soma_volume_a_produzir", response_model=float)
def soma_producao_produzir(empresa_id: int, db: Session = Depends(get_db)):
    """Soma o volume a produzir para uma empresa específica."""
    soma = db.query(func.coalesce(func.sum(Producao.volume), 0.0))\
             .filter(Producao.status == "Produzir", Producao.empresa == empresa_id)\
             .scalar()
    return soma

@app.get("/producao-semanal")
def producao_semanal(empresa_id: int, db: Session = Depends(get_db)):
    """Retorna a produção semanal para uma empresa específica."""
    resultados = (
        db.query(
            func.dayname(Producao.data).label("dia_semana"),
            func.sum(Producao.volume).label("total_volume")
        )
        .filter(Producao.empresa == empresa_id)
        .group_by(func.dayname(Producao.data))
        .all()
    )
    return [{"dia_semana": r.dia_semana, "total_volume": float(r.total_volume or 0)} for r in resultados]

# --- Fertilizante ---

@app.get("/fertilizante", response_model=List[FertilizanteOut])
def listar_fertilizantes(empresa_id: int, db: Session = Depends(get_db)):
    """Lista os fertilizantes de uma empresa específica."""
    return db.query(Fertilizante).filter(Fertilizante.empresa == empresa_id).all()

@app.post("/fertilizante", response_model=FertilizanteOut)
def criar_tipo_fertilizante(fertilizante: FertilizanteCreate, db: Session = Depends(get_db)):
    """Cria um novo fertilizante (o 'empresa_id' deve vir no corpo da requisição)."""
    db_fertilizante = Fertilizante(**fertilizante.dict())
    db.add(db_fertilizante)
    db.commit()
    db.refresh(db_fertilizante)
    return db_fertilizante

# --- Sensor ---

@app.get("/sensor", response_model=List[SensorOut])
def listar_sensores(empresa_id: int, db: Session = Depends(get_db)):
    """Lista os sensores de uma empresa específica."""
    return db.query(Sensor).filter(Sensor.empresa == empresa_id).all()

@app.post("/sensor", response_model=SensorOut)
def criar_sensores(sensor: SensorCreate, db: Session = Depends(get_db)):
    """Cria um novo sensor (o 'empresa_id' deve vir no corpo da requisição)."""
    db_sensor = Sensor(**sensor.dict())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@app.get("/sensor/soma_ativos", response_model=int)
def soma_sensores_ativos(empresa_id: int, db: Session = Depends(get_db)):
    """Conta os sensores ativos de uma empresa específica."""
    soma = db.query(func.count(Sensor.id))\
             .filter(Sensor.status == "ATIVO", Sensor.empresa == empresa_id)\
             .scalar()
    return soma

# --- Rastreio ---

@app.get("/rastreio", response_model=List[RastreioOut])
def listar_rastreio(empresa_id: int, db: Session = Depends(get_db)):
    """Lista os registros de rastreio de uma empresa específica."""
    return db.query(Rastreio).filter(Rastreio.empresa == empresa_id).all()

@app.post("/rastreio", response_model=RastreioOut)
def criar_rastreio(rastreio: RastreioCreate, db: Session = Depends(get_db)):
    """Cria um novo registro de rastreio (o 'empresa_id' deve vir no corpo da requisição)."""
    db_rastreio = Rastreio(**rastreio.dict())
    db.add(db_rastreio)
    db.commit()
    db.refresh(db_rastreio)
    return db_rastreio

# --- Laudos ---

@app.get("/laudos", response_model=List[LaudoOut])
def listar_laudos(empresa_id: int, producao_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Lista os laudos de uma empresa, com filtro opcional por produção."""
    query = db.query(Laudo).filter(Laudo.empresa == empresa_id)
    if producao_id:
        query = query.filter(Laudo.producao_id == producao_id)
    return query.order_by(Laudo.data_criacao.desc()).all()

@app.post("/laudos", response_model=LaudoOut)
def criar_laudo(laudo: LaudoCreate, db: Session = Depends(get_db)):
    """Cria um novo laudo (o 'empresa_id' deve vir no corpo da requisição)."""
    db_laudo = Laudo(**laudo.dict())
    db.add(db_laudo)
    db.commit()
    db.refresh(db_laudo)
    return db_laudo

@app.get("/laudos/{laudo_id}", response_model=LaudoOut)
def obter_laudo(laudo_id: int, empresa_id: int, db: Session = Depends(get_db)):
    """Obtém um laudo específico, verificando se pertence à empresa correta."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id, Laudo.empresa == empresa_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado ou não pertence a esta empresa")
    return laudo

# --- Entry point ---
if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)