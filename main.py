from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import joblib
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Laudo
from typing import List


from auth import autenticar_usuario, get_db
from models import Usuario, Empresa, Producao, Fertilizante, Sensor, Rastreio
from schemas import UsuarioLogin
from typing import List, Optional
from datetime import datetime
from schemas import EmpresaOut
from schemas import EmpresaUpdate
from schemas import EmpresaCreate
from schemas import EmpresaBase
from schemas import ProducaoBase
from schemas import ProducaoCreate
from schemas import ProducaoUpdate
from schemas import ProducaoOut
from schemas import FertilizanteBase
from schemas import FertilizanteCreate
from schemas import FertilizanteUpdate
from schemas import FertilizanteOut
from schemas import SensorBase
from schemas import SensorCreate
from schemas import SensorUpdate
from schemas import SensorOut
from schemas import RastreioBase
from schemas import RastreioCreate
from schemas import RastreioOut
from schemas import RastreioUpdate
from schemas import LaudoBase
from schemas import LaudoCreate
from schemas import LaudoOut



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
    allow_origins=["*"],  # ou use seu domínio em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/empresas", response_model=List[EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).all()

@app.post("/empresas", response_model=EmpresaOut)
def criar_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    db_empresa = Empresa(**empresa.dict())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

@app.patch("/empresas/{empresa_id}", response_model=EmpresaOut)
def atualizar_empresa(empresa_id: int, updates: EmpresaUpdate, db: Session = Depends(get_db)):
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    for key, value in updates.dict(exclude_unset=True).items():
        setattr(db_empresa, key, value)

    db.commit()
    db.refresh(db_empresa)
    return db_empresa




@app.get("/producao", response_model=List[ProducaoOut])
def listar_producoes(db: Session = Depends(get_db)):
    return db.query(Producao).all()


@app.post("/producao", response_model=ProducaoOut)
def criar_producao(producao: ProducaoCreate, db: Session = Depends(get_db)):
    db_producao = Producao(**producao.dict())
    db.add(db_producao)
    db.commit()
    db.refresh(db_producao)
    return db_producao


@app.get("/producao/soma_volume_a_produzir", response_model=int)
def soma_producao_produzir(db: Session = Depends(get_db)):
    soma = db.query(func.coalesce(func.sum(Producao.volume), 0))\
             .filter(Producao.status == "Produzir")\
             .scalar()
    return soma


@app.get("/producao-semanal")
def producao_semanal(db: Session = Depends(get_db)):
    # Consulta agrupando por dia da semana
    resultados = (
        db.query(
            func.dayname(Producao.data).label("dia_semana"),
            func.sum(Producao.volume).label("total_volume")
        )
        .group_by(func.dayname(Producao.data))
        .order_by(
            func.field(
                func.dayname(Producao.data),
                "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
            )
        )
        .all()
    )

    # Converte para lista de dicionários
    return [
        {"dia_semana": r.dia_semana, "total_volume": float(r.total_volume or 0)}
        for r in resultados
    ]


@app.get("/fertilizante", response_model=List[FertilizanteOut])
def listar_fertilizantes(db: Session = Depends(get_db)):
    return db.query(Fertilizante).all()


@app.post("/fertilizante", response_model=FertilizanteOut)
def criar_tipo_fertilizante(fertilizante: FertilizanteCreate, db: Session = Depends(get_db)):
    db_fertilizante = Fertilizante(**fertilizante.dict())
    db.add(db_fertilizante)
    db.commit()
    db.refresh(db_fertilizante)
    return db_fertilizante



@app.get("/sensor", response_model=List[SensorOut])
def listar_sensores(db: Session = Depends(get_db)):
    return db.query(Sensor).all()


@app.post("/sensor", response_model=SensorOut)
def criar_sensores(sensor: SensorCreate, db: Session = Depends(get_db)):
    db_sensor = Sensor(**sensor.dict())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@app.get("/sensor/soma_ativos", response_model=int)
def soma_sensores_ativos(db: Session = Depends(get_db)):
    soma = db.query(func.count(Sensor.id))\
             .filter(Sensor.status == "ATIVO")\
             .scalar()
    return soma

@app.get("/rastreio", response_model=List[RastreioOut])
def listar_rastreio(db: Session = Depends(get_db)):
    return db.query(Rastreio).all()


@app.post("/rastreio", response_model=SensorOut)
def criar_rastreio(rastreio: RastreioCreate, db: Session = Depends(get_db)):
    db_rastreio = Rastreio(**rastreio.dict())
    db.add(db_rastreio)
    db.commit()
    db.refresh(db_rastreio)
    return db_rastreio


# Criar um laudo
@app.post("/laudos", response_model=LaudoOut)
def criar_laudo(laudo: LaudoCreate, db: Session = Depends(get_db)):
    db_laudo = Laudo(**laudo.dict())
    db.add(db_laudo)
    db.commit()
    db.refresh(db_laudo)
    return db_laudo

# Listar todos os laudos (pode receber filtro por producao_id)
@app.get("/laudos", response_model=List[LaudoOut])
def listar_laudos(producao_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Laudo)
    if producao_id:
        query = query.filter(Laudo.producao_id == producao_id)
    return query.order_by(Laudo.data_criacao.desc()).all()

# Obter um laudo específico por id
@app.get("/laudos/{laudo_id}", response_model=LaudoOut)
def obter_laudo(laudo_id: int, db: Session = Depends(get_db)):
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    return laudo