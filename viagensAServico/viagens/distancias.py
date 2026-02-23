# viagens/distancias.py
import pandas as pd
import numpy as np
import os

class GerenciadorDistancias:
    """Responsável exclusivo por cruzar cidades com o Geocoder e calcular o GCD."""
    def __init__(self, geocoder, lookup_file='lookup_distancias_master.csv'):
        self.geocoder = geocoder
        self.lookup_file = lookup_file

    def executar(self, trecho_df):
        print("🔄 Processo 2: Gerenciando Distâncias...")
        if os.path.exists(self.lookup_file):
            df_master_lookup = pd.read_csv(self.lookup_file)
        else:
            df_master_lookup = pd.DataFrame(columns=['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)', 'Latitude_Origem', 'Longitude_Origem', 'Latitude_Destino', 'Longitude_Destino'])
        
        df_current_trechos = trecho_df[['Origem - Cidade', 'Destino - Cidade']].drop_duplicates().reset_index(drop=True)
        
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
            df_master_lookup.round(6).to_csv(self.lookup_file, index=False)
            print(f"   - Lookup atualizado. Total: {len(df_master_lookup)} trechos.")

        df_trechos_unicos = pd.merge(df_current_trechos, df_master_lookup, on=['Origem - Cidade', 'Destino - Cidade'], how='left')
        trecho_df = pd.merge(trecho_df, df_trechos_unicos[['Origem - Cidade', 'Destino - Cidade', 'Distância (GCD)']], on=['Origem - Cidade', 'Destino - Cidade'], how='left')
        trecho_df.dropna(subset=['Distância (GCD)'], inplace=True)
        print("   - ✅ Distâncias processadas.")
        
        return trecho_df