# test_db.py
from sqlalchemy import text
from database import SessionLocal

def testar_conexao():
    try:
        db = SessionLocal()
        resultado = db.execute(text("SELECT 1")).fetchone()
        print("✅ Conexão com o banco bem-sucedida!", resultado)
    except Exception as e:
        print("❌ Erro ao conectar com o banco:", e)
    finally:
        db.close()

if __name__ == "__main__":
    testar_conexao()
