# viagens/geocoder.py
import requests
import math
import pandas as pd
import numpy as np
import time
import os

class GeoCacheManager:
    # Caminho para o cache principal da API (salvo na raiz do projeto)
    CACHE_API_FILE = 'coordenadas_api_cache.csv'
    
    # Caminho para o log de cidades não encontradas (Erros/Typos)
    LOG_FALTANTES_FILE = 'cidades_nao_encontradas.csv'
    
    # Caminho para a base local (Excel)
    ARQUIVO_COORDENADAS_LOCAIS = "../documentosWalleci/CodTrechos.xlsx"
    NOME_SHEET_LOCAL = "ID_Cidades"
    
    TEMPO_ESPERA = 1.1 
    CHECKPOINT_LOTE = 50 

    def __init__(self, user_agent='SustentabilidadeApp/1.0'):
        self.user_agent = user_agent
        self.mapa_coordenadas = None
        self.cidades_nao_encontradas = set()
        
        # Carrega os caches na memória
        self._load_cidades_nao_encontradas()
        self._load_mapa_coordenadas()

    def _load_cidades_nao_encontradas(self):
        """Carrega a lista de cidades que a API já falhou em encontrar para economizar tempo."""
        if os.path.exists(self.LOG_FALTANTES_FILE):
            try:
                df_faltantes = pd.read_csv(self.LOG_FALTANTES_FILE, encoding='utf-8')
                if 'Cidade' in df_faltantes.columns:
                    self.cidades_nao_encontradas = set(df_faltantes['Cidade'].astype(str).str.strip())
                    print(f"   -> Cache de Falhas carregado: {len(self.cidades_nao_encontradas)} cidades ignoradas.", flush=True)
            except Exception as e:
                print(f"   ❌ Erro ao ler log de falhas: {e}")
        else:
            self.cidades_nao_encontradas = set()

    def _registrar_falha(self, cidade):
        """Salva a cidade no log de não encontradas para o usuário corrigir depois."""
        self.cidades_nao_encontradas.add(cidade)
        arquivo_existe = os.path.exists(self.LOG_FALTANTES_FILE)
        try:
            with open(self.LOG_FALTANTES_FILE, 'a', encoding='utf-8') as f:
                if not arquivo_existe:
                    f.write("Cidade\n") # Escreve o cabeçalho se o arquivo for novo
                f.write(f'"{cidade}"\n')
        except Exception as e:
            print(f"   ❌ Erro ao escrever no log de falhas: {e}")

    def _load_local_base(self):
        """Carrega a base de coordenadas do arquivo Excel (ID_Cidades)."""
        try:
            df_local = pd.read_excel(
                self.ARQUIVO_COORDENADAS_LOCAIS, 
                sheet_name=self.NOME_SHEET_LOCAL
            )
            df_local = df_local.rename(columns={
                'nome': 'Cidade', 'LATITUDE': 'Latitude', 'LONGITUDE': 'Longitude'
            })
            df_local = df_local[['Cidade', 'Latitude', 'Longitude']].copy()
            df_local['Cidade'] = df_local['Cidade'].astype(str).str.strip()
            return df_local
        except FileNotFoundError:
            print("   - Aviso: Arquivo Excel de base local não encontrado. Usando apenas cache da API.")
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])
        except Exception as e:
            print(f"   - ❌ Erro ao carregar base local (planilha '{self.NOME_SHEET_LOCAL}'): {e}", flush=True)
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])

    def _load_api_cache(self):
        """Carrega o cache de coordenadas da API de forma tolerante a erros."""
        if not os.path.exists(self.CACHE_API_FILE) or os.stat(self.CACHE_API_FILE).st_size == 0:
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])
        
        try:
            df_cache = pd.read_csv(self.CACHE_API_FILE, encoding='latin1', on_bad_lines='warn', engine='python')
            if df_cache.empty or 'Cidade' not in df_cache.columns:
                return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])
                
            df_cache['Cidade'] = df_cache['Cidade'].astype(str).str.strip()
            print(f"   -> Cache API carregado com sucesso: {len(df_cache)} entradas.", flush=True)
            return df_cache
            
        except Exception as e:
            print(f"   ❌ ERRO FATAL ao ler o cache API '{self.CACHE_API_FILE}': {e}. Sugestão: Apague o arquivo.", flush=True)
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])

    def _load_mapa_coordenadas(self):
        """Carrega o mapa completo de coordenadas (Cache API PRIMÁRIO + Base Local SECUNDÁRIO)."""
        df_cache_api = self._load_api_cache()
        df_local = self._load_local_base()
        
        dfs_para_concatenar = [df for df in [df_cache_api, df_local] if not df.empty]

        if dfs_para_concatenar:
            self.mapa_coordenadas = pd.concat(dfs_para_concatenar, ignore_index=True)
        else:
            self.mapa_coordenadas = pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])

        self.mapa_coordenadas = self.mapa_coordenadas.drop_duplicates(subset=['Cidade'], keep='first')
        print(f"✅ GeoCacheManager: Mapa de coordenadas inicializado com {len(self.mapa_coordenadas)} cidades válidas.", flush=True)

    def _obter_coordenadas_api(self, local):
        """Método privado para obter coordenadas de um local via API."""
        try:
            url = f"https://nominatim.openstreetmap.org/search?format=json&q={local}&limit=1"
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=5) 
            response.raise_for_status()
            dados = response.json()
            if dados:
                resultado = dados[0]
                return {
                    'Cidade': local,
                    'Latitude': float(resultado['lat']),
                    'Longitude': float(resultado['lon'])
                }
            return None
        except Exception:
            return None

    def get_coordinates(self, cidades_list: list):
        """
        Garante que todas as cidades na lista tenham coordenadas.
        Consulta a API apenas se a cidade não estiver no cache E não estiver no log de falhas.
        """
        cidades_list = [str(c).strip() for c in cidades_list if pd.notna(c)]
        cidades_df_unico = pd.DataFrame(np.unique(cidades_list), columns=['Cidade'])

        # Cidades que já temos coordenada
        df_conhecidas = pd.merge(
            cidades_df_unico,
            self.mapa_coordenadas,
            on='Cidade',
            how='inner'
        )
        
        cidades_conhecidas = set(df_conhecidas['Cidade'])
        
        # Filtra cidades: Não tem coordenada AND Não tentamos e falhamos antes
        cidades_para_geocoding = [
            c for c in cidades_df_unico['Cidade'] 
            if c not in cidades_conhecidas and c not in self.cidades_nao_encontradas
        ]
        
        if not cidades_para_geocoding:
            print("   -> Geocoding: Todas as cidades já estão no cache ou foram marcadas como falhas.", flush=True)
            return df_conhecidas

        num_faltantes = len(cidades_para_geocoding)
        print(f"\n   -> 🔄 Geocoding API: {num_faltantes} cidades desconhecidas. Iniciando consulta ({self.TEMPO_ESPERA}s/req).", flush=True)
        
        resultados_api = []
        header_needs_to_be_written = not os.path.exists(self.CACHE_API_FILE) or os.stat(self.CACHE_API_FILE).st_size == 0
        
        for i, cidade in enumerate(cidades_para_geocoding):
            
            if i % 10 == 0 or i == 0:
                print(f"      -> Processando: {i}/{num_faltantes}. Cidade: {cidade}", flush=True)
            
            coord = self._obter_coordenadas_api(cidade)

            if coord:
                resultados_api.append(coord)
            else:
                # SE A API NÃO ACHOU, ANOTA NO LOG DE FALHAS PARA CORREÇÃO POSTERIOR
                self._registrar_falha(cidade)
                print(f"      ⚠️ Não encontrada: {cidade} (Salva no log de falhas)")
                
            # Checkpoint: Salva em lote para não perder tudo se der erro
            if (i + 1) % self.CHECKPOINT_LOTE == 0 or (i + 1) == num_faltantes:
                if resultados_api:
                    df_novos_coords_lote = pd.DataFrame(resultados_api)
                    df_novos_coords_lote.to_csv(
                        self.CACHE_API_FILE, 
                        index=False, 
                        mode='a', 
                        header=header_needs_to_be_written,
                        encoding='latin1'
                    )
                    header_needs_to_be_written = False # Só escreve o cabeçalho uma vez
                    print(f"      >>> CHECKPOINT SALVO: {len(resultados_api)} novas cidades válidas no cache.", flush=True)
                    
                    # Adiciona ao mapa de coordenadas em memória
                    self.mapa_coordenadas = pd.concat([self.mapa_coordenadas, df_novos_coords_lote], ignore_index=True)
                    self.mapa_coordenadas.drop_duplicates(subset=['Cidade'], keep='last', inplace=True)
                    resultados_api = [] 
            
            time.sleep(self.TEMPO_ESPERA)
        
        print(f"   -> ✅ Geocoding API concluído.", flush=True)
        
        # Retorna o DataFrame completo
        df_final_coords = pd.merge(
            cidades_df_unico,
            self.mapa_coordenadas,
            on='Cidade',
            how='left'
        )
        return df_final_coords

    @staticmethod
    def calcular_haversine(lat1, lon1, lat2, lon2):
        """Calcula a Distância Haversine (GCD) de forma vetorizada (NumPy)."""
        R = 6371.0 # Raio da Terra em km
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distancia_km = R * c
        return distancia_km