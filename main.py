# main.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # <-- IMPORT CORRIGIDO
from pydantic import BaseModel, EmailStr
import joblib
import os
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid # <-- IMPORT ADICIONADO
from datetime import date # <-- IMPORT ADICIONADO

from auth import autenticar_usuario, get_db
from models import Usuario, Empresa, Producao, Fertilizante, Sensor, Rastreio, Laudo, IndicadorDashboard 
from schemas import (
    UsuarioLogin, UsuarioOut, EmpresaCreate, EmpresaOut, EmpresaUpdate, ProducaoCreate,
    ProducaoOut, FertilizanteCreate, FertilizanteOut, SensorOut,
    RastreioCreate, RastreioOut, LaudoCreate, LaudoOut, IndicadorDashboardCreate, 
    IndicadorDashboardOut
)

# Carrega o modelo treinado
modelo = joblib.load("modelo_dosagem.pkl")

# Define o app
app = FastAPI(title="API de Validação FertiControl IA - Deway")

# --- Configuração de CORS e Arquivos Estáticos ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cria o diretório para salvar as imagens dos sensores, se não existir
os.makedirs("static/sensor_images", exist_ok=True)
# Monta o diretório 'static' para ser acessível via /static na URL
app.mount("/static", StaticFiles(directory="static"), name="static")


# Modelo de entrada para predição
class FertilizanteInput(BaseModel):
    N: int
    P: int
    K: int
    volume: float

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
    db_producao = Producao(**producao.dict())
    db.add(db_producao)
    db.commit()
    db.refresh(db_producao)
    return db_producao

@app.get("/producao/soma_volume_a_produzir", response_model=float)
def soma_producao_produzir(empresa_id: int, db: Session = Depends(get_db)):
    soma = db.query(func.coalesce(func.sum(Producao.volume), 0.0))\
             .filter(Producao.status == "Produzir", Producao.empresa == empresa_id)\
             .scalar()
    return soma

@app.get("/producao-semanal")
def producao_semanal(empresa_id: int, db: Session = Depends(get_db)):
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
    return db.query(Fertilizante).filter(Fertilizante.empresa == empresa_id).all()

@app.post("/fertilizante", response_model=FertilizanteOut)
def criar_tipo_fertilizante(fertilizante: FertilizanteCreate, db: Session = Depends(get_db)):
    db_fertilizante = Fertilizante(**fertilizante.dict())
    db.add(db_fertilizante)
    db.commit()
    db.refresh(db_fertilizante)
    return db_fertilizante

# --- Sensor ---

