# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date

class UsuarioLogin(BaseModel):
    username: str
    senha: str

class UsuarioOut(BaseModel):
    id: int
    username: str
    name: str
    role: str

    class Config:
        from_attributes = True

        
class EmpresaBase(BaseModel):
    cnpj: str
    nome_empresa: str
    email_contato: Optional[EmailStr] = None
    cep: str
    cidade: str
    endereco: str
    complemento: Optional[str] = None
    responsavel_nome: str
    responsavel_email: EmailStr
    ativo: Optional[bool] = True

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nome_empresa: Optional[str] = None
    email_contato: Optional[EmailStr] = None
    cep: Optional[str] = None
    cidade: Optional[str] = None
    endereco: Optional[str] = None
    complemento: Optional[str] = None
    responsavel_nome: Optional[str] = None
    responsavel_email: Optional[EmailStr] = None
    ativo: Optional[bool] = None

class EmpresaOut(EmpresaBase):
    id: int
    data_criacao: datetime

    class Config:
        from_attributes  = True



# Produção
class ProducaoBase(BaseModel):
    tipo: str
    volume: float
    data: date
    hora: str
    status: str
    laudo: str
    sn: float
    sp: float
    sk: float
    amonia: str
    fosfato: str
    potassio: str

class ProducaoCreate(ProducaoBase):
    pass

class ProducaoUpdate(BaseModel):
    tipo: Optional[str] = None
    volume: Optional[float] = None
    data: Optional[date] = None
    hora: Optional[str] = None
    status: Optional[str] = None
    laudo: Optional[str] = None
    sn: Optional[float] = None
    sp: Optional[float] = None
    sk: Optional[float] = None
    amonia: Optional[str] = None
    fosfato: Optional[str] = None
    potassio: Optional[str] = None

class ProducaoOut(ProducaoBase):
    id: int

    class Config:
        from_attributes = True

# Fertilizante
class FertilizanteBase(BaseModel):
    fertilizante: str
    n: int
    p: int
    k: int

class FertilizanteCreate(FertilizanteBase):
    pass

class FertilizanteUpdate(BaseModel):
    fertilizante: Optional[str] = None
    n: Optional[int] = None
    p: Optional[int] = None
    k: Optional[int] = None

class FertilizanteOut(FertilizanteBase):
    id: int

    class Config:
        from_attributes = True

# Sensor
class SensorBase(BaseModel):
    sensor: str
    device: str
    status: str    

class SensorCreate(SensorBase):
    pass

class SensorUpdate(BaseModel):
    sensor: Optional[str] = None
    device: Optional[str] = None
    status: Optional[str] = None

class SensorOut(SensorBase):
    id: int

    class Config:
        from_attributes = True


# Rastreio
class RastreioBase(BaseModel):
    producao: int
    sensor: str
    quantidade: float
    peso: float
    data: date
    hora: str
    status: str    

class RastreioCreate(RastreioBase):
    pass

class RastreioUpdate(BaseModel):
    producao: Optional[int] = None
    sensor: Optional[str] = None
    quantidade: Optional[float] = None
    peso: Optional[float] = None
    data: Optional[date] = None
    hora: Optional[str] = None
    status: Optional[str] = None

class RastreioOut(RastreioBase):
    id: int

    class Config:
        from_attributes = True


class LaudoBase(BaseModel):
    tipo: str
    texto: str
    producao_id: Optional[int] = None

class LaudoCreate(LaudoBase):
    pass

class LaudoOut(LaudoBase):
    id: int
    data_criacao: datetime

    class Config:
       from_attributes = True