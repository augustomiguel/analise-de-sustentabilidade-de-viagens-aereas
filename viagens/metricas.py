import pandas as pd
import os

class CalculadoraMetricas:
    """
    Classe centralizada para cálculos matemáticos e regras de negócio do modelo PIBIC.
    Implementa as equações dos indicadores (ED, DF, IB) e as pontuações (Scores).
    """
    def __init__(self, ano):
        self.ano = ano
        
        # IPCA Oficial (IBGE) Acumulado para trazer tudo a Valor Presente (R$ de 2025)
        self.fatores_correcao = {
            2011: 2.2221, 2012: 2.0864, 2013: 1.9713, 2014: 1.8613,
            2015: 1.7492, 2016: 1.5805, 2017: 1.4870, 2018: 1.4444,
            2019: 1.3922, 2020: 1.3347, 2021: 1.2770, 2022: 1.1602,
            2023: 1.0967, 2024: 1.0483, 2025: 1.0000
        }

    def preparar_dados_numericos(self, df):
        """Prepara e limpa os dados brutos."""
        df_limpo = df.copy()
        
        if 'Período - Data de início' in df_limpo.columns:
            df_limpo['Data_Viagem'] = pd.to_datetime(df_limpo['Período - Data de início'], format='%d/%m/%Y', errors='coerce')
            df_limpo.dropna(subset=['Data_Viagem'], inplace=True)
            df_limpo['Mes_Num'] = df_limpo['Data_Viagem'].dt.month
            df_limpo['Mes_Ano'] = df_limpo['Mes_Num'].apply(lambda x: f"{self.ano}-{x:02d}")

        colunas_numericas = ['Distância (GCD)', 'Emissões (KgCO2eq)', 'Valor passagens']
        for col in colunas_numericas:
            if col in df_limpo.columns:
                df_limpo[col] = pd.to_numeric(df_limpo[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
                
        return df_limpo

    def calcular_resumo_mensal(self, df):
        """Gera o dataframe agrupado por mês para gráficos e planilhas."""
        df = self.preparar_dados_numericos(df)
        if df.empty: return pd.DataFrame()

        # APLICA INFLAÇÃO NOS GASTOS MENSAIS PARA VALOR PRESENTE (2025)
        fator_ano = self.fatores_correcao.get(self.ano, 1.0)
        df['Valor passagens'] = df['Valor passagens'] * fator_ano

        df_agrupado = df.groupby(['Mes_Ano', 'Mes_Num']).agg(
            Total_Distancia_Km = ('Distância (GCD)', 'sum'),
            Total_Emissoes_KgCO2eq = ('Emissões (KgCO2eq)', 'sum'),
            Total_Viagens = ('Identificador do processo de viagem', 'count'),
            Total_Passagens = ('Valor passagens', 'sum')
        ).reset_index()

        meses_template = pd.DataFrame({'Mes_Num': range(1, 13)})
        meses_template['Mes_Ano'] = meses_template['Mes_Num'].apply(lambda x: f"{self.ano}-{x:02d}")
        
        df_mensal = pd.merge(meses_template, df_agrupado, on=['Mes_Num', 'Mes_Ano'], how='left')
        df_mensal = df_mensal.infer_objects(copy=False).fillna(0)
        df_mensal['Total_Viagens'] = df_mensal['Total_Viagens'].astype(int)
        
        return df_mensal

    def calcular_baseline_dinamico(self, orgao: str, anos_processamento: list):
        """Calcula a linha de base com correção de IPCA lendo direto do Master."""
        if len(anos_processamento) < 2: return None
        anos_baseline = anos_processamento[:2]
        
        total_gasto, total_emissoes, total_distancia = 0, 0, 0
        anos_encontrados = 0

        for ano_base in anos_baseline:
            caminho_csv = os.path.join("dadosViagens", f"dados_viagens{ano_base}", f"df_master_{orgao}_aereo_{ano_base}.csv")
            if os.path.exists(caminho_csv):
                df = pd.read_csv(caminho_csv, low_memory=False)
                df = self.preparar_dados_numericos(df)
                
                fator_ano = self.fatores_correcao.get(ano_base, 1.0)
                soma_gasto = df['Valor passagens'].sum() * fator_ano
                
                total_gasto += soma_gasto
                total_emissoes += df['Emissões (KgCO2eq)'].sum()
                total_distancia += df['Distância (GCD)'].sum()
                anos_encontrados += 1

        if anos_encontrados == 0: return None

        return {
            'Anos_Utilizados': anos_baseline,
            'Gasto_Medio_Anual': total_gasto / anos_encontrados,
            'Emissoes_Medias_Anuais': total_emissoes / anos_encontrados,
            'Distancia_Media_Anual': total_distancia / anos_encontrados
        }

    def calcular_indicadores_e_scores(self, df_bruto, baseline):
        """Mapeia as fórmulas da Metodologia PIBIC (Níveis 4 e 5) e atribui a pontuação S (Nível 3)."""
        df = self.preparar_dados_numericos(df_bruto)
        total_viagens = len(df)
        
        if total_viagens == 0: return {}

        ed1_1_emissoes_totais = df['Emissões (KgCO2eq)'].sum()
        ed2_1_distancia_total = df['Distância (GCD)'].sum()
        
        viagens_muito_curtas = len(df[df['Distância (GCD)'] < 600])
        viagens_curtas = len(df[(df['Distância (GCD)'] >= 600) & (df['Distância (GCD)'] <= 3700)])
        viagens_longas = len(df[df['Distância (GCD)'] > 3700])

        df1_4_taxa_evitaveis = 0.0
        df1_5_taxa_urgentes = 0.0

        if 'Período - Data de fim' in df.columns:
            df['Data_Fim'] = pd.to_datetime(df['Período - Data de fim'], format='%d/%m/%Y', errors='coerce')
            df['Duracao_Dias'] = (df['Data_Fim'] - df['Data_Viagem']).dt.days
            viagens_0_1_dia = len(df[df['Duracao_Dias'] <= 1])
            df1_4_taxa_evitaveis = viagens_0_1_dia / total_viagens if total_viagens > 0 else 0

        coluna_urgencia = [col for col in df.columns if 'urgência' in col.lower() or 'urgente' in col.lower()]
        if coluna_urgencia:
            urgentes = len(df[df[coluna_urgencia[0]].astype(str).str.upper().isin(['SIM', 'S', 'TRUE'])])
            df1_5_taxa_urgentes = urgentes / total_viagens if total_viagens > 0 else 0

        scores = {}

        if baseline and baseline['Emissoes_Medias_Anuais'] > 0:
            if ed1_1_emissoes_totais < baseline['Emissoes_Medias_Anuais']: scores['ED1.1_Score'] = 1.0 
            elif ed1_1_emissoes_totais < (baseline['Emissoes_Medias_Anuais'] * 1.1): scores['ED1.1_Score'] = 0.5 
            else: scores['ED1.1_Score'] = 0.0 
        else: scores['ED1.1_Score'] = 0.5 

        if baseline and baseline['Distancia_Media_Anual'] > 0:
            scores['ED2.1_Score'] = 1.0 if ed2_1_distancia_total < baseline['Distancia_Media_Anual'] else 0.5
        else: scores['ED2.1_Score'] = 0.5

        if df1_5_taxa_urgentes < 0.05: scores['DF1.5_Score'] = 1.0
        elif df1_5_taxa_urgentes < 0.15: scores['DF1.5_Score'] = 0.5
        else: scores['DF1.5_Score'] = 0.0

        scores['Indicadores_Brutos'] = {
            'ED1.1_Emissoes': ed1_1_emissoes_totais, 'ED2.1_Distancia': ed2_1_distancia_total,
            'DF1.4_Taxa_Evitaveis': df1_4_taxa_evitaveis, 'DF1.5_Taxa_Urgentes': df1_5_taxa_urgentes,
            'ED2.3.1_Curtas': viagens_muito_curtas
        }
        return scores

    def calcular_painel_indices(self, dict_scores):
        """Consolida os scores de Nível 3 nas médias de Nível 2 e no Índice Geral (Nível 1)."""
        ed1 = dict_scores.get('ED1.1_Score', 0.500)
        ed2 = dict_scores.get('ED2.1_Score', 0.500)
        ed3 = 0.500  
        
        df1 = dict_scores.get('DF1.5_Score', 0.500)
        df2 = 1.000  
        
        ib1, ib2, ib3 = 0.667, 0.000, 0.250  
        
        ed_total = (ed1 + ed2 + ed3) / 3
        df_total = (df1 + df2) / 2
        ib_total = (ib1 + ib2 + ib3) / 3
        
        indice_geral = (ed_total + df_total + ib_total) / 3
        
        return {
            'N3': {'ED1': ed1, 'ED2': ed2, 'ED3': ed3, 'DF1': df1, 'DF2': df2, 'IB1': ib1, 'IB2': ib2, 'IB3': ib3},
            'N2': {'ED': ed_total, 'DF': df_total, 'IB': ib_total},
            'N1': {'Geral': indice_geral}
        }