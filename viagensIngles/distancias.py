# travels/distancias.py
import pandas as pd
import numpy as np
import os

class DistanceManager:
    """Exclusively responsible for crossing cities with the Geocoder and calculating GCD."""
    def __init__(self, geocoder, lookup_file='lookup_distances_master.csv'):
        self.geocoder = geocoder
        self.lookup_file = lookup_file

    def execute(self, segment_df):
        print("🔄 Process 2: Managing Distances...")
        if os.path.exists(self.lookup_file):
            df_master_lookup = pd.read_csv(self.lookup_file)
        else:
            df_master_lookup = pd.DataFrame(columns=['Origem - Cidade', 'Destino - Cidade', 'Distance (GCD)', 'Latitude_Origin', 'Longitude_Origin', 'Latitude_Destination', 'Longitude_Destination'])
        
        df_current_segments = segment_df[['Origem - Cidade', 'Destino - Cidade']].drop_duplicates().reset_index(drop=True)
        
        df_new_segments = pd.merge(
            df_current_segments, df_master_lookup, on=['Origem - Cidade', 'Destino - Cidade'], how='left', indicator=True
        ).query('_merge == "left_only"').drop(columns=['_merge'] + list(df_master_lookup.columns.drop(['Origem - Cidade', 'Destino - Cidade'])))
        
        df_new_calculated = pd.DataFrame()
        
        if not df_new_segments.empty:
            cities = np.unique(np.concatenate((df_new_segments['Origem - Cidade'].unique(), df_new_segments['Destino - Cidade'].unique()))).tolist()
            df_coords = self.geocoder.get_coordinates(cities)
            
            df_new_segments = pd.merge(df_new_segments, df_coords.add_suffix('_Origin'), left_on='Origem - Cidade', right_on='City_Origin', how='left')
            df_new_segments = pd.merge(df_new_segments, df_coords.add_suffix('_Destination'), left_on='Destino - Cidade', right_on='City_Destination', how='left')
            df_new_segments.dropna(subset=['Latitude_Origin', 'Latitude_Destination'], inplace=True)
            
            if not df_new_segments.empty:
                df_new_segments['Distance (GCD)'] = self.geocoder.calculate_haversine(
                    df_new_segments['Latitude_Origin'].values, df_new_segments['Longitude_Origin'].values,
                    df_new_segments['Latitude_Destination'].values, df_new_segments['Longitude_Destination'].values
                )
                df_new_calculated = df_new_segments[['Origem - Cidade', 'Destino - Cidade', 'Distance (GCD)', 'Latitude_Origin', 'Longitude_Origin', 'Latitude_Destination', 'Longitude_Destination']]

        if not df_new_calculated.empty:
            df_master_lookup = pd.concat([df_master_lookup, df_new_calculated], ignore_index=True).drop_duplicates(subset=['Origem - Cidade', 'Destino - Cidade'])
            df_master_lookup.round(6).to_csv(self.lookup_file, index=False)
            print(f"   - Lookup updated. Total: {len(df_master_lookup)} segments.")

        df_unique_segments = pd.merge(df_current_segments, df_master_lookup, on=['Origem - Cidade', 'Destino - Cidade'], how='left')
        segment_df = pd.merge(segment_df, df_unique_segments[['Origem - Cidade', 'Destino - Cidade', 'Distance (GCD)']], on=['Origem - Cidade', 'Destino - Cidade'], how='left')
        segment_df.dropna(subset=['Distance (GCD)'], inplace=True)
        print("   - ✅ Distances processed.")
        
        return segment_df