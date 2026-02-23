import requests
import math
import pandas as pd
import numpy as np
import time
import os
from stat import S_ISREG, ST_MODE

# --- CONFIGURAÇÕES GLOBAIS ---
# 🚨 Novo: Deriva o diretório do próprio script Python para garantir o caminho absoluto
DIRETORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CACHE_API_FILE = os.path.join(DIRETORIO_SCRIPT, 'coordenadas_api_cache.csv')

# O Excel (CodTrechos.xlsx) usa o caminho relativo do notebook
ARQUIVO_COORDENADAS_LOCAIS = "documentosWalleci/CodTrechos.xlsx"
NOME_SHEET_LOCAL = "ID_Cidades"
TEMPO_ESPERA = 1.1 
CHECKPOINT_LOTE = 50 

class Distancia:
    def __init__(self, user_agent='CalculadorDistador/1.0'):
        self.user_agent = user_agent
        self.mapa_coordenadas = None
        self._load_mapa_coordenadas()

    # --- MÉTODOS PRIVADOS DE GEOCÓDIGO E CACHE ---

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

    def _load_local_base(self):
        """Carrega a base de coordenadas do arquivo Excel (ID_Cidades)."""
        try:
            df_local = pd.read_excel(
                ARQUIVO_COORDENADAS_LOCAIS, 
                sheet_name=NOME_SHEET_LOCAL
            )
            df_local = df_local.rename(columns={
                'nome': 'Cidade', 'LATITUDE': 'Latitude', 'LONGITUDE': 'Longitude'
            })
            df_local = df_local[['Cidade', 'Latitude', 'Longitude']].copy()
            df_local['Cidade'] = df_local['Cidade'].astype(str).str.strip()
            return df_local
        except FileNotFoundError:
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])
        except Exception as e:
            print(f"❌ Erro ao carregar base local (planilha '{NOME_SHEET_LOCAL}'): {e}", flush=True)
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])

    def _load_api_cache(self):
        """Carrega o cache de coordenadas da API de forma tolerante a erros."""
        caminho_cache = CACHE_API_FILE
        
        if not os.path.exists(caminho_cache):
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])
        
        try:
            if os.stat(caminho_cache).st_size == 0:
                 return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])
            
            # ROBUSTEZ MÁXIMA: Tenta carregar. Se falhar, sugere que o usuário apague o arquivo.
            df_cache = pd.read_csv(caminho_cache, encoding='latin1', on_bad_lines='warn', engine='python')
            
            if df_cache.empty or 'Cidade' not in df_cache.columns:
                print(f"   -> Cache API '{caminho_cache}' sem colunas válidas. Pode ter apenas cabeçalho.", flush=True)
                return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])
                
            df_cache['Cidade'] = df_cache['Cidade'].astype(str).str.strip()
            print(f"   -> Cache API carregado com sucesso: {len(df_cache)} entradas.", flush=True)
            return df_cache
            
        except Exception as e:
            print(f"   ❌ ERRO FATAL ao ler o cache API '{caminho_cache}': {e}. Sugestão: Apague o arquivo.", flush=True)
            return pd.DataFrame(columns=['Cidade', 'Latitude', 'Longitude'])

    def _load_mapa_coordenadas(self):
        """Carrega o mapa completo de coordenadas (Cache API PRIMÁRIO + Base Local SECUNDÁRIO)."""
        df_cache_api = self._load_api_cache()
        df_local = self._load_local_base()
        
        self.mapa_coordenadas = pd.concat([df_cache_api, df_local], ignore_index=True)
        self.mapa_coordenadas = self.mapa_coordenadas.drop_duplicates(subset=['Cidade'], keep='first')
        
        print(f"✅ Gerenciador de Coordenadas inicializado. Mapa possui {len(self.mapa_coordenadas)} cidades.", flush=True)
        
    def obter_mapa_coordenadas_hibridas(self, cidades_list: list):
        """Implementação da lógica de geocoding com checkpoint."""
        cidades_list = [str(c).strip() for c in cidades_list if pd.notna(c)]
        cidades_list_df = pd.Series(np.unique(cidades_list)).to_frame(name='Cidade')

        df_faltantes = pd.merge(
            cidades_list_df,
            self.mapa_coordenadas[['Cidade']],
            on='Cidade',
            how='left',
            indicator=True
        ).query('_merge == "left_only"')
        cidades_para_geocoding = df_faltantes['Cidade'].tolist()

        if not cidades_para_geocoding:
            print("✅ Todas as cidades já estão no cache/base local. Não é necessário chamar a API.", flush=True)
            return self.mapa_coordenadas
        
        num_faltantes = len(cidades_para_geocoding)
        print(f"\n🔄 Geocoding API: {num_faltantes} cidades faltantes encontradas. Iniciando com Rate Limit (1.1s de espera).", flush=True)
        
        # 2. Geocoding com Checkpoint (Salva a cada 50)
        resultados_api = []
        start_time = time.time()
        
        # AQUI ESTÁ A CORREÇÃO: Verifica se o cabeçalho é necessário APENAS na primeira escrita.
        # CRÍTICO: Se o arquivo existir, o cabeçalho NÃO DEVE ser escrito novamente.
        header_needs_to_be_written = not os.path.exists(CACHE_API_FILE) or os.stat(CACHE_API_FILE).st_size == 0
        
        for i, cidade in enumerate(cidades_para_geocoding):
            
            if i % 10 == 0 or i == 0:
                print(f"   -> Processando: {i}/{num_faltantes}. Cidade atual: {cidade}", flush=True)
            
            coord = self._obter_coordenadas_api(cidade)

            if coord:
                resultados_api.append(coord)
                
            # --- CHECKPOINT CRÍTICO: SALVA A CADA 50 ---
            if (i + 1) % CHECKPOINT_LOTE == 0 or (i + 1) == num_faltantes:
                
                if resultados_api:
                    df_novos_coords_lote = pd.DataFrame(resultados_api)
                    
                    # Salva no modo APPEND. O 'header' é controlado pela variável de controle.
                    df_novos_coords_lote.to_csv(
                        CACHE_API_FILE, 
                        index=False, 
                        mode='a', 
                        header=header_needs_to_be_written,
                        encoding='latin1'
                    )
                    
                    # Se o cabeçalho foi escrito, ele não precisa ser escrito novamente (nem que seja um checkpoint).
                    header_needs_to_be_written = False
                    
                    print(f"   >>> CHECKPOINT SALVO: {i + 1}/{num_faltantes} cidades processadas e salvas no disco.", flush=True)
                    
                    resultados_api = [] 
            # --- FIM DO CHECKPOINT ---
            
            time.sleep(TEMPO_ESPERA)
        
        
        # 3. Finalização: Fusão e Sobrescrita Total (Garantir o Cache Primário)
        df_cache_completo = self._load_api_cache()
        df_local = self._load_local_base()
        
        mapa_final = pd.concat([df_cache_completo, df_local], ignore_index=True)
        mapa_final = mapa_final.drop_duplicates(subset=['Cidade'], keep='first')

        mapa_final.to_csv(
            CACHE_API_FILE, 
            index=False, 
            mode='w', # Sobrescreve TUDO (API + Excel) para tornar o cache a fonte única.
            header=True, 
            encoding='latin1'
        )
        
        self.mapa_coordenadas = mapa_final
        
        print(f"✅ Cache FINAL sobrescrito. {len(mapa_final)} cidades totais. Tempo final: {time.time() - start_time:.2f}s.", flush=True)
        
        return self.mapa_coordenadas

    @staticmethod
    def calcular_haversine(lat1, lon1, lat2, lon2):
        """
        Calcula a Distância Haversine (GCD) de forma vetorizada (usando NumPy).
        O resultado é arredondado para o inteiro mais próximo (em km).
        """
        R = 6371.0 # Raio da Terra em km
        
        # Converte graus para radianos
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        # Lei Esférica dos Cossenos
        cos_c = np.sin(lat1) * np.sin(lat2) + np.cos(lat1) * np.cos(lat2) * np.cos(dlon)
        
        # Limita o argumento do arccos entre [-1, 1] (para estabilidade numérica)
        cos_c = np.clip(cos_c, -1.0, 1.0)
        
        c = np.arccos(cos_c) # Ângulo central em radianos
        
        distancia_km = R * c
        
        return distancia_km