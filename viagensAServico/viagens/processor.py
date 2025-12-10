# viagens/processor.py
import pandas as pd
import numpy as np
import os
import json
from tqdm.auto import tqdm
from .geocoder import GeoCacheManager 

tqdm.pandas(desc="Processando Itinerários")

class ViagemProcessor:
    
    MASTER_LOOKUP_FILE = 'lookup_distancias_master.csv' 
    MASTER_ITINERARIOS_FILE = 'itinerarios_master.jsonl'
    
    EF_ECO_MUITO_CURTA = 0.272576785 
    EF_ECO_CURTA = 0.182869354 
    EF_ECO_LONGA = 0.200108215
    
    LIMITE_DH = 600
    LIMITE_SH = 3700

    def __init__(self, ano: int, geocoder: GeoCacheManager):
        self.ano = ano
        self.geocoder = geocoder
        
        self.pasta_saida = f'dadosViagens/dados_viagens{self.ano}'
        self.arquivo_master_out = os.path.join(self.pasta_saida, f'df_master_ALL_aereo_{self.ano}.csv')
        self.CORRECOES_FILE = 'correcoes_cidades.csv'
        
        self.viagem_df = None
        self.passagem_df = None
        self.trecho_df = None
        self.df_trechos_unicos = None
        self.df_viagens_agregadas = None
        self.df_master = None
        
        print(f"ViagemProcessor: Pronto para processar o ano {self.ano} (TODAS as instituições)")

    def load_data(self, viagem_df, passagem_df, trecho_df):
        self.viagem_df = viagem_df.copy()
        self.passagem_df = passagem_df.copy()
        self.trecho_df = trecho_df.copy()
        print(f"  -> Dados brutos carregados no processador.")

    def _load_corrections_dict(self):
        correcoes_dict = {}
        try:
            with open(self.CORRECOES_FILE, 'r', encoding='utf-8') as f:
                next(f)
                for line in f:
                    line = line.strip()
                    if not line: continue
                    parts = line.split(',', 1) 
                    if len(parts) == 2:
                        incorreto, correto = parts
                        correcoes_dict[incorreto.strip().strip('"')] = correto.strip().strip('"')
            print(f"   - ✅ Dicionário de correções carregado: {len(correcoes_dict)} regras.")
            return correcoes_dict
        except Exception:
            return {}

    def _filter_and_clean(self):
        print("🔄 Processo 1: Filtrando e Limpando Dados...")
        COL_ID = 'Identificador do processo de viagem'
        
        self.viagem_df[COL_ID] = self.viagem_df[COL_ID].astype(str).str.strip().str.zfill(21)
        self.passagem_df[COL_ID] = self.passagem_df[COL_ID].astype(str).str.strip().str.zfill(21)
        self.trecho_df[COL_ID] = self.trecho_df[COL_ID].astype(str).str.strip().str.zfill(21)

        ids_viagem = set(self.viagem_df[COL_ID].unique())
        ids_passagem = set(self.passagem_df[COL_ID].unique())
        ids_trecho = set(self.trecho_df[COL_ID].unique())
        
        ids_validos = ids_viagem.intersection(ids_passagem).intersection(ids_trecho)
        
        self.viagem_df = self.viagem_df[self.viagem_df[COL_ID].isin(ids_validos)].copy()
        self.passagem_df = self.passagem_df[self.passagem_df[COL_ID].isin(ids_validos)].copy()
        self.trecho_df = self.trecho_df[self.trecho_df[COL_ID].isin(ids_validos)].copy()
        
        self.trecho_df = self.trecho_df[
            (self.trecho_df['Meio de transporte'].astype(str).str.upper() == 'AÉREO')
        ].copy()

        self.trecho_df['Origem - Cidade'] = self.trecho_df['Origem - Cidade'].astype(str).str.strip()
        self.trecho_df['Destino - Cidade'] = self.trecho_df['Destino - Cidade'].astype(str).str.strip()
        
        correcoes = self._load_corrections_dict()
        if correcoes: 
            self.trecho_df['Origem - Cidade'] = self.trecho_df['Origem - Cidade'].replace(correcoes)
            self.trecho_df['Destino - Cidade'] = self.trecho_df['Destino - Cidade'].replace(correcoes)

        self.trecho_df = self.trecho_df[self.trecho_df['Origem - Cidade'] != self.trecho_df['Destino - Cidade']].copy()
        print(f"✅ Filtro concluído. {len(self.trecho_df)} trechos válidos.")
        
    def _process_distances(self):
        print("🔄 Processo 2: Gerenciando Distâncias...")
        if os.path.exists(self.MASTER_LOOKUP_FILE):
            df_master_lookup = pd.read_csv(self.MASTER_LOOKUP_FILE)
        else:
            df_master_lookup = pd.DataFrame(columns=['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)', 'Latitude_Origem', 'Longitude_Origem', 'Latitude_Destino', 'Longitude_Destino'])
        
        df_current_trechos = self.trecho_df[['Origem - Cidade', 'Destino - Cidade']].drop_duplicates().reset_index(drop=True)
        
        df_new_trechos = pd.merge(
            df_current_trechos, df_master_lookup, on=['Origem - Cidade', 'Destino - Cidade'], how='left', indicator=True
        ).query('_merge == "left_only"').drop(columns=['_merge'] + list(df_master_lookup.columns.drop(['Origem - Cidade', 'Destino - Cidade'])))
        
        df_new_calculated = pd.DataFrame()
        
        if not df_new_trechos.empty:
            cidades = np.unique(np.concatenate((df_new_trechos['Origem - Cidade'].unique(), df_new_trechos['Destino - Cidade'].unique()))).tolist()
            df_coords = self.geocoder.get_coordinates(cidades)
            
            df_new_trechos = pd.merge(df_new_trechos, df_coords.add_suffix('_Origem'), left_on='Origem - Cidade', right_on='Cidade_Origem', how='left')
            df_new_trechos = pd.merge(df_new_trechos, df_coords.add_suffix('_Destino'), left_on='Destino - Cidade', right_on='Cidade_Destino', how='left')
            df_new_trechos.dropna(subset=['Latitude_Origem', 'Latitude_Destino'], inplace=True)
            
            if not df_new_trechos.empty:
                df_new_trechos['Distância (GCD)'] = self.geocoder.calcular_haversine(
                    df_new_trechos['Latitude_Origem'].values, df_new_trechos['Longitude_Origem'].values,
                    df_new_trechos['Latitude_Destino'].values, df_new_trechos['Longitude_Destino'].values
                )
                df_new_calculated = df_new_trechos[['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)', 'Latitude_Origem', 'Longitude_Origem', 'Latitude_Destino', 'Longitude_Destino']]

        if not df_new_calculated.empty:
            df_master_lookup = pd.concat([df_master_lookup, df_new_calculated], ignore_index=True).drop_duplicates(subset=['Origem - Cidade', 'Destino - Cidade'])
            df_master_lookup.round(6).to_csv(self.MASTER_LOOKUP_FILE, index=False)
            print(f"   - Lookup atualizado. Total: {len(df_master_lookup)} trechos.")

        self.df_trechos_unicos = pd.merge(df_current_trechos, df_master_lookup, on=['Origem - Cidade', 'Destino - Cidade'], how='left')
        self.trecho_df = pd.merge(self.trecho_df, self.df_trechos_unicos[['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)']], on=['Origem - Cidade', 'Destino - Cidade'], how='left')
        self.trecho_df.dropna(subset=['Distância (GCD)'], inplace=True)
        print("✅ Distâncias processadas.")

    def _aggregate_and_calculate_emissions(self):
        print("🔄 Processo 3: Calculando Emissões...")
        self.df_viagens_agregadas = self.trecho_df.groupby("Identificador do processo de viagem", as_index=False).agg(
            **{'Distância (GCD)': pd.NamedAgg(column='Distância (GCD)', aggfunc='sum'),
               'Origem - Cidade': pd.NamedAgg(column='Origem - Cidade', aggfunc='first'),
               'Destino - Cidade': pd.NamedAgg(column='Destino - Cidade', aggfunc='last'),
               'Total_Trechos': pd.NamedAgg(column='Origem - Cidade', aggfunc='count')}
        )

        conditions = [
            self.df_viagens_agregadas['Distância (GCD)'].le(self.LIMITE_DH),
            (self.df_viagens_agregadas['Distância (GCD)'].gt(self.LIMITE_DH)) & (self.df_viagens_agregadas['Distância (GCD)'].le(self.LIMITE_SH)),
            self.df_viagens_agregadas['Distância (GCD)'].gt(self.LIMITE_SH)
        ]
        self.df_viagens_agregadas['Categoria Distância'] = np.select(conditions, ['Muito Curta (Evitável)', 'Curta Distância', 'Longa Distância'], default='Não Calculada')
        self.df_viagens_agregadas['EF Aplicado'] = np.select(conditions, [self.EF_ECO_MUITO_CURTA, self.EF_ECO_CURTA, self.EF_ECO_LONGA], default=np.nan)
        self.df_viagens_agregadas['Emissões (KgCO2eq)'] = (self.df_viagens_agregadas['Distância (GCD)'] * self.df_viagens_agregadas['EF Aplicado']).round(4)
        print("✅ Emissões calculadas.")

    # --- CLASSIFICAÇÃO ATUALIZADA (COM MOTIVO PARA ALUNOS) ---
    def _classificar_vinculo(self, row):
        """
        Classifica o viajante em Professor, Servidor, Externo, Acadêmico ou Vazio.
        Usa Cargo e Motivo para desambiguação.
        """
        cargo = row.get('Cargo')
        motivo = row.get('Motivo')
        
        # Normaliza strings
        cargo_str = str(cargo).upper().strip() if pd.notna(cargo) else ""
        motivo_str = str(motivo).upper().strip() if pd.notna(motivo) else ""
        
        # Ignora strings vazias ou 'NAN'
        if cargo_str == 'NAN' or cargo_str == 'SEM INFORMAÇÃO' or cargo_str == '':
            cargo_str = None
            
        # 1. Professores (Prioridade Máxima pelo Cargo)
        if cargo_str and any(k in cargo_str for k in ['PROFESSOR', 'DOCENTE', 'MAGISTERIO', 'VISITANTE', 'REGENTE']):
            return 'Professor'

        # 2. Acadêmicos (Pelo Cargo)
        if cargo_str and any(k in cargo_str for k in ['ESTUDANTE', 'DISCENTE', 'ALUNO', 'ACADEMICO', 'MESTRANDO', 'DOUTORANDO', 'BOLSISTA', 'ESTAGIARIO', 'POS-GRADUACAO']):
            return 'Acadêmico'

        # 3. Externos (Pelo Cargo)
        if cargo_str and any(k in cargo_str for k in ['COLABORADOR', 'CONVIDADO', 'EXTERNO', 'CONSULTOR']):
            return 'Externo'

        # 4. Verificação por MOTIVO (Se cargo não for conclusivo)
        if motivo_str:
            # Acadêmicos no Motivo
            if any(k in motivo_str for k in ['ESTUDANTE', 'DISCENTE', 'ALUNO', 'ACADEMICO', 'MESTRANDO', 'DOUTORANDO', 'BOLSISTA', 'APRESENTAÇÃO DE TRABALHO']):
                 return 'Acadêmico'
            
            # Externos no Motivo
            if any(k in motivo_str for k in ['CONVIDADO', 'COLABORADOR', 'PALESTRANTE', 'EXTERNO', 'MEMBRO EXTERNO', 'BANCA EXAMINADORA']):
                 return 'Externo'

        # 5. Servidores (Se tem cargo válido e não caiu nos filtros acima, é Servidor)
        if cargo_str:
             return 'Servidor'

        # 6. Se falhar tudo
        return 'Não Informado'

    def _build_master_file(self):
        print("🔄 Processo 4: Construindo Arquivo Mestre (ALL)...")
        viagem_df_unique = self.viagem_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        passagem_df_unique = self.passagem_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        
        colunas_viagem = [col for col in viagem_df_unique.columns if col not in ['Origem - Cidade', 'Destino - Cidade']]
        colunas_passagem = [col for col in passagem_df_unique.columns if col != "Identificador do processo de viagem"]

        self.df_master = pd.merge(self.df_viagens_agregadas, viagem_df_unique[colunas_viagem], on="Identificador do processo de viagem", how='left')
        self.df_master = pd.merge(self.df_master, passagem_df_unique[colunas_passagem + ["Identificador do processo de viagem"]], on="Identificador do processo de viagem", how='left', suffixes=('', '_PASSAGEM'))
        
        self.df_master['Distância (GCD)'] = self.df_master['Distância (GCD)'].round().astype(int)
        self.df_master['Emissões (KgCO2eq)'] = self.df_master['Emissões (KgCO2eq)'].round().astype(int)
        
        print("   - Classificando vínculos (Professor / Servidor / Acadêmico / Externo)...")
        # Aplica a função de classificação atualizada
        self.df_master['Vínculo'] = self.df_master.apply(self._classificar_vinculo, axis=1)
        
        print("   -> Contagem de Vínculos:")
        print(self.df_master['Vínculo'].value_counts())
        
        print(f"✅ Arquivo Mestre (ALL) construído com {len(self.df_master)} linhas.")
        
    def save_master_file(self):
        if self.df_master is not None and not self.df_master.empty:
            self.df_master.to_csv(self.arquivo_master_out, index=False)
            print(f"✅ Processo Concluído: Arquivo mestre salvo em '{self.arquivo_master_out}'")
        else:
            print("⚠️ Arquivo Mestre vazio.")

    def process_all(self):
        if self.viagem_df is None: return
        self._filter_and_clean()
        if self.trecho_df.empty:
            self.df_master = pd.DataFrame(columns=['Identificador do processo de viagem', 'Vínculo'])
            self.save_master_file()
            return
        self._process_distances()
        self._aggregate_and_calculate_emissions()
        self._build_master_file()
        self.save_master_file()