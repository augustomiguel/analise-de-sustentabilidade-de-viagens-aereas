#  "[{"key":"chave-api-dados","value":"9b8e00db8253945fc8e90aa1cd4423be"}]

# Teste rápido da chave - Substitua SUA_CHAVE_REAL_AQUI
import pandas as pd
import requests
import locale
from datetime import datetime

chave = "9b8e00db8253945fc8e90aa1cd4423be"
teste = requests.get(
    "https://api.portaldatransparencia.gov.br/api-de-dados/orgaos",
    headers={"chave-api-dados": chave}
)
print("Status:", teste.status_code)
print("Resposta:", teste.text[:100])



# Configuração
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
headers = {'chave-api-dados': '9b8e00db8253945fc8e90aa1cd4423be'}  # ← Substituir!

# 1. Primeiro valide a chave
def validar_chave():
    teste = requests.get(
        "https://api.portaldatransparencia.gov.br/api-de-dados/orgaos",
        headers=headers,
        timeout=10
    )
    if teste.status_code == 200:
        print("✅ Chave validada com sucesso!")
        return True
    else:
        print(f"❌ Erro {teste.status_code} - Chave inválida ou problema de conexão")
        print("Resposta:", teste.text)
        return False

# 2. Busca específica para energia na UFPB
def buscar_energia_ufpb():
    if not validar_chave():
        return pd.DataFrame()

    params = {
        'codigoOrgao': '153308',  # UFPB
        'ano': 2023,
        'elementoDespesa': '339030',  # Energia elétrica
        'pagina': 1
    }

    print("\n🔍 Buscando despesas de energia...")
    todas = []
    while True:
        try:
            resp = requests.get(
                "https://api.portaldatransparencia.gov.br/api-de-dados/despesas",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if resp.status_code != 200:
                print(f"Erro {resp.status_code}: {resp.text[:200]}...")
                break
                
            dados = resp.json()
            if not dados:
                break
                
            todas.extend(dados)
            print(f"Página {params['pagina']}: {len(dados)} registros")
            params['pagina'] += 1
            
        except Exception as e:
            print(f"Falha na requisição: {str(e)}")
            break

    return pd.DataFrame(todas)

# Execução principal
if __name__ == "__main__":
    df = buscar_energia_ufpb()
    
    if not df.empty:
        # Processamento dos dados
        df['valor'] = pd.to_numeric(
            df['valor'].str.replace(r'[^\d,]', '', regex=True)
            .str.replace(',', '.'),
            errors='coerce'
        )
        
        print(f"\n🎯 Total de registros: {len(df)}")
        print(f"💸 Total gasto: R$ {df['valor'].sum():,.2f}")
        
        # Salvar com encoding correto
        df.to_csv('gastos_energia_ufpb.csv', index=False, encoding='utf-8-sig')
        print("💾 Arquivo salvo como 'gastos_energia_ufpb.csv'")
    else:
        print("\n⚠️ Nenhum dado encontrado. Verifique:")
        print("- Chave API válida")
        print("- Parâmetros corretos (código órgão e elemento despesa)")
        print("- Conexão com a internet")