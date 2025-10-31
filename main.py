# main.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import joblib
import os
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid
from datetime import date, datetime
import time
import random
from database import SessionLocal

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

#regex_origens_permitidas = r"^https?:\/\/((localhost(:\d+)?)|(ferticontrol-web\.vercel\.app)).*" # adicionado

app.add_middleware(
    CORSMiddleware,
    # allow_origin_regex=regex_origens_permitidas,  # adicionado
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

# --- NOVO MÉTODO DELETE ADICIONADO AQUI ---
@app.delete("/empresas/{empresa_id}")
def deletar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """
    Deleta uma empresa e todos os usuários associados a ela.
    """
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Deleta usuários associados à empresa primeiro para evitar violação de chave estrangeira
    db.query(Usuario).filter(Usuario.empresa == empresa_id).delete()
    
    # Agora deleta a empresa
    db.delete(empresa)
    
    db.commit()
    return {"detail": "Empresa e usuários associados deletados com sucesso"}


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
def criar_producao(producao: ProducaoCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Cria uma nova produção. Se o status for 'Produzir',
    inicia a simulação de dosagem em segundo plano.
    """
    db_producao = Producao(**producao.dict())
    db.add(db_producao)
    db.commit()
    db.refresh(db_producao)

    # Se a produção for criada com o status "Produzir", adiciona a tarefa de simulação
    if producao.status == 'Produzir':
        background_tasks.add_task(iniciar_simulacao_dosagem, db_producao.id)

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
    ip: Optional[str] = Form(None),      
    porta: Optional[str] = Form(None), 
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
        ip=ip,                  
        porta=porta,           
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
    empresa: int = Form(...), 
    ip: Optional[str] = Form(None),       
    porta: Optional[str] = Form(None),   
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
    db_sensor.ip = ip             
    db_sensor.porta = porta       

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
    """
    Cria um novo laudo. Atualiza o status da produção associada
    tanto para laudos Aprovados quanto Reprovados.
    """
    # 1. Cria o novo objeto de laudo
    db_laudo = Laudo(**laudo.dict())
    db.add(db_laudo)

    # --- LÓGICA ATUALIZADA ---
    # 2. Verifica se o laudo tem uma produção associada
    if laudo.producao_id:
        db_producao = db.query(Producao).filter(Producao.id == laudo.producao_id).first()

        # Se a produção for encontrada, aplica as regras
        if db_producao:
            # A produção é considerada 'Concluída' em ambos os casos, pois o processo de análise terminou.
            db_producao.status = 'Concluído'

            # Define o resultado do laudo na produção com base no tipo do laudo
            if laudo.tipo == 'Aprovado':
                db_producao.laudo = 'Conforme'
            elif laudo.tipo == 'Reprovado':
                db_producao.laudo = 'Rejeitado'

    # 3. Salva todas as alterações (o novo laudo e a atualização da produção)
    db.commit()

    # 4. Atualiza o objeto do laudo com os dados do banco
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

# Adicione esta função em main.py, na seção de Produção

@app.get("/producao/media_conformidade", response_model=float)
def obter_media_conformidade(empresa_id: int, db: Session = Depends(get_db)):
    """
    Calcula a porcentagem de produções concluídas que estão em conformidade.
    A conformidade é definida pelo campo 'laudo' sendo igual a 'Conforme'.
    """
    # Conta todas as produções que foram concluídas para a empresa
    total_concluidas = db.query(Producao).filter(
        Producao.empresa == empresa_id,
        Producao.status == 'Concluído'
    ).count()

    # Se não houver produções concluídas, a conformidade é 0 para evitar divisão por zero
    if total_concluidas == 0:
        return 0.0

    # Conta as produções concluídas que têm o laudo "Conforme"
    total_conforme = db.query(Producao).filter(
        Producao.empresa == empresa_id,
        Producao.status == 'Concluído',
        Producao.laudo == 'Conforme'
    ).count()

    # Calcula a porcentagem
    media = (total_conforme / total_concluidas) * 100

    return round(media, 2)


# --- 2. ADICIONE A NOVA FUNÇÃO DE SIMULAÇÃO (Pode ser antes da rota criar_producao) ---
# SUBSTITUA A SUA FUNÇÃO ANTIGA POR ESTA VERSÃO OTIMIZADA
def iniciar_simulacao_dosagem(producao_id: int):
    """
    Simula o processo de dosagem de forma mais rápida e utilizando os
    nomes dos sensores cadastrados no banco de dados para a empresa.
    """
    print(f"--- Iniciando simulação de dosagem para Produção ID: {producao_id} ---")

    # Cria uma nova sessão de DB exclusiva para esta tarefa
    db = SessionLocal()
    try:
        # Busca os dados da produção que será simulada
        db_producao = db.query(Producao).filter(Producao.id == producao_id).first()
        if not db_producao:
            print(f"[ERRO] Produção ID {producao_id} não encontrada.")
            return

        # --- MUDANÇA 1: BUSCAR SENSORES REAIS DO BANCO DE DADOS ---
        # Busca os nomes dos sensores cadastrados para a empresa desta produção.
        sensores_da_empresa = db.query(Sensor.sensor).filter(Sensor.empresa == db_producao.empresa).all()

        # Extrai os nomes da lista de tuplas retornada pela query
        lista_nomes_sensores = [s[0] for s in sensores_da_empresa]

        if not lista_nomes_sensores:
            print(f"[ERRO] Nenhum sensor cadastrado para a empresa ID {db_producao.empresa}. Abortando simulação.")
            db_producao.status = 'Falhou' # Atualiza o status para indicar o erro
            db.commit()
            return

        # Mapeia dinamicamente os sensores aos valores de Nitrogênio, Fosfato e Potássio.
        # Usa o operador de módulo (%) para evitar erros caso haja menos de 3 sensores.
        sensor_n = lista_nomes_sensores[0]
        sensor_p = lista_nomes_sensores[1 % len(lista_nomes_sensores)]
        sensor_k = lista_nomes_sensores[2 % len(lista_nomes_sensores)]

        dosagens_a_simular = {
            sensor_n: db_producao.sn,      # Nitrogênio / Amônia
            sensor_p: db_producao.sp,      # Fosfato
            sensor_k: db_producao.sk       # Potássio
        }

        # --- MUDANÇA 2: SIMULAÇÃO MAIS RÁPIDA E BASEADA EM PASSOS ---
        num_passos = 8 # Define um número fixo de passos para a simulação

        # Itera sobre cada sensor/insumo para simular a dosagem
        for sensor_nome, quantidade_final in dosagens_a_simular.items():
            # Pula a simulação para este nutriente se a quantidade for zero
            if quantidade_final <= 0:
                print(f"[{sensor_nome}] Quantidade é 0. Pulando dosagem.")
                continue

            print(f"[{sensor_nome}] Iniciando dosagem. Meta: {quantidade_final:.2f}g")

            # Loop que executa um número fixo de passos, tornando a duração previsível
            for passo in range(1, num_passos + 1):
                # Calcula o peso atual proporcionalmente ao passo atual
                peso_atual = (quantidade_final / num_passos) * passo

                # Garante que o peso não ultrapasse a meta final e arredonda
                peso_atual = round(min(peso_atual, quantidade_final), 2)

                # Cria o payload para a tabela de rastreio
                payload_rastreio = {
                    "producao": producao_id,
                    "sensor": sensor_nome, # <-- Usa o nome do sensor real
                    "quantidade": quantidade_final,
                    "peso": peso_atual,
                    "data": datetime.now().date(),
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "status": "Dosando",
                    "empresa": db_producao.empresa
                }

                # Cria e salva o registro de rastreio diretamente no banco
                novo_rastreio = Rastreio(**payload_rastreio)
                db.add(novo_rastreio)
                db.commit()

                print(f"[{sensor_nome}] Passo {passo}/{num_passos} - Peso atual: {peso_atual:.2f}g")

                # Pausa menor para uma simulação mais rápida
                time.sleep(0.2) # <-- Reduzido de 1s para 0.2s

            print(f"[{sensor_nome}] Dosagem finalizada.")

        # Ao final de todas as dosagens, atualiza o status da produção
        db_producao.status = 'Em Análise' # Próxima etapa do processo
        db.commit()

        print(f"--- Simulação finalizada. Produção ID {producao_id} atualizada para 'Em Análise' ---")

    except Exception as e:
        print(f"[ERRO GERAL] Ocorreu um erro durante a simulação para a produção ID {producao_id}: {e}")
        # Tenta reverter o status da produção em caso de falha inesperada
        db_producao = db.query(Producao).filter(Producao.id == producao_id).first()
        if db_producao:
            db_producao.status = 'Falhou'
            db.commit()
    finally:
        db.close()

# --- Entry point ---
if __name__ == "__main__":
    import uvicorn
    # O ideal é usar a string 'main:app' para que o reload funcione corretamente
    # com o uvicorn instalado no ambiente virtual.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)