# classes/processor.py
import pandas as pd
import numpy as np
import os
import json
from tqdm.auto import tqdm
# Importe usando o caminho relativo
from .geocoder import GeoCacheManager 

tqdm.pandas(desc="Processando Itinerários")

class ViagemProcessor:
    
    # --- Constantes do Processador ---
    MASTER_LOOKUP_FILE = 'lookup_distancias_master.csv' 
    MASTER_ITINERARIOS_FILE = 'itinerarios_master.jsonl'
    
    # Fatores de Emissão (EF) em kg CO2e / pass.km
    EF_ECO_MUITO_CURTA = 0.272576785 
    EF_ECO_CURTA = 0.182869354 
    EF_ECO_LONGA = 0.200108215
    
    LIMITE_DH = 600
    LIMITE_SH = 3700

    def __init__(self, ano: int, geocoder: GeoCacheManager):
        self.ano = ano
        self.geocoder = geocoder # Recebe a instância do geocoder
        
        self.pasta_saida = f'dadosViagens/dados_viagens{self.ano}'
        self.arquivo_master_out = os.path.join(self.pasta_saida, f'df_master_ALL_aereo_{self.ano}.csv')
        
        self.CORRECOES_FILE = 'correcoes_cidades.csv'
        
        # DataFrames de estado
        self.viagem_df = None
        self.passagem_df = None
        self.trecho_df = None
        self.df_trechos_unicos = None
        self.df_viagens_agregadas = None
        self.df_master = None
        
        print(f"ViagemProcessor: Pronto para processar o ano {self.ano} (TODAS as instituições)")
        print(f"  -> Arquivo de saída: {self.arquivo_master_out}")

    def load_data(self, viagem_df, passagem_df, trecho_df):
        """Recebe os DataFrames brutos do Downloader."""
        self.viagem_df = viagem_df.copy()
        self.passagem_df = passagem_df.copy()
        self.trecho_df = trecho_df.copy()
        print(f"  -> Dados brutos (viagem, passagem, trecho) carregados no processador.")

    # --- FUNÇÃO DE CARREGAMENTO DE CORREÇÕES MODIFICADA ---
    def _load_corrections_dict(self):
        """
        Carrega o dicionário de correções a partir de um arquivo CSV externo,
        lidando corretamente com vírgulas nos valores.
        """
        correcoes_dict = {}
        try:
            with open(self.CORRECOES_FILE, 'r', encoding='utf-8') as f:
                next(f) # Pula o cabeçalho 'Incorreto,Correto'
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Divide a linha APENAS na primeira vírgula
                    parts = line.split(',', 1) 
                    
                    if len(parts) == 2:
                        incorreto, correto = parts
                        
                        # Limpa aspas que podem ter sido usadas para 'escapar' a vírgula
                        incorreto = incorreto.strip().strip('"')
                        correto = correto.strip().strip('"')
                        
                        correcoes_dict[incorreto] = correto
                    else:
                        print(f"   - ⚠️ Linha de correção mal formatada ignorada: {line}")
            
            print(f"   - ✅ Dicionário de correções carregado com {len(correcoes_dict)} regras.")
            return correcoes_dict
            
        except FileNotFoundError:
            print(f"   - ⚠️ ATENÇÃO: Arquivo '{self.CORRECOES_FILE}' não encontrado.")
            print("   -    Nenhuma correção de cidade será aplicada.")
            return {} # Retorna um dicionário vazio
        except Exception as e:
            print(f"   - ❌ ERRO ao ler o arquivo de correções: {e}")
            return {}

    def _filter_and_clean(self):
        """Filtra e limpa os DataFrames (apenas aéreo, sem filtro de órgão)."""
        print("🔄 Processo 1: Filtrando e Limpando Dados...")
        COL_ID = 'Identificador do processo de viagem'
        
        # 1. Filtro de Integridade
        self.viagem_df[COL_ID] = self.viagem_df[COL_ID].astype(str).str.strip().str.zfill(21)
        self.passagem_df[COL_ID] = self.passagem_df[COL_ID].astype(str).str.strip().str.zfill(21)
        self.trecho_df[COL_ID] = self.trecho_df[COL_ID].astype(str).str.strip().str.zfill(21)

        ids_viagem = set(self.viagem_df[COL_ID].unique())
        ids_passagem = set(self.passagem_df[COL_ID].unique())
        ids_trecho = set(self.trecho_df[COL_ID].unique())
        
        ids_validos = ids_viagem.intersection(ids_passagem).intersection(ids_trecho)
        print(f"   - IDs válidos (presentes nos 3 arquivos): {len(ids_validos)}")
        
        self.viagem_df = self.viagem_df[self.viagem_df[COL_ID].isin(ids_validos)].copy()
        self.passagem_df = self.passagem_df[self.passagem_df[COL_ID].isin(ids_validos)].copy()
        self.trecho_df = self.trecho_df[self.trecho_df[COL_ID].isin(ids_validos)].copy()
        
        # 2. Filtro por Transporte
        self.trecho_df = self.trecho_df[
            (self.trecho_df['Meio de transporte'].astype(str).str.upper() == 'AÉREO')
        ].copy()
        print(f"   - Trechos filtrados (Apenas Aéreo): {len(self.trecho_df)}")

        # 3. Limpeza de Cidades
        self.trecho_df['Origem - Cidade'] = self.trecho_df['Origem - Cidade'].astype(str).str.strip()
        self.trecho_df['Destino - Cidade'] = self.trecho_df['Destino - Cidade'].astype(str).str.strip()
        
        correcoes = self._load_corrections_dict()
        if correcoes: 
            self.trecho_df['Origem - Cidade'] = self.trecho_df['Origem - Cidade'].replace(correcoes)
            self.trecho_df['Destino - Cidade'] = self.trecho_df['Destino - Cidade'].replace(correcoes)

        # 4. Filtro O!=D
        linhas_antes = len(self.trecho_df)
        self.trecho_df = self.trecho_df[self.trecho_df['Origem - Cidade'] != self.trecho_df['Destino - Cidade']].copy()
        print(f"   - Trechos O=D removidos: {linhas_antes - len(self.trecho_df)}")
        print(f"✅ Filtro e Limpeza concluídos. {len(self.trecho_df)} trechos válidos restantes.")
        
    def _process_distances(self):
        """Gerencia o lookup mestre e junta distâncias."""
        print("🔄 Processo 2: Gerenciando Distâncias (Lookup Mestre)...")
        
        # 1. Carregar Lookup Mestre
        if os.path.exists(self.MASTER_LOOKUP_FILE):
            df_master_lookup = pd.read_csv(self.MASTER_LOOKUP_FILE)
        else:
            df_master_lookup = pd.DataFrame(columns=['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)', 'Latitude_Origem', 'Longitude_Origem', 'Latitude_Destino', 'Longitude_Destino'])
        
        # 2. Identificar Trechos Únicos Atuais
        df_current_trechos = self.trecho_df[['Origem - Cidade', 'Destino - Cidade']].drop_duplicates().reset_index(drop=True)
        
        # 3. Encontrar Trechos Novos
        df_new_trechos = pd.merge(
            df_current_trechos,
            df_master_lookup,
            on=['Origem - Cidade', 'Destino - Cidade'],
            how='left',
            indicator=True
        ).query('_merge == "left_only"').drop(columns=['_merge'] + list(df_master_lookup.columns.drop(['Origem - Cidade', 'Destino - Cidade'])))
        
        print(f"   - {len(df_current_trechos)} trechos únicos nesta execução.")
        print(f"   - {len(df_new_trechos)} trechos novos a serem processados.")

        # 4. Processar Trechos Novos
        df_new_calculated = pd.DataFrame() 
        
        if not df_new_trechos.empty:
            cidades_origem = df_new_trechos['Origem - Cidade'].unique()
            cidades_destino = df_new_trechos['Destino - Cidade'].unique()
            lista_cidades_novas = np.unique(np.concatenate((cidades_origem, cidades_destino))).tolist()
            
            df_coords_map = self.geocoder.get_coordinates(lista_cidades_novas)
            
            df_new_trechos = pd.merge(df_new_trechos, df_coords_map.add_suffix('_Origem'), left_on='Origem - Cidade', right_on='Cidade_Origem', how='left')
            df_new_trechos = pd.merge(df_new_trechos, df_coords_map.add_suffix('_Destino'), left_on='Destino - Cidade', right_on='Cidade_Destino', how='left')
            
            df_new_trechos.dropna(subset=['Latitude_Origem', 'Latitude_Destino'], inplace=True)
            
            if not df_new_trechos.empty:
                df_new_trechos['Distância (GCD)'] = self.geocoder.calcular_haversine(
                    df_new_trechos['Latitude_Origem'].values, df_new_trechos['Longitude_Origem'].values,
                    df_new_trechos['Latitude_Destino'].values, df_new_trechos['Longitude_Destino'].values
                )
            
                df_new_calculated = df_new_trechos[['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)', 'Latitude_Origem', 'Longitude_Origem', 'Latitude_Destino', 'Longitude_Destino']]
            
            else:
                print("   - ⚠️ Nenhum trecho novo pôde ser calculado (falha no geocoding de todos).")

        # 5. Atualizar e Salvar Mestre
        if not df_new_calculated.empty:
            df_master_lookup = pd.concat([df_master_lookup, df_new_calculated], ignore_index=True).drop_duplicates(subset=['Origem - Cidade', 'Destino - Cidade'])
            df_master_lookup.round(6).to_csv(self.MASTER_LOOKUP_FILE, index=False)
            print(f"   - Lookup Mestre salvo. Total de {len(df_master_lookup)} trechos cacheados.")
        else:
            print("   - Nenhum trecho novo foi calculado, lookup mestre não foi alterado.")

        # 6. Criar tabela de lookup da execução atual
        self.df_trechos_unicos = pd.merge(
            df_current_trechos,
            df_master_lookup,
            on=['Origem - Cidade', 'Destino - Cidade'],
            how='left'
        )
        
        # 7. Juntar distâncias ao trecho_df principal
        self.trecho_df = pd.merge(
            self.trecho_df,
            self.df_trechos_unicos[['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)']],
            on=['Origem - Cidade', 'Destino - Cidade'],
            how='left'
        )
        
        nulos_pos_merge = self.trecho_df['Distância (GCD)'].isnull().sum()
        if nulos_pos_merge > 0:
            print(f"   - ⚠️ {nulos_pos_merge} trechos removidos por falha no geocoding (não estavam no cache).")
            self.trecho_df.dropna(subset=['Distância (GCD)'], inplace=True)
            
        print("✅ Distâncias processadas e juntadas.")

    def _aggregate_and_calculate_emissions(self):
        """Agrega viagens e calcula emissões."""
        print("🔄 Processo 3: Agregando Trechos e Calculando Emissões...")
        
        # 1. Agregação
        self.df_viagens_agregadas = self.trecho_df.groupby("Identificador do processo de viagem", as_index=False).agg(
            **{'Distância (GCD)': pd.NamedAgg(column='Distância (GCD)', aggfunc='sum'),
               'Origem - Cidade': pd.NamedAgg(column='Origem - Cidade', aggfunc='first'),
               'Destino - Cidade': pd.NamedAgg(column='Destino - Cidade', aggfunc='last'),
               'Total_Trechos': pd.NamedAgg(column='Origem - Cidade', aggfunc='count')
              }
        )
        print(f"   - {len(self.df_viagens_agregadas)} viagens aéreas únicas (totais) agregadas.")

        # 2. Cálculo de Emissões
        conditions = [
            self.df_viagens_agregadas['Distância (GCD)'].le(self.LIMITE_DH),
            (self.df_viagens_agregadas['Distância (GCD)'].gt(self.LIMITE_DH)) & (self.df_viagens_agregadas['Distância (GCD)'].le(self.LIMITE_SH)),
            self.df_viagens_agregadas['Distância (GCD)'].gt(self.LIMITE_SH)
        ]
        category_values = ['Muito Curta (Evitável)', 'Curta Distância', 'Longa Distância']
        ef_values = [self.EF_ECO_MUITO_CURTA, self.EF_ECO_CURTA, self.EF_ECO_LONGA]
        
        self.df_viagens_agregadas['Categoria Distância'] = np.select(conditions, category_values, default='Não Calculada')
        self.df_viagens_agregadas['EF Aplicado'] = np.select(conditions, ef_values, default=np.nan)
        
        self.df_viagens_agregadas['Emissões (KgCO2eq)'] = (self.df_viagens_agregadas['Distância (GCD)'] * self.df_viagens_agregadas['EF Aplicado']).round(4)
        
        print("✅ Agregação e Cálculo de Emissões concluídos.")
        
    def _build_master_file(self):
        """Junta todos os dados no df_master final."""
        print("🔄 Processo 4: Construindo Arquivo Mestre (ALL)...")
        
        viagem_df_unique = self.viagem_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        passagem_df_unique = self.passagem_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        
        colunas_viagem = [col for col in viagem_df_unique.columns if col not in ['Origem - Cidade', 'Destino - Cidade']]
        colunas_passagem = [col for col in passagem_df_unique.columns if col != "Identificador do processo de viagem"]

        self.df_master = pd.merge(
            self.df_viagens_agregadas,
            viagem_df_unique[colunas_viagem],
            on="Identificador do processo de viagem",
            how='left'
        )
        
        self.df_master = pd.merge(
            self.df_master,
            passagem_df_unique[colunas_passagem + ["Identificador do processo de viagem"]],
            on="Identificador do processo de viagem",
            how='left',
            suffixes=('', '_PASSAGEM')
        )
        
        # Arredondamento final
        self.df_master['Distância (GCD)'] = self.df_master['Distância (GCD)'].round().astype(int)
        self.df_master['Emissões (KgCO2eq)'] = self.df_master['Emissões (KgCO2eq)'].round().astype(int)
        
        print(f"✅ Arquivo Mestre (ALL) construído com {len(self.df_master)} linhas.")
        
    def save_master_file(self):
        """Salva o df_master gerado."""
        if self.df_master is not None and not self.df_master.empty:
            self.df_master.to_csv(self.arquivo_master_out, index=False)
            print(f"✅ Processo Concluído: Arquivo mestre (ALL) salvo em '{self.arquivo_master_out}'")
        else:
            print("⚠️ Arquivo Mestre está vazio ou não foi gerado. Nada foi salvo.")

    def process_all(self):
        """Executa o pipeline completo de processamento (para TODAS as viagens)."""
        if self.viagem_df is None:
            print("❌ Erro: Dados brutos não carregados. Chame 'load_data()' primeiro.")
            return
            
        self._filter_and_clean()
        
        if self.trecho_df.empty:
            print(f"⚠️ Nenhuma viagem AÉREA encontrada para o ano {self.ano}. Parando o processamento.")
            # Salva um arquivo mestre vazio
            self.df_master = pd.DataFrame(columns=['Identificador do processo de viagem', 'Distância (GCD)', 'Origem - Cidade', 'Destino - Cidade', 'Total_Trechos', 'Categoria Distância', 'EF Aplicado', 'Emissões (KgCO2eq)'])
            self.save_master_file()
            return
            
        self._process_distances()
        self._aggregate_and_calculate_emissions()
        self._build_master_file()
        self.save_master_file()