import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# Função para extrair os valores NPK da string
def parse_npk(npk_str):
    return list(map(int, npk_str.replace("NPK ", "").split("-")))

# 1. Criar base de dados simulado fazer troca para outra fonte de dados
data = [
    {"tipo": "NPK 20-10-10", "volume": 100},
    {"tipo": "NPK 4-14-8", "volume": 50},
    {"tipo": "NPK 10-20-20", "volume": 200},
    {"tipo": "NPK 30-0-10", "volume": 150},
    {"tipo": "NPK 5-10-5", "volume": 80},
]

# Aplicar parsing e simular dosagens 
for row in data:
    N, P, K = parse_npk(row["tipo"])
    volume = row["volume"]
    row["N"] = N
    row["P"] = P
    row["K"] = K
    # Simples proporção como base (poderia ser mais complexo com IA)
    row["amonia"] = N * volume / 100
    row["fosfato"] = P * volume / 100
    row["potassio"] = K * volume / 100

df = pd.DataFrame(data)

# 2. Separar dados de entrada e saída
X = df[["N", "P", "K", "volume"]]
y = df[["amonia", "fosfato", "potassio"]]

# 3. Treinamento do modelo
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
modelo = LinearRegression()
modelo.fit(X_train, y_train)

# Salvar o modelo treinado
joblib.dump(modelo, "modelo_dosagem.pkl")

# 4. Avaliar o modelo
y_pred = modelo.predict(X_test)
erro = mean_squared_error(y_test, y_pred)
print(f"Erro médio quadrático: {erro:.2f}")

# 5. Prever nova dosagem
def prever_dosagem(n, p, k, volume):
    entrada = [[n, p, k, volume]]
    pred = modelo.predict(entrada)[0]
    return {
        "amonia (g)": round(pred[0], 2),
        "fosfato (g)": round(pred[1], 2),
        "potassio (g)": round(pred[2], 2),
    }

# 6. Exemplo de uso
resposta = prever_dosagem(20, 10, 10, 500)
print("\nDosagem recomendada para NPK 20-10-10, volume 500L:")
print(resposta)
