# downloader.py
import os
import requests
import zipfile
import pandas as pd
import re # Importa regex

class ViagensDownloader:
    def __init__(self, ano: int):
        self.ano = ano
        self.pasta_base_dados = "dadosViagens"
        self.nome_arquivo_zip = os.path.join(self.pasta_base_dados, f"viagens_{self.ano}.zip")
        self.pasta_destino_csv = os.path.join(self.pasta_base_dados, f"dados_viagens{self.ano}")
        os.makedirs(self.pasta_destino_csv, exist_ok=True)
        
        print(f"DataDownloader: Pronto para o ano {self.ano}.")
        print(f"  -> Pasta de CSVs: {self.pasta_destino_csv}")

    def _download_csv(self):
        url = f"https://portaldatransparencia.gov.br/download-de-dados/viagens/{self.ano}"
        print(f"🔄 Fazendo download de: {url}")
        
        try:
            resposta = requests.get(url)
            resposta.raise_for_status()
            url_csv = resposta.url # URL final após redirecionamento
            
            print(f"➡️ Redirecionado para: {url_csv}")
            conteudo = requests.get(url_csv)
            conteudo.raise_for_status()

            with open(self.nome_arquivo_zip, "wb") as f:
                f.write(conteudo.content)
            print(f"✅ Download salvo em: {self.nome_arquivo_zip}")
            return True
        except Exception as e:
            print(f"❌ Erro no download para o ano {self.ano}: {e}")
            return False

    def _descompactar_arquivo(self):
        print(f"🔄 Descompactando '{self.nome_arquivo_zip}'...")
        try:
            with zipfile.ZipFile(self.nome_arquivo_zip, 'r') as zip_ref:
                zip_ref.extractall(self.pasta_destino_csv)
            print(f"✅ Arquivos extraídos para: {self.pasta_destino_csv}")
            
            # Limpeza do .zip e Pagamento.csv
            os.remove(self.nome_arquivo_zip)
            print(f"   - Arquivo .zip removido.")
            
            arquivo_pagamento = os.path.join(self.pasta_destino_csv, f"{self.ano}_Pagamento.csv")
            if os.path.exists(arquivo_pagamento):
                os.remove(arquivo_pagamento)
                print(f"   - Arquivo de Pagamento removido.")
            return True
        except Exception as e:
            print(f"❌ Erro ao descompactar ou limpar: {e}")
            return False

    def _normalize_whitespace(self, text):
        """Limpa agressivamente o texto, removendo espaços ocultos."""
        if isinstance(text, str):
            # Substitui múltiplos espaços (incluindo \n, \t, \xa0) por um espaço único
            text = re.sub(r'\s+', ' ', text, flags=re.UNICODE)
            return text.strip()
        return text

    def _normalizar_colunas(self, df, var_name):
        """
        Verifica nomes de colunas conhecidos e os renomeia para um padrão interno.
        """
        
        # *** ETAPA DE LIMPEZA AGRESSIVA ***
        df.columns = [self._normalize_whitespace(col) for col in df.columns]
        
        # *** LÓGICA MOVIDA PARA 'viagem_df' ***
        if var_name == "viagem_df":
            # Chave: Nome padrão interno
            # Valor: Lista de possíveis nomes (EM MAIÚSCULAS E LIMPOS)
            mapa_colunas = {
                'Nome órgão solicitante': ['NOME ÓRGÃO SOLICITANTE', 'ÓRGÃO SOLICITANTE'],
            }
            
            colunas_renomeadas = {}
            coluna_padrao_encontrada = False

            # Itera sobre as colunas ATUAIS do DataFrame
            for col_atual in df.columns:
                col_limpa_upper = col_atual.upper() # Compara em maiúsculas
                
                for nome_padrao, possiveis_nomes_upper in mapa_colunas.items():
                    if col_limpa_upper in possiveis_nomes_upper:
                        if col_atual != nome_padrao: # Se precisar renomear
                            colunas_renomeadas[col_atual] = nome_padrao
                        coluna_padrao_encontrada = True # Marca que encontramos
                        break # Para o loop interno
            
            if colunas_renomeadas:
                df = df.rename(columns=colunas_renomeadas)
                print(f"      -> Colunas normalizadas: {colunas_renomeadas}")

            # Verificação final
            if not coluna_padrao_encontrada:
                print(f"      -> ⚠️ ATENÇÃO: Coluna 'Nome órgão solicitante' não foi encontrada em {var_name}.")
                print(f"         Colunas atuais: {list(df.columns)}")
                raise KeyError(f"Falha na normalização da coluna 'Nome órgão solicitante' em {var_name}.")
        
        # Mapeamento para 'trecho_df'
        if var_name == "trecho_df":
            if "Identificador do processo de viagem " in df.columns:
                df = df.rename(columns={"Identificador do processo de viagem ": "Identificador do processo de viagem"})
        
        return df

    def carregar_csvs(self):
        """Carrega os CSVs essenciais em DataFrames."""
        print(f"🔄 Carregando CSVs para DataFrames do ano {self.ano}...")
        nomes = {
            "passagem_df": f"{self.ano}_Passagem.csv",
            "trecho_df": f"{self.ano}_Trecho.csv",
            "viagem_df": f"{self.ano}_Viagem.csv"
        }
        resultados = {}
        
        for var_name, nome_arquivo in nomes.items():
            caminho_completo = os.path.join(self.pasta_destino_csv, nome_arquivo)
            try:
                df_raw = pd.read_csv(caminho_completo, sep=";", encoding="latin1", header=None, low_memory=False)
                # Limpa o CABEÇALHO antes de atribuir
                df_raw.columns = [self._normalize_whitespace(col) for col in df_raw.iloc[0]]
                df = df_raw.drop(index=0).reset_index(drop=True)
                
                # *** ETAPA DE NORMALIZAÇÃO ***
                df = self._normalizar_colunas(df, var_name)
                    
                resultados[var_name] = df
                print(f"✅ {nome_arquivo} carregado ({len(df)} linhas).")
            except FileNotFoundError:
                print(f"❌ Arquivo não encontrado: {caminho_completo}. Execute 'obter_dados_brutos()' primeiro.")
                return None, None, None
            except Exception as e:
                print(f"❌ Erro ao carregar {nome_arquivo}: {e}")
                return None, None, None
        
        return resultados.get("viagem_df"), resultados.get("passagem_df"), resultados.get("trecho_df")


    def obter_dados_brutos(self):
        """Método principal: Baixa, descompacta e carrega os dados."""
        if not self._download_csv():
            return None, None, None
        if not self._descompactar_arquivo():
            return None, None, None
        return self.carregar_csvs()