@app.get("/sensor", response_model=List[SensorOut])
def listar_sensores(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(Sensor).filter(Sensor.empresa == empresa_id).all()

@app.post("/sensor", response_model=SensorOut)
async def criar_sensores(
    db: Session = Depends(get_db),
    sensor: str = Form(...),
    device: str = Form(...),
    status: str = Form(...),
    empresa: int = Form(...),
    imagem: Optional[UploadFile] = File(None)
):
    imagem_url = None
    if imagem:
        file_extension = imagem.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"static/sensor_images/{unique_filename}"
        
        with open(file_path, "wb") as buffer:
            buffer.write(await imagem.read())
        
        imagem_url = f"/{file_path}"

    db_sensor = Sensor(
        sensor=sensor,
        device=device,
        status=status,
        empresa=empresa,
        imagem_url=imagem_url
    )
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor


@app.put("/sensor/{sensor_id}", response_model=SensorOut)
async def atualizar_sensor(
    sensor_id: int,
    db: Session = Depends(get_db),
    sensor: str = Form(...),
    device: str = Form(...),
    status: str = Form(...),
    empresa: int = Form(...), # Adicionado para validação
    imagem: Optional[UploadFile] = File(None)
):
    """
    Atualiza um sensor existente. Aceita dados de formulário e uma nova imagem opcional.
    """
    db_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not db_sensor:
        raise HTTPException(status_code=404, detail="Sensor não encontrado")
    
    # Opcional: Validar se o sensor pertence à empresa que está editando
    if db_sensor.empresa != empresa:
        raise HTTPException(status_code=403, detail="Acesso não autorizado para editar este sensor")

    # Atualiza os campos de texto
    db_sensor.sensor = sensor
    db_sensor.device = device
    db_sensor.status = status

    # Se uma nova imagem foi enviada, atualiza
    if imagem:
        # Opcional: Deletar a imagem antiga do servidor para não acumular lixo
        if db_sensor.imagem_url:
            old_image_path = db_sensor.imagem_url.lstrip('/')
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        
        # Salva a nova imagem
        file_extension = imagem.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"static/sensor_images/{unique_filename}"
        
        with open(file_path, "wb") as buffer:
            buffer.write(await imagem.read())
        
        db_sensor.imagem_url = f"/{file_path}"

    db.commit()
    db.refresh(db_sensor)
    return db_sensor


@app.get("/sensor/soma_ativos", response_model=int)
def soma_sensores_ativos(empresa_id: int, db: Session = Depends(get_db)):
    soma = db.query(func.count(Sensor.id))\
             .filter(Sensor.status == "ATIVO", Sensor.empresa == empresa_id)\
             .scalar()
    return soma

# --- Rastreio ---

@app.get("/rastreio", response_model=List[RastreioOut])
def listar_rastreio(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(Rastreio).filter(Rastreio.empresa == empresa_id).all()

@app.post("/rastreio", response_model=RastreioOut)
def criar_rastreio(rastreio: RastreioCreate, db: Session = Depends(get_db)):
    db_rastreio = Rastreio(**rastreio.dict())
    db.add(db_rastreio)
    db.commit()
    db.refresh(db_rastreio)
    return db_rastreio

# --- Laudos ---

@app.get("/laudos", response_model=List[LaudoOut])
def listar_laudos(empresa_id: int, producao_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Laudo).filter(Laudo.empresa == empresa_id)
    if producao_id:
        query = query.filter(Laudo.producao_id == producao_id)
    return query.order_by(Laudo.data_criacao.desc()).all()

@app.post("/laudos", response_model=LaudoOut)
def criar_laudo(laudo: LaudoCreate, db: Session = Depends(get_db)):
    db_laudo = Laudo(**laudo.dict())
    db.add(db_laudo)
    db.commit()
    db.refresh(db_laudo)
    return db_laudo

@app.get("/laudos/{laudo_id}", response_model=LaudoOut)
def obter_laudo(laudo_id: int, empresa_id: int, db: Session = Depends(get_db)):
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id, Laudo.empresa == empresa_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado ou não pertence a esta empresa")
    return laudo

# --- NOVAS ROTAS PARA INDICADORES DO DASHBOARD ---

# ROTA CORRIGIDA para consistência com o frontend
@app.post("/indicadores_dashboard", response_model=IndicadorDashboardOut)
def salvar_dados_grafico(
    dados: IndicadorDashboardCreate, db: Session = Depends(get_db)
):
    """
    Salva ou atualiza os dados dos gráficos do dashboard para uma empresa em um dia específico.
    """
    db_indicador = db.query(IndicadorDashboard).filter(
        IndicadorDashboard.empresa_id == dados.empresa_id,
        IndicadorDashboard.data == dados.data
    ).first()

    if not db_indicador:
        db_indicador = IndicadorDashboard(empresa_id=dados.empresa_id, data=dados.data)
        db.add(db_indicador)

    update_data = dados.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(db_indicador, key) and value is not None:
            setattr(db_indicador, key, value)
    
    if db_indicador.disponibilidade is not None and db_indicador.performance is not None and db_indicador.qualidade is not None:
        db_indicador.oee = (db_indicador.disponibilidade / 100) * (db_indicador.performance / 100) * (db_indicador.qualidade / 100) * 100

    if db_indicador.tempo_produzindo is not None and db_indicador.tempo_planejado is not None and db_indicador.tempo_planejado > 0:
        db_indicador.eficiencia_operacional = (db_indicador.tempo_produzindo / db_indicador.tempo_planejado) * 100

    if db_indicador.producao_real is not None and db_indicador.horas_trabalhadas is not None and db_indicador.horas_trabalhadas > 0:
        db_indicador.produtividade = db_indicador.producao_real / db_indicador.horas_trabalhadas
    
    db.commit()
    db.refresh(db_indicador)
    return db_indicador


# ROTA CORRIGIDA para consistência com o frontend
@app.get("/indicadores_dashboard/latest", response_model=Optional[IndicadorDashboardOut])
def obter_ultimos_dados_grafico(empresa_id: int, db: Session = Depends(get_db)):
    """
    Retorna o último registro de dados de gráfico para uma empresa.
    """
    return db.query(IndicadorDashboard)\
             .filter(IndicadorDashboard.empresa_id == empresa_id)\
             .order_by(IndicadorDashboard.data.desc())\
             .first()

# --- Entry point ---
if __name__ == "__main__":
    import uvicorn
    # O ideal é usar a string 'main:app' para que o reload funcione corretamente
    # com o uvicorn instalado no ambiente virtual.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)