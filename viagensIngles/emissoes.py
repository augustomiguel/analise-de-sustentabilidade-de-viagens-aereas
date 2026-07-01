# travels/emissoes.py
import pandas as pd
import numpy as np

class EmissionsCalculator:
    """Exclusively responsible for applying the Emission Factor (EF) based on distance."""
    def __init__(self):
        self.EF_ECO_VERY_SHORT = 0.272576785 
        self.EF_ECO_SHORT = 0.182869354 
        self.EF_ECO_LONG = 0.200108215
        self.DH_LIMIT = 600
        self.SH_LIMIT = 3700

    def execute(self, segment_df):
        print("🔄 Process 3: Calculating Emissions...")
        df_aggregated_travels = segment_df.groupby("Identificador do processo de viagem", as_index=False).agg(
            **{'Distance (GCD)': pd.NamedAgg(column='Distance (GCD)', aggfunc='sum'),
               'Origem - Cidade': pd.NamedAgg(column='Origem - Cidade', aggfunc='first'),
               'Destino - Cidade': pd.NamedAgg(column='Destino - Cidade', aggfunc='last'),
               'Total_Segments': pd.NamedAgg(column='Origem - Cidade', aggfunc='count')}
        )

        conditions = [
            df_aggregated_travels['Distance (GCD)'].le(self.DH_LIMIT),
            (df_aggregated_travels['Distance (GCD)'].gt(self.DH_LIMIT)) & (df_aggregated_travels['Distance (GCD)'].le(self.SH_LIMIT)),
            df_aggregated_travels['Distance (GCD)'].gt(self.SH_LIMIT)
        ]
        
        df_aggregated_travels['Distance Category'] = np.select(conditions, ['Very Short (Avoidable)', 'Short Distance', 'Long Distance'], default='Not Calculated')
        df_aggregated_travels['Applied EF'] = np.select(conditions, [self.EF_ECO_VERY_SHORT, self.EF_ECO_SHORT, self.EF_ECO_LONG], default=np.nan)
        df_aggregated_travels['Emissions (KgCO2eq)'] = (df_aggregated_travels['Distance (GCD)'] * df_aggregated_travels['Applied EF']).round(4)
        df_aggregated_travels['Emissions (tCO2eq)'] = (df_aggregated_travels['Emissions (KgCO2eq)'] / 1000).round(4)

        print("   - ✅ Emissions calculated.")
        return df_aggregated_travels