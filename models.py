# models.py
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, TIMESTAMP, Float, Date, Text
from database import Base
from sqlalchemy.sql import func # Importação necessária

# Modelo Empresa (Não muda)
class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_criacao = Column(TIMESTAMP, server_default=func.now())
    cnpj = Column(String(18), unique=True, nullable=False)
    nome_empresa = Column(String(255), nullable=False)
    email_contato = Column(String(255), nullable=True)
    cep = Column(String(9), nullable=False)
    cidade = Column(String(100), nullable=False)
    endereco = Column(String(255), nullable=False)
    complemento = Column(String(100), nullable=True)
    responsavel_nome = Column(String(255), nullable=False)
    responsavel_email = Column(String(255), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)

# Modelo Usuario (Não muda)
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    senha_hash = Column(String(255))
    name = Column(String(100))
    role = Column(String(50), default="user")
    empresa = Column(Integer, ForeignKey("empresas.id"), nullable=True)

# Modelo Producao (Não muda)
class Producao(Base):
    __tablename__ = "producao"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(250), nullable=False)
    volume = Column(Float, nullable=False)
    data = Column(Date, nullable=True)
    hora = Column(String(20), nullable=True)
    status = Column(String(25), nullable=False)
    laudo = Column(Text, nullable=True)
    sn = Column(Float, nullable=False)
    sp = Column(Float, nullable=False)
    sk = Column(Float, nullable=False)
    amonia = Column(String(20), nullable=True)
    fosfato = Column(String(20), nullable=True)
    potassio = Column(String(20), nullable=True)
    empresa = Column(Integer, ForeignKey("empresas.id"))

# Modelo Fertilizante (Não muda)
class Fertilizante(Base):
    __tablename__ = "fertilizante"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fertilizante = Column(String(25), nullable=False)
    n = Column(Integer, nullable=False)
    p = Column(Integer, nullable=False)
    k = Column(Integer, nullable=False)
    empresa = Column(Integer, ForeignKey("empresas.id"))

# Modelo Sensor (MODIFICADO)
class Sensor(Base):
    __tablename__ = "sensor"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor = Column(String(25), nullable=False)
    device = Column(String(25), nullable=False)
    status = Column(String(10), nullable=False)
    porta = Column(String(10), nullable=False)
    ip = Column(String(25), nullable=False)
    imagem_url = Column(String(512), nullable=True) # <-- NOVO CAMPO
    empresa = Column(Integer, ForeignKey("empresas.id"))

# Modelo Rastreio (Não muda)
class Rastreio(Base):
    __tablename__ = "rastreio"
    id = Column(Integer, primary_key=True, autoincrement=True)
    producao = Column(Integer)
    sensor = Column(String(15), nullable=True)
    quantidade = Column(Float, nullable=False)
    peso = Column(Float, nullable=False)
    data = Column(Date, nullable=True)
    hora = Column(String(15), nullable=True)
    status = Column(String(10), nullable=False)
    empresa = Column(Integer, ForeignKey("empresas.id"))

# Modelo Laudo (Não muda)
class Laudo(Base):
    __tablename__ = "laudos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    producao_id = Column(Integer, ForeignKey("producao.id"), nullable=True)
    tipo = Column(String(50))
    texto = Column(Text)
    data_criacao = Column(TIMESTAMP, server_default=func.now())
    empresa = Column(Integer, ForeignKey("empresas.id"))

# NOVO MODELO para os gráficos do Dashboard
class IndicadorDashboard(Base):
    __tablename__ = "indicadores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Date, nullable=False)
    
    # Campos OEE
    disponibilidade = Column(Float, nullable=True)
    performance = Column(Float, nullable=True)
    qualidade = Column(Float, nullable=True)
    oee = Column(Float, nullable=True)
    
    # Campos Eficiência Operacional
    tempo_produzindo = Column(Float, nullable=True)
    tempo_planejado = Column(Float, nullable=True)
    eficiencia_operacional = Column(Float, nullable=True)
    
    # Campos Produtividade
    producao_real = Column(Float, nullable=True)
    horas_trabalhadas = Column(Float, nullable=True)
    produtividade = Column(Float, nullable=True)
    
    data_criacao = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)