# classes/reporting.py
import pandas as pd
import numpy as np
import altair as alt
import os
import glob
import re

class ReportGenerator:
    
    # Constantes de Baseline Histórico (Fallback)
    BASELINE_HISTORICO_ED1_1 = 285440.323 
    BASELINE_HISTORICO_ED2_1 = 1738431.16 
    
    def __init__(self, ano: int):
        self.ano = ano
        self.pasta_dados_ano = f'dadosViagens/dados_viagens{self.ano}'
        self.pasta_relatorios_mensais = os.path.join(self.pasta_dados_ano, 'Relatorios_Mensais')
        self.pasta_metricas = os.path.join(self.pasta_dados_ano, 'metricas_scores')
        
        os.makedirs(self.pasta_relatorios_mensais, exist_ok=True)
        os.makedirs(self.pasta_metricas, exist_ok=True)
        
        print(f"ReportGenerator: Pronto para relatórios do ano {self.ano}.")

    def _load_master_file(self, orgao: str):
        """Carrega o arquivo mestre para um órgão específico."""
        arquivo_master = os.path.join(self.pasta_dados_ano, f'df_master_{orgao}_aereo_{self.ano}.csv')
        try:
            df = pd.read_csv(arquivo_master)
            return df
        except FileNotFoundError:
            print(f"   - ❌ Erro: Arquivo mestre '{arquivo_master}' não encontrado.")
            return pd.DataFrame()

    def generate_monthly_report(self, orgao: str):
        """Gera o CSV mensal."""
        print(f"🔄 Gerando Relatório Mensal para {orgao}...")
        df = self._load_master_file(orgao)
        if df.empty: return

        df['Data_Viagem'] = pd.to_datetime(df['Período - Data de início'], format='%d/%m/%Y', errors='coerce')
        df.dropna(subset=['Data_Viagem'], inplace=True)
        df['Mes_Num'] = df['Data_Viagem'].dt.month
        df['Mes_Ano'] = df['Mes_Num'].apply(lambda x: f"{self.ano}-{x:02d}")
        
        for col in ['Distância (GCD)', 'Emissões (KgCO2eq)', 'Valor passagens']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

        df_agrupado = df.groupby(['Mes_Ano', 'Mes_Num']).agg(
            Total_Distancia_Km = ('Distância (GCD)', 'sum'),
            Total_Emissoes_KgCO2eq = ('Emissões (KgCO2eq)', 'sum'),
            Total_Viagens = ('Identificador do processo de viagem', 'count'),
            Total_Passagens = ('Valor passagens', 'sum')
        ).reset_index()

        meses_template = pd.DataFrame({'Mes_Num': range(1, 13)})
        meses_template['Mes_Ano'] = meses_template['Mes_Num'].apply(lambda x: f"{self.ano}-{x:02d}")
        df_mensal = pd.merge(meses_template, df_agrupado, on=['Mes_Num', 'Mes_Ano'], how='left')
        df_mensal.fillna(0, inplace=True)
        df_mensal['Total_Viagens'] = df_mensal['Total_Viagens'].astype(int)

        nome_arquivo_saida = f"relatorio_mensal_{orgao}_aereo_{self.ano}.csv"
        caminho_saida = os.path.join(self.pasta_relatorios_mensais, nome_arquivo_saida)
        df_mensal.round(2).to_csv(caminho_saida, index=False)
        print(f"   - ✅ Relatório mensal salvo em: '{caminho_saida}'")

    def _create_chart_with_text(self, base, y_col, y_title, y_format):
        line = base.mark_line(point=True).encode(y=alt.Y(y_col, title=y_title))
        text = base.mark_text(dy=-10, color='black').encode(
            x=alt.X('Mes_Num:O'), 
            y=alt.Y(y_col),
            text=alt.condition(alt.datum[y_col] > 0, alt.Text(y_col, format=y_format, type='quantitative'), alt.value(''))
        )
        return (line + text).properties(title=f'Comparativo Institucional de {y_title}')

    def generate_comparison_pdf(self):
        """Gera o PDF comparativo."""
        print(f"🔄 Gerando PDF Comparativo para {self.ano}...")
        search_pattern = os.path.join(self.pasta_relatorios_mensais, f"relatorio_mensal_*_aereo_{self.ano}.csv")
        all_files = sorted(glob.glob(search_pattern))
        if not all_files: return
            
        all_data_list = []
        for f in all_files:
            try:
                org_match = re.search(f'relatorio_mensal_(.*?)_aereo_{self.ano}\\.csv$', os.path.basename(f))
                if org_match:
                    df_report = pd.read_csv(f)
                    for col in ['Total_Distancia_Km', 'Total_Emissoes_KgCO2eq', 'Total_Passagens', 'Total_Viagens']:
                        df_report[col] = pd.to_numeric(df_report[col], errors='coerce').fillna(0)
                    df_report['Instituicao'] = org_match.group(1)
                    all_data_list.append(df_report)
            except Exception: pass

        if not all_data_list: return
        df_comparativo = pd.concat(all_data_list, ignore_index=True)
        
        base_comp = alt.Chart(df_comparativo).encode(
            x=alt.X('Mes_Num:O', axis=alt.Axis(title='Mês')),
            color=alt.Color('Instituicao:N', title='Instituição'),
            tooltip=['Instituicao', 'Mes_Ano', 'Total_Emissoes_KgCO2eq', 'Total_Distancia_Km', 'Total_Passagens']
        ).properties(width=700)

        chart1 = self._create_chart_with_text(base_comp, 'Total_Emissoes_KgCO2eq', 'Total Emissões ($KgCO_2eq$)', ',.0f')
        chart2 = self._create_chart_with_text(base_comp, 'Total_Distancia_Km', 'Total Distância (km)', ',.0f')
        chart3 = self._create_chart_with_text(base_comp, 'Total_Passagens', 'Total Passagens (R$)', ',.0f')

        dashboard = alt.vconcat(chart1, chart2, chart3).properties(title=f"Comparativo Institucional - {self.ano}")
        
        instituicoes = sorted(df_comparativo['Instituicao'].unique())
        nome_arquivo = f'dashboard_comparativo_institucional_{self.ano}_{"_".join(instituicoes)}.pdf'
        try:
            dashboard.save(os.path.join(self.pasta_relatorios_mensais, nome_arquivo))
            print(f"   - ✅ PDF comparativo salvo.")
        except Exception as e:
            print(f"   - ❌ Erro ao salvar PDF: {e}")

    def _clean_numeric_value(self, value_in):
        if pd.isna(value_in): return np.nan
        if isinstance(value_in, (int, float)): return float(value_in)
        try:
            s = str(value_in).strip()
            s = re.sub(r'(R\$|\s?KgCO2eq|\s?Km|%)', '', s, flags=re.IGNORECASE).strip()
            is_pt_br = ',' in s and ('.' not in s or s.rfind(',') > s.rfind('.'))
            if is_pt_br: s = s.replace('.', '').replace(',', '.')
            else: s = s.replace(',', '')
            return float(s)
        except: return np.nan

    def _get_baseline_values(self, orgao):
        ano_anterior = self.ano - 1
        pasta_metricas_anterior = f'dadosViagens/dados_viagens{ano_anterior}/metricas_scores'
        padrao_arquivo = os.path.join(pasta_metricas_anterior, f"relatorio_metricas_scores_{orgao}_{ano_anterior}.csv")
        lista_arquivos = glob.glob(padrao_arquivo)
        if lista_arquivos:
            try:
                df_anterior = pd.read_csv(lista_arquivos[0], sep=';') # Lê sem decimal definido, pois é misto
                val_emiss = df_anterior.loc[(df_anterior['Indicador/Métrica'] == 'ED1.1_Total_Emissions_KgCO2eq') & (df_anterior['Tipo'] == 'Métrica Bruta'), 'Valor'].iloc[0]
                val_custo = df_anterior.loc[(df_anterior['Indicador/Métrica'] == 'ED2.1_Total_Costs_R$') & (df_anterior['Tipo'] == 'Métrica Bruta'), 'Valor'].iloc[0]
                return self._clean_numeric_value(val_emiss), self._clean_numeric_value(val_custo)
            except Exception: pass
        return self.BASELINE_HISTORICO_ED1_1, self.BASELINE_HISTORICO_ED2_1

    def _format_metric_value(self, row):
        indicador = row['Indicador/Métrica']; valor = row['Valor']; tipo = row['Tipo']
        if pd.isna(valor): return 'N/A'
        def fmt(v, d=2): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        if tipo == 'Score (0 a 1)': return fmt(valor, 4)
        if tipo == 'Variação vs Baseline': return f"{fmt(valor * 100)}%"
        if 'R$' in indicador: return f"R$ {fmt(valor)}"
        if 'KgCO2eq' in indicador: return f"{fmt(valor)} KgCO2eq"
        if 'Km' in indicador: return f"{fmt(valor)} Km"
        if 'Count' in indicador or 'Trips' in indicador: return f"{int(valor)}"
        return fmt(valor)

    def generate_metrics_report(self, orgao: str):
        """Gera o relatório CSV de métricas e scores."""
        print(f"🔄 Gerando Relatório de Métricas (CSV) para {orgao}...")
        df = self._load_master_file(orgao)
        if df.empty: return
        
        for col in ['Distância (GCD)', 'Emissões (KgCO2eq)', 'Valor passagens', 'Valor diárias', 'Valor outros gastos']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
            
        df['Custo_Total_Viagem'] = df[['Valor passagens', 'Valor diárias', 'Valor outros gastos']].sum(axis=1)
        
        # Totais
        totais = {
            'ED1.1_Total_Emissions_KgCO2eq': df['Emissões (KgCO2eq)'].sum(),
            'ED1.2_Avoidable_Emissions_KgCO2eq': df.loc[df['Categoria Distância'] == 'Muito Curta (Evitável)', 'Emissões (KgCO2eq)'].sum(),
            'ED2.1_Total_Costs_R$': df['Custo_Total_Viagem'].sum(),
            'ED2.3_Total_Trips': len(df),
            'ED3.1_Total_Distance_Km': df['Distância (GCD)'].sum()
        }
        # Médias
        n_viajantes = df['CPF viajante'].nunique()
        n_viagens = len(df)
        totais.update({
            'ED1.3_Avg_Emissions_per_Traveler': totais['ED1.1_Total_Emissions_KgCO2eq'] / n_viajantes if n_viajantes else 0,
            'ED1.4_Avg_Emissions_per_Trip': totais['ED1.1_Total_Emissions_KgCO2eq'] / n_viagens if n_viagens else 0,
            'ED2.2_Avg_Cost_per_Traveler': totais['ED2.1_Total_Costs_R$'] / n_viajantes if n_viajantes else 0,
            'ED2.4_Avg_Cost_per_Trip': totais['ED2.1_Total_Costs_R$'] / n_viagens if n_viagens else 0,
            'ED2.5_Avg_Cost_per_Km': totais['ED2.1_Total_Costs_R$'] / totais['ED3.1_Total_Distance_Km'] if totais['ED3.1_Total_Distance_Km'] else 0,
            'ED3.2_Avg_Distance_per_Traveler': totais['ED3.1_Total_Distance_Km'] / n_viajantes if n_viajantes else 0,
            'ED3.3_Avg_Distance_per_Trip': totais['ED3.1_Total_Distance_Km'] / n_viagens if n_viagens else 0
        })
        # Governança
        urgentes = (df['Viagem Urgente'].astype(str).str.strip().str.upper() == 'SIM').sum()
        urg_s_just = df[(df['Viagem Urgente'].astype(str).str.strip().str.upper() == 'SIM') & 
                        (df['Justificativa Urgência Viagem'].astype(str).str.strip().fillna('Sem informação').str.upper() == 'SEM INFORMAÇÃO')].shape[0]
        totais.update({
            'DF1.4_Urgent_Trips_Percent': (urgentes / n_viagens * 100) if n_viagens else 0,
            'DF1.4_Urgent_Trips_Count': urgentes,
            'DF1.5_Urgent_Trips_wo_Justif_Percent': (urg_s_just / n_viagens * 100) if n_viagens else 0,
            'DF1.5_Urgent_Trips_wo_Justif_Count': urg_s_just
        })

        metrics_df = pd.DataFrame(totais.items(), columns=['Indicador/Métrica', 'Valor'])
        metrics_df['Tipo'] = 'Métrica Bruta'

        # Baseline e Scores
        BASE_ED1, BASE_ED2 = self._get_baseline_values(orgao)
        baselines_df = pd.DataFrame([
            {'Indicador/Métrica': 'ED1.1_Baseline_KgCO2eq', 'Valor': BASE_ED1, 'Tipo': 'Baseline'},
            {'Indicador/Métrica': 'ED2.1_Baseline_R$', 'Valor': BASE_ED2, 'Tipo': 'Baseline'}
        ])

        scores = {}
        vars = {}
        
        # DF1.5
        prop_urg_sj = urg_s_just / n_viagens if n_viagens else 0
        scores['DF1.5_Score'] = max(0, 1.0 - prop_urg_sj)
        vars['DF1.5_Proporção_Urg_s_Just'] = prop_urg_sj
        
        # ED1.1
        var_ed1 = (totais['ED1.1_Total_Emissions_KgCO2eq'] - BASE_ED1) / BASE_ED1 if BASE_ED1 else 0
        scores['ED1.1_Score'] = 1.0 if totais['ED1.1_Total_Emissions_KgCO2eq'] <= BASE_ED1 else max(0, 1.0 - (var_ed1 / 2.0))
        vars['ED1.1_Variação_vs_Baseline'] = var_ed1
        
        # ED2.1
        var_ed2 = (totais['ED2.1_Total_Costs_R$'] - BASE_ED2) / BASE_ED2 if BASE_ED2 else 0
        scores['ED2.1_Score'] = 1.0 if totais['ED2.1_Total_Costs_R$'] <= BASE_ED2 else max(0, 1.0 - (var_ed2 / 2.0))
        vars['ED2.1_Variação_vs_Baseline'] = var_ed2

        scores_df = pd.DataFrame(scores.items(), columns=['Indicador/Métrica', 'Valor']); scores_df['Tipo'] = 'Score (0 a 1)'
        vars_df = pd.DataFrame(vars.items(), columns=['Indicador/Métrica', 'Valor']); vars_df['Tipo'] = 'Variação vs Baseline'

        final_df = pd.concat([metrics_df, baselines_df, vars_df, scores_df], ignore_index=True)
        final_df['Valor'] = final_df.apply(self._format_metric_value, axis=1)
        
        caminho = os.path.join(self.pasta_metricas, f"relatorio_metricas_scores_{orgao}_{self.ano}.csv")
        final_df.to_csv(caminho, index=False, sep=';', decimal=',')
        print(f"   - ✅ Relatório CSV salvo em: '{caminho}'")

    # --- MÉTODO REINSERIDO: DASHBOARD DE MÉTRICAS (BARRAS) ---
    def generate_metrics_dashboard(self, orgao: str):
        """Gera o dashboard visual de métricas (Barras comparativas)."""
        print(f"🔄 Gerando Dashboard Visual de Métricas para {orgao}...")
        caminho_csv = os.path.join(self.pasta_metricas, f"relatorio_metricas_scores_{orgao}_{self.ano}.csv")
        if not os.path.exists(caminho_csv): return

        try:
            df = pd.read_csv(caminho_csv, sep=';') # CSV Misto
            df['Valor_Num'] = df['Valor'].apply(self._clean_numeric_value)
            
            # Gráfico Comparativo
            indicadores = ['ED1.1_Total_Emissions_KgCO2eq', 'ED1.1_Baseline_KgCO2eq', 'ED2.1_Total_Costs_R$', 'ED2.1_Baseline_R$']
            df_comp = df[df['Indicador/Métrica'].isin(indicadores)].copy()
            df_comp['Grupo'] = df_comp['Indicador/Métrica'].apply(lambda x: 'Emissões (KgCO2eq)' if 'ED1.1' in x else 'Custos (R$)')
            df_comp['Legenda'] = df_comp['Tipo'].apply(lambda x: 'Baseline' if x == 'Baseline' else 'Atual')
            
            chart_comp = alt.Chart(df_comp).mark_bar().encode(
                x=alt.X('Legenda:N', title=None),
                y=alt.Y('Valor_Num:Q', title='Valor'),
                color='Legenda:N',
                column='Grupo:N',
                tooltip=['Indicador/Métrica', 'Valor']
            ).properties(width=150)

            # Gráfico Scores
            df_scores = df[df['Tipo'] == 'Score (0 a 1)'].copy()
            chart_scores = alt.Chart(df_scores).mark_bar().encode(
                x='Indicador/Métrica',
                y=alt.Y('Valor_Num:Q', scale=alt.Scale(domain=[0, 1]), title='Score'),
                color=alt.Color('Valor_Num:Q', scale=alt.Scale(scheme='redyellowgreen', domain=[0, 1])),
                tooltip=['Indicador/Métrica', 'Valor']
            ).properties(width=400, title='Scores de Desempenho')
            
            dashboard = alt.vconcat(chart_comp, chart_scores).resolve_scale(y='independent')
            dashboard.save(os.path.join(self.pasta_metricas, f"dashboard_metricas_{orgao}_{self.ano}.pdf"))
            print(f"   - ✅ Dashboard de Métricas salvo.")
        except Exception as e:
            print(f"   - ❌ Erro ao gerar dashboard métricas: {e}")

    # --- MÉTODO NOVO: DASHBOARD EXECUTIVO (PIZZA + BARRAS DETALHADAS) ---
    def generate_executive_dashboard(self, orgao: str):
        """Gera o dashboard visual detalhado (Pizza por Vínculo, Barras por Distância)."""
        print(f"🔄 Gerando Dashboard Executivo para {orgao}...")
        df = self._load_master_file(orgao)
        if df.empty: return

        for col in ['Emissões (KgCO2eq)', 'Distância (GCD)']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

        # Pizza: Emissões por Vínculo
        agg_emiss = df.groupby('Vínculo')['Emissões (KgCO2eq)'].sum().reset_index()
        agg_emiss['Percent'] = agg_emiss['Emissões (KgCO2eq)'] / agg_emiss['Emissões (KgCO2eq)'].sum()
        
        base_pie = alt.Chart(agg_emiss).encode(theta=alt.Theta("Emissões (KgCO2eq)", stack=True))
        pie = base_pie.mark_arc(outerRadius=120).encode(
            color="Vínculo",
            order=alt.Order("Emissões (KgCO2eq)", sort="descending"),
            tooltip=["Vínculo", "Emissões (KgCO2eq)", alt.Tooltip("Percent", format=".1%")]
        )
        text = base_pie.mark_text(radius=140).encode(
            text=alt.Text("Percent", format=".1%"),
            order=alt.Order("Emissões (KgCO2eq)", sort="descending"),
            color=alt.value("black")
        )
        chart_pie_emiss = (pie + text).properties(title="Emissões por Função")

        # Pizza: Viagens por Vínculo
        agg_trips = df.groupby('Vínculo')['Identificador do processo de viagem'].count().reset_index().rename(columns={'Identificador do processo de viagem': 'Viagens'})
        agg_trips['Percent'] = agg_trips['Viagens'] / agg_trips['Viagens'].sum()
        
        base_pie2 = alt.Chart(agg_trips).encode(theta=alt.Theta("Viagens", stack=True))
        pie2 = base_pie2.mark_arc(outerRadius=120).encode(
            color="Vínculo",
            order=alt.Order("Viagens", sort="descending"),
            tooltip=["Vínculo", "Viagens", alt.Tooltip("Percent", format=".1%")]
        )
        text2 = base_pie2.mark_text(radius=140).encode(
            text=alt.Text("Percent", format=".1%"),
            order=alt.Order("Viagens", sort="descending"),
            color=alt.value("black")
        )
        chart_pie_trips = (pie2 + text2).properties(title="Nº de Viagens por Função")

        # Barras: Distância e Emissões por Categoria
        df_bars = df.groupby('Categoria Distância')[['Distância (GCD)', 'Emissões (KgCO2eq)']].sum().reset_index()
        df_melted = df_bars.melt('Categoria Distância', var_name='Métrica', value_name='Valor')
        
        chart_bars = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('Categoria Distância', axis=alt.Axis(title=None)),
            y=alt.Y('Valor', axis=alt.Axis(title='Total')),
            color='Categoria Distância',
            column='Métrica:N',
            tooltip=['Categoria Distância', 'Valor']
        ).properties(width=150, title="Comparativo: Curta vs Longa Distância")

        dashboard = alt.vconcat(
            alt.hconcat(chart_pie_emiss, chart_pie_trips),
            chart_bars
        ).resolve_scale(color='independent').properties(title=f"Dashboard Executivo - {orgao} {self.ano}")

        try:
            dashboard.save(os.path.join(self.pasta_metricas, f"dashboard_executivo_{orgao}_{self.ano}.pdf"))
            print(f"   - ✅ Dashboard Executivo salvo.")
        except Exception as e:
            print(f"   - ❌ Erro ao salvar Dashboard Executivo: {e}")