import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# --- 1. GERAÇÃO DE UMA BASE DE DADOS ROBUSTA ---

# Parâmetros para a geração dos dados
num_amostras = 500
formulas_npk_comuns = [
    (20, 10, 10), (4, 14, 8), (10, 20, 20), (30, 0, 10),
    (5, 10, 5), (15, 15, 15), (10, 10, 10), (25, 5, 5),
    (0, 20, 20)
]

dados_gerados = []

print("Gerando base de dados sintética...")

for _ in range(num_amostras):
    # Escolhe uma fórmula NPK aleatória da lista
    n, p, k = formulas_npk_comuns[np.random.randint(0, len(formulas_npk_comuns))]
    
    # Gera um volume de produção aleatório entre 100kg e 50000kg
    volume_kg = np.random.randint(100, 50001)
    
    # --- CÁLCULO CORRETO DA DOSAGEM EM GRAMAS ---
    # Fórmula: massa_nutriente_g = volume_total_kg * 1000 * (percentual_garantia / 100)
    
    massa_amonia_g = (volume_kg * 1000) * (n / 100)
    massa_fosfato_g = (volume_kg * 1000) * (p / 100)
    massa_potassio_g = (volume_kg * 1000) * (k / 100)
    
    # Adiciona uma pequena variação (ruído) para simular imperfeições do processo real
    fator_ruido = 1 + (np.random.rand() - 0.5) * 0.02 # Variação de +/- 1%
    
    dados_gerados.append({
        "N": n,
        "P": p,
        "K": k,
        "volume": volume_kg,
        "amonia": massa_amonia_g * fator_ruido,
        "fosfato": massa_fosfato_g * fator_ruido,
        "potassio": massa_potassio_g * fator_ruido,
    })

# Cria um DataFrame do Pandas com os dados gerados
df = pd.DataFrame(dados_gerados)

# Salva a base de dados gerada em um arquivo CSV para referência
df.to_csv("dosagem_dataset.csv", index=False)
print(f"Base de dados com {num_amostras} amostras salva em 'dosagem_dataset.csv'")


# --- 2. TREINAMENTO DO NOVO MODELO ---

# Separar dados de entrada (features) e saída (targets)
X = df[["N", "P", "K", "volume"]]
y = df[["amonia", "fosfato", "potassio"]]

# Dividir os dados em conjuntos de treino e teste
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Criar e treinar o modelo de Regressão Linear
modelo_corrigido = LinearRegression()
modelo_corrigido.fit(X_train, y_train)

# Salvar o novo modelo treinado
joblib.dump(modelo_corrigido, "modelo_dosagem_corrigido.pkl")
print("Novo modelo treinado e salvo como 'modelo_dosagem_corrigido.pkl'")


# --- 3. AVALIAÇÃO E EXEMPLO DE USO ---

# Avaliar o desempenho do novo modelo no conjunto de teste
y_pred = modelo_corrigido.predict(X_test)
score_r2 = r2_score(y_test, y_pred)
print(f"\nDesempenho do modelo (R² Score): {score_r2:.4f}")
print("(Um valor próximo de 1.0 indica um modelo muito preciso)")

# Exemplo de uso da função de previsão com o novo modelo
def prever_dosagem_corrigida(n, p, k, volume_kg):
    entrada = [[n, p, k, volume_kg]]
    pred = modelo_corrigido.predict(entrada)[0]
    return {
        "amonia (g)": round(pred[0], 2),
        "fosfato (g)": round(pred[1], 2),
        "potassio (g)": round(pred[2], 2),
    }

# Teste com o caso que estava dando inconformidade (NPK 4-14-8 para 40000 kg)
print("\n--- Exemplo de Previsão Corrigida ---")
resposta = prever_dosagem_corrigida(4, 14, 8, 40000)
print("Dosagem recomendada para NPK 4-14-8, volume 40000 kg:")
print(resposta)

# Valores esperados (metas)
meta_n = 40000 * 1000 * (4 / 100)
meta_p = 40000 * 1000 * (14 / 100)
meta_k = 40000 * 1000 * (8 / 100)
print(f"\nMetas para conformidade: Amônia={meta_n:,.2f}g, Fosfato={meta_p:,.2f}g, Potássio={meta_k:,.2f}g")
