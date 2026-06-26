# viagens/limpador.py
import pandas as pd

class LimpadorDados:
    """Responsável exclusivo por limpar strings, aplicar o dicionário e mesclar os dados."""
    def __init__(self, correcoes_file='correcoes_cidades.csv'):
        self.correcoes_file = correcoes_file

    def _load_corrections_dict(self):
        correcoes_dict = {}
        try:
            with open(self.correcoes_file, 'r', encoding='utf-8') as f:
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

    def executar(self, viagem_df, passagem_df, trecho_df):
        print("🔄 Processo 1: Filtrando e Limpando Dados...")
        COL_ID = 'Identificador do processo de viagem'
        
        viagem_df[COL_ID] = viagem_df[COL_ID].astype(str).str.strip().str.zfill(21)
        passagem_df[COL_ID] = passagem_df[COL_ID].astype(str).str.strip().str.zfill(21)
        trecho_df[COL_ID] = trecho_df[COL_ID].astype(str).str.strip().str.zfill(21)

        ids_viagem = set(viagem_df[COL_ID].unique())
        ids_passagem = set(passagem_df[COL_ID].unique())
        ids_trecho = set(trecho_df[COL_ID].unique())
        
        ids_validos = ids_viagem.intersection(ids_passagem).intersection(ids_trecho)
        
        viagem_df = viagem_df[viagem_df[COL_ID].isin(ids_validos)].copy()
        passagem_df = passagem_df[passagem_df[COL_ID].isin(ids_validos)].copy()
        trecho_df = trecho_df[trecho_df[COL_ID].isin(ids_validos)].copy()
        
        trecho_df = trecho_df[
            (trecho_df['Meio de transporte'].astype(str).str.upper() == 'AÉREO')
        ].copy()

        trecho_df['Origem - Cidade'] = trecho_df['Origem - Cidade'].astype(str).str.strip()
        trecho_df['Destino - Cidade'] = trecho_df['Destino - Cidade'].astype(str).str.strip()
        
        correcoes = self._load_corrections_dict()
        if correcoes: 
            trecho_df['Origem - Cidade'] = trecho_df['Origem - Cidade'].replace(correcoes)
            trecho_df['Destino - Cidade'] = trecho_df['Destino - Cidade'].replace(correcoes)

        trecho_df = trecho_df[trecho_df['Origem - Cidade'] != trecho_df['Destino - Cidade']].copy()
        print(f"   - ✅ Filtro concluído. {len(trecho_df)} trechos válidos.")
        
        return viagem_df, passagem_df, trecho_df