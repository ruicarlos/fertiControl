# models.py
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, TIMESTAMP, Float, Date, Text
from database import Base



# Modelo existente
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    senha_hash = Column(String(255))

# Novo modelo Empresa
class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_criacao = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
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


# Modelo Producao
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


# Modelo Fertilizante
class Fertilizante(Base):
    __tablename__ = "fertilizante"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fertilizante = Column(String(25), nullable=False)
    n = Column(Integer, nullable=False)
    p = Column(Integer, nullable=False)
    k = Column(Integer, nullable=False)


# Modelo Sensor
class Sensor(Base):
    __tablename__ = "sensor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor = Column(String(25), nullable=False)
    device = Column(String(25), nullable=False)
    status = Column(String(10), nullable=False)


# Modelo Rastreio
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

# Modelo Laudo
class Laudo(Base):
    __tablename__ = "laudos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    producao_id = Column(Integer, ForeignKey("producao.id"), nullable=True)
    tipo = Column(String(50))  # ex: dosagem, monitoramento, conformidade
    texto = Column(Text)
    data_criacao = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")