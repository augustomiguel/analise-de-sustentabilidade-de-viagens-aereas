# viagens/emissoes.py
import pandas as pd
import numpy as np

class CalculadoraEmissoes:
    """Responsável exclusivo por aplicar o Fator de Emissão (FE) baseado na distância."""
    def __init__(self):
        self.EF_ECO_MUITO_CURTA = 0.272576785 
        self.EF_ECO_CURTA = 0.182869354 
        self.EF_ECO_LONGA = 0.200108215
        self.LIMITE_DH = 600
        self.LIMITE_SH = 3700

    def executar(self, trecho_df):
        print("🔄 Processo 3: Calculando Emissões...")
        df_viagens_agregadas = trecho_df.groupby("Identificador do processo de viagem", as_index=False).agg(
            **{'Distância (GCD)': pd.NamedAgg(column='Distância (GCD)', aggfunc='sum'),
               'Origem - Cidade': pd.NamedAgg(column='Origem - Cidade', aggfunc='first'),
               'Destino - Cidade': pd.NamedAgg(column='Destino - Cidade', aggfunc='last'),
               'Total_Trechos': pd.NamedAgg(column='Origem - Cidade', aggfunc='count')}
        )

        conditions = [
            df_viagens_agregadas['Distância (GCD)'].le(self.LIMITE_DH),
            (df_viagens_agregadas['Distância (GCD)'].gt(self.LIMITE_DH)) & (df_viagens_agregadas['Distância (GCD)'].le(self.LIMITE_SH)),
            df_viagens_agregadas['Distância (GCD)'].gt(self.LIMITE_SH)
        ]
        
        df_viagens_agregadas['Categoria Distância'] = np.select(conditions, ['Muito Curta (Evitável)', 'Curta Distância', 'Longa Distância'], default='Não Calculada')
        df_viagens_agregadas['EF Aplicado'] = np.select(conditions, [self.EF_ECO_MUITO_CURTA, self.EF_ECO_CURTA, self.EF_ECO_LONGA], default=np.nan)
        df_viagens_agregadas['Emissões (KgCO2eq)'] = (df_viagens_agregadas['Distância (GCD)'] * df_viagens_agregadas['EF Aplicado']).round(4)
        df_viagens_agregadas['Emissões (tCO2eq)'] = (df_viagens_agregadas['Emissões (KgCO2eq)'] / 1000).round(4)

        print("   - ✅ Emissões calculadas.")
        return df_viagens_agregadas