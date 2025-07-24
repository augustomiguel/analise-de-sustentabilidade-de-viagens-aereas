import os
import requests
import zipfile
import pandas as pd

class Despesas:
    def __init__(self, ano: int, mes: int):
        self.ano = ano
        self.mes = mes
        self.periodo = f"{ano}{mes:02d}"
        self.nome_arquivo_zip = f"dadosDespesas/despesas_{self.periodo}.zip"
        self.pasta_destino = f"dadosDespesas/dados_despesas_{self.periodo}/"
        os.makedirs(os.path.dirname(self.nome_arquivo_zip), exist_ok=True)

    def pegarDespesas(self):
        self.download_csv()
        self.descompactar_arquivo()
        return self.carregar_csvs()

    def download_csv(self):
        url = f"https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao/{self.periodo}"
        print(f"🔄 Fazendo download de: {url}")

        try:
            resposta = requests.get(url)
            resposta.raise_for_status()
        except requests.HTTPError:
            raise SystemExit(f"❌ Erro ao acessar URL {url}: {resposta.status_code}")

        with open(self.nome_arquivo_zip, "wb") as f:
            f.write(resposta.content)

        print(f"✅ Arquivo ZIP salvo em: {self.nome_arquivo_zip}")

    def descompactar_arquivo(self):
        try:
            with zipfile.ZipFile(self.nome_arquivo_zip, 'r') as zip_ref:
                zip_ref.extractall(self.pasta_destino)
                print(f"✅ Arquivos extraídos para: {os.path.abspath(self.pasta_destino)}")
                print("📁 Conteúdo extraído:")
                for nome_arquivo in zip_ref.namelist():
                    print(f" - {nome_arquivo}")
        except zipfile.BadZipFile:
            print("❌ O arquivo ZIP está corrompido ou inválido.")
        except FileNotFoundError:
            print("❌ Arquivo ZIP não encontrado.")
        except Exception as e:
            print(f"❌ Erro ao descompactar: {e}")

        try:
            os.remove(self.nome_arquivo_zip)
            print(f"✅ Arquivo ZIP removido: {self.nome_arquivo_zip}")
        except Exception as e:
            print(f"⚠️ Erro ao remover o arquivo ZIP: {e}")

    def carregar_csvs(self):
        arquivos_csv = [f for f in os.listdir(self.pasta_destino) if f.endswith(".csv")]
        dataframes = {}

        for nome in arquivos_csv:
            caminho = os.path.join(self.pasta_destino, nome)
            try:
                df_raw = pd.read_csv(caminho, sep=";", encoding="latin1", header=None, low_memory=False)
                df_raw.columns = df_raw.iloc[0]
                df = df_raw.drop(index=0).reset_index(drop=True)
                dataframes[nome] = df
                print(f"✅ {nome} carregado com {len(df)} linhas.")
            except Exception as e:
                print(f"❌ Erro ao carregar {nome}: {e}")

        return dataframes

# Exemplo de uso:
# despesas = Despesas(2025, 1)
# dfs = despesas.pegarDespesas()
# for nome, df in dfs.items():
#     print(f"\n{nome} - Colunas: {df.columns.tolist()}")
