#  "[{"key":"chave-api-dados","value":"9b8e00db8253945fc8e90aa1cd4423be"}]

    
import pandas as pd
import requests
import locale

# Configuração inicial
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
minha_chave = '9b8e00db8253945fc8e90aa1cd4423be'  # ← Substitua pela sua chave!
headers = {'chave-api-dados': minha_chave}

# 1. Buscar dados da API
url = 'https://api.portaldatransparencia.gov.br/api-de-dados/despesas/por-orgao?ano=2023&orgaoSuperior=44000'
response = requests.get(url, headers=headers)

if response.status_code == 200:
    dados = response.json()
    df_despesas = pd.DataFrame(dados)
    
    # 2. Verificar colunas disponíveis
    print("Colunas disponíveis:", df_despesas.columns.tolist())
    
    # 3. Converter valores (ajuste o nome da coluna conforme necessário)
    if 'valorEmpenhado' in df_despesas.columns:  # Nome comum na API
        df_despesas['valor_empenhado'] = df_despesas['valorEmpenhado'].apply(
            lambda x: locale.atof(x.replace('.', '').replace(',', '.')) if isinstance(x, str) else x
        )
        print(df_despesas[['orgao', 'valor_empenhado']].head())
    else:
        print("Coluna 'valorEmpenhado' não encontrada nos dados.")
else:
    print("Erro na requisição:", response.status_code, response.text)