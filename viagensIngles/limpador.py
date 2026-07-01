# travels/limpador.py
import pandas as pd

class DataCleaner:
    """Exclusively responsible for cleaning strings, applying the dictionary, and merging data."""
    def __init__(self, corrections_file='cities_corrections.csv'):
        self.corrections_file = corrections_file

    def _load_corrections_dict(self):
        corrections_dict = {}
        try:
            with open(self.corrections_file, 'r', encoding='utf-8') as f:
                next(f)
                for line in f:
                    line = line.strip()
                    if not line: continue
                    parts = line.split(',', 1) 
                    if len(parts) == 2:
                        incorrect, correct = parts
                        corrections_dict[incorrect.strip().strip('"')] = correct.strip().strip('"')
            print(f"   - ✅ Corrections dictionary loaded: {len(corrections_dict)} rules.")
            return corrections_dict
        except Exception:
            return {}

    def execute(self, travel_df, ticket_df, segment_df):
        print("🔄 Process 1: Filtering and Cleaning Data...")
        COL_ID = 'Identificador do processo de viagem'
        
        travel_df[COL_ID] = travel_df[COL_ID].astype(str).str.strip().str.zfill(21)
        ticket_df[COL_ID] = ticket_df[COL_ID].astype(str).str.strip().str.zfill(21)
        segment_df[COL_ID] = segment_df[COL_ID].astype(str).str.strip().str.zfill(21)

        travel_ids = set(travel_df[COL_ID].unique())
        ticket_ids = set(ticket_df[COL_ID].unique())
        segment_ids = set(segment_df[COL_ID].unique())
        
        valid_ids = travel_ids.intersection(ticket_ids).intersection(segment_ids)
        
        travel_df = travel_df[travel_df[COL_ID].isin(valid_ids)].copy()
        ticket_df = ticket_df[ticket_df[COL_ID].isin(valid_ids)].copy()
        segment_df = segment_df[segment_df[COL_ID].isin(valid_ids)].copy()
        
        segment_df = segment_df[
            (segment_df['Meio de transporte'].astype(str).str.upper() == 'AÉREO')
        ].copy()

        segment_df['Origem - Cidade'] = segment_df['Origem - Cidade'].astype(str).str.strip()
        segment_df['Destino - Cidade'] = segment_df['Destino - Cidade'].astype(str).str.strip()
        
        corrections = self._load_corrections_dict()
        if corrections: 
            segment_df['Origem - Cidade'] = segment_df['Origem - Cidade'].replace(corrections)
            segment_df['Destino - Cidade'] = segment_df['Destino - Cidade'].replace(corrections)

        segment_df = segment_df[segment_df['Origem - Cidade'] != segment_df['Destino - Cidade']].copy()
        print(f"   - ✅ Filter completed. {len(segment_df)} valid segments.")
        
        return travel_df, ticket_df, segment_df