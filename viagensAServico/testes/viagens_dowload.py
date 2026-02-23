# O codigo a seguir vai no portal da transparencia e baixa o csv do ano especificado para viagens a serviço 
# extrai os dados e cria um dataframe de cada arquivo para trabalhar em cima deles
import os
import requests
import zipfile
import pandas as pd

class Viagens:
    def __init__(self, ano: int):
        self.ano = ano
        self.nome_arquivo_zip = f"dadosViagens/viagens_{ano}.zip"
        self.pasta_destino = f"dadosViagens/dados_viagens{ano}/"
        self.pasta_base = "dadosViagens/dados_viagens"
        os.makedirs(os.path.dirname(self.nome_arquivo_zip), exist_ok=True)

    def pegarViagens(self):
        self.download_csv()
        self.descompactar_arquivo()
        self.remover_arquivos_desnecessarios()
        passagem_df, trecho_df, viagem_df = self.carregar_csvs()

        return passagem_df, trecho_df, viagem_df

    def download_csv(self):
        url = f"https://portaldatransparencia.gov.br/download-de-dados/viagens/{self.ano}"
        print(f"🔄 Fazendo download de: {url}")

        try:
            resposta = requests.get(url)
            resposta.raise_for_status()
        except requests.HTTPError:
            raise SystemExit(f"Erro ao acessar URL {url}: {resposta.status_code}")

        url_csv = resposta.url
        print(f"➡️ Redirecionado para o CSV: {url_csv}")

        try:
            conteudo = requests.get(url_csv)
            conteudo.raise_for_status()
        except requests.HTTPError:
            raise SystemExit(f"Erro ao baixar o CSV: {conteudo.status_code}")

        with open(self.nome_arquivo_zip, "wb") as f:
            f.write(conteudo.content)

        print(f"✅ CSV salvo em: {self.nome_arquivo_zip}")

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
            print("❌ Arquivo .zip não encontrado.")
        except Exception as e:
            print(f"❌ Erro ao descompactar: {e}")

    def remover_arquivos_desnecessarios(self):
        pagamento = os.path.join(self.pasta_destino, f"{self.ano}_Pagamento.csv")
        #pagamento = f"dadosViagens/dados_viagens{ano}/{ano}_Pagamento.csv"

        try:
            os.remove(self.nome_arquivo_zip)
            print(f"✅ Arquivo ZIP removido: {self.nome_arquivo_zip}")
        except FileNotFoundError:
            print(f"❌ Arquivo ZIP não encontrado para remoção: {self.nome_arquivo_zip}")
        except Exception as e:
            print(f"❌ Erro ao remover o arquivo ZIP: {e}")

        try:
            os.remove(pagamento)
            print(f"✅ Arquivo de pagamentos removido: {pagamento}")
        except FileNotFoundError:
            print(f"❌ Arquivo de pagamentos não encontrado: {pagamento}")
        except Exception as e:
            print(f"❌ Erro ao remover o arquivo de pagamentos: {e}")

    def carregar_csvs(self):
        nomes = {
            "passagem_df": f"{self.ano}_Passagem.csv",
            "trecho_df": f"{self.ano}_Trecho.csv",
            "viagem_df": f"{self.ano}_Viagem.csv"
        }

        pasta_dados = os.path.join(self.pasta_base + str(self.ano))
        resultados = {}

        for var_name, nome_arquivo in nomes.items():
            caminho_completo = os.path.join(pasta_dados, nome_arquivo)
            try:
                df_raw = pd.read_csv(caminho_completo, sep=";", encoding="latin1", header=None, low_memory=False)
                df_raw.columns = df_raw.iloc[0]
                df = df_raw.drop(index=0).reset_index(drop=True)
                resultados[var_name] = df
                print(f"✅ {nome_arquivo} carregado com {len(df)} linhas (sem cabeçalho).")
            except FileNotFoundError:
                print(f"❌ Arquivo não encontrado: {nome_arquivo}")
                resultados[var_name] = None
            except Exception as e:
                print(f"❌ Erro ao carregar {nome_arquivo}: {e}")
                resultados[var_name] = None

        return resultados.get("passagem_df"), resultados.get("trecho_df"), resultados.get("viagem_df")



# ano = 2024
# vi = Viagens(ano)
# viagem_df, trecho_df, passagem_df = vi.pegarViagens()
