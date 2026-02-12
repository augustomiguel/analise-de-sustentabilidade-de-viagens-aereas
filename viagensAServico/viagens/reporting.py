# classes/reporting.py
import pandas as pd
import numpy as np
import altair as alt
import os
import glob
import re
from PIL import Image


class ReportGenerator:
    
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

    # --- HELPERS DE DADOS ---

    def _load_master_file(self, orgao: str):
        arquivo_master = os.path.join(self.pasta_dados_ano, f'df_master_{orgao}_aereo_{self.ano}.csv')
        try:
            return pd.read_csv(arquivo_master)
        except FileNotFoundError:
            print(f"   - ❌ Erro: Arquivo mestre '{arquivo_master}' não encontrado.")
            return pd.DataFrame()

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

    def _format_metric_value(self, row): 
        indicador = row['Indicador/Métrica']; valor = row['Valor']; tipo = row['Tipo']
        if pd.isna(valor): return 'N/A'
        def fmt(v, d=2): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        if tipo == 'Score (0 a 1)': return fmt(valor, 4)
        if tipo == 'Variação vs Baseline': return f"{fmt(valor * 100)}%"
        if tipo == 'Baseline':
            if 'R$' in indicador: return f"R$ {fmt(valor)}"
            if 'KgCO2eq' in indicador: return f"{fmt(valor)}"
        
        if 'Percent' in indicador: return f"{fmt(valor)}%"
        if 'R$' in indicador: return f"R$ {fmt(valor)}"
        if 'KgCO2eq' in indicador: return f"{fmt(valor)} KgCO2eq"
        if 'Km' in indicador: return f"{fmt(valor)} Km"
        if 'Count' in indicador or 'Trips' in indicador: return f"{int(valor)}" 
        return f"{fmt(valor)}"

    def _get_baseline_values(self, orgao):
        ano_anterior = self.ano - 1
        pasta_metricas_anterior = f'dadosViagens/dados_viagens{ano_anterior}/metricas_scores'
        padrao_arquivo = os.path.join(pasta_metricas_anterior, f"relatorio_metricas_scores_{orgao}_{ano_anterior}.csv")
        lista_arquivos = glob.glob(padrao_arquivo)
        if lista_arquivos:
            try:
                df_anterior = pd.read_csv(lista_arquivos[0], sep=';') 
                val_emiss_str = df_anterior.loc[(df_anterior['Indicador/Métrica'] == 'ED1.1_Total_Emissions_KgCO2eq') & (df_anterior['Tipo'] == 'Métrica Bruta'), 'Valor'].iloc[0]
                val_custo_str = df_anterior.loc[(df_anterior['Indicador/Métrica'] == 'ED2.1_Total_Costs_R$') & (df_anterior['Tipo'] == 'Métrica Bruta'), 'Valor'].iloc[0]
                val_emiss = self._clean_numeric_value(val_emiss_str)
                val_custo = self._clean_numeric_value(val_custo_str)
                if pd.notna(val_emiss) and pd.notna(val_custo): return val_emiss, val_custo
            except Exception: pass
        return self.BASELINE_HISTORICO_ED1_1, self.BASELINE_HISTORICO_ED2_1

    def _calcular_indices_gerais(self, df_metrics):
        def get_score(code):
            try:
                row = df_metrics[(df_metrics['Indicador/Métrica'].str.startswith(code)) & (df_metrics['Tipo'].str.contains('Score'))]
                if not row.empty:
                    val = row['Valor'].values[0]
                    if isinstance(val, str): val = float(val.replace(',', '.'))
                    return val
                return 0.0
            except: return 0.0

        score_emissoes = get_score('ED1.1')
        score_custos = get_score('ED2.1')
        score_urgencia = get_score('DF1.5')
        
        idx_emissoes_custo = (score_emissoes * 0.5) + (score_custos * 0.5)
        idx_motivacoes = score_urgencia 
        idx_barreiras = 0.500 
        idx_geral = (idx_emissoes_custo + idx_motivacoes + idx_barreiras) / 3

        data_kpi = [
            {'Label': 'ÍNDICE GERAL', 'Value': idx_geral, 'Color': 'white', 'TextColor': 'black', 'X': 0, 'Y': 0, 'W': 2, 'H': 0.8},
            
            {'Label': 'Emissões, Deslocamento e Custo', 'Value': idx_emissoes_custo, 'Color': '#e2f0d9', 'TextColor': 'black', 'X': 0, 'Y': 1.2, 'W': 2, 'H': 0.8},
            {'Label': 'Análise de Emissões', 'Value': score_emissoes, 'Color': '#e2f0d9', 'TextColor': 'black', 'X': 0, 'Y': 2.0, 'W': 0.66, 'H': 0.6},
            {'Label': 'Análise do Deslocamento', 'Value': score_emissoes, 'Color': '#e2f0d9', 'TextColor': 'black', 'X': 0.67, 'Y': 2.0, 'W': 0.66, 'H': 0.6},
            {'Label': 'Análise dos Custos', 'Value': score_custos, 'Color': '#a9d08e', 'TextColor': 'black', 'X': 1.34, 'Y': 2.0, 'W': 0.66, 'H': 0.6},

            {'Label': 'Motivações para o voo', 'Value': idx_motivacoes, 'Color': '#dae3f3', 'TextColor': 'black', 'X': 2.2, 'Y': 1.2, 'W': 2, 'H': 0.8},
            {'Label': 'Incentivo à hipermobilidade', 'Value': idx_motivacoes, 'Color': '#dae3f3', 'TextColor': 'black', 'X': 2.2, 'Y': 2.0, 'W': 1, 'H': 0.6},
            {'Label': 'Propósitos do voo', 'Value': 1.000, 'Color': '#dae3f3', 'TextColor': 'black', 'X': 3.2, 'Y': 2.0, 'W': 1, 'H': 0.6},

            {'Label': 'Barreiras Institucionais', 'Value': idx_barreiras, 'Color': '#fff2cc', 'TextColor': 'black', 'X': 4.4, 'Y': 1.2, 'W': 2, 'H': 0.8},
            {'Label': 'Restrições', 'Value': 0.667, 'Color': '#fff2cc', 'TextColor': 'black', 'X': 4.4, 'Y': 2.0, 'W': 0.66, 'H': 0.6},
            {'Label': 'Incentivo', 'Value': 0.000, 'Color': '#ffd966', 'TextColor': 'black', 'X': 5.07, 'Y': 2.0, 'W': 0.66, 'H': 0.6},
            {'Label': 'Mudança Organizacional', 'Value': 0.250, 'Color': '#bf8f00', 'TextColor': 'white', 'X': 5.74, 'Y': 2.0, 'W': 0.66, 'H': 0.6},
        ]
        return pd.DataFrame(data_kpi)

    # --- CHART BUILDERS (CORRIGIDOS) ---

    def _create_chart_with_text(self, base, y_col, y_title, y_format):
        """Cria um gráfico de linha com rótulos de texto."""
        line = base.mark_line(point=True).encode(y=alt.Y(y_col, title=y_title))
        text = base.mark_text(dy=-10, color='black').encode(
            x=alt.X('Mes_Num:O'), 
            y=alt.Y(y_col),
            text=alt.condition(alt.datum[y_col] > 0, alt.Text(y_col, format=y_format, type='quantitative'), alt.value(''))
        )
        return (line + text).properties(title=f'Comparativo Institucional de {y_title}')

    def _build_kpi_header(self, df_metrics):
        """Constrói o gráfico de KPIs com largura ajustada para evitar cortes."""
        df_kpi = self._calcular_indices_gerais(df_metrics)
        
        base = alt.Chart(df_kpi).encode()
        rects = base.mark_rect(stroke='gray', strokeWidth=0.5).encode(
            x=alt.X('X:Q', axis=None),
            y=alt.Y('Y:Q', axis=None, scale=alt.Scale(reverse=True)),
            x2='x2_calc:Q', y2='y2_calc:Q', color=alt.Color('Color:N', scale=None),
        ).transform_calculate(x2_calc="datum.X + datum.W", y2_calc="datum.Y + datum.H")

        # Texto do Rótulo: Removi o 'limit' e ajustei o tamanho
        labels = base.mark_text(dy=-10, size=10).encode(
            x=alt.X('cx_calc:Q', axis=None), 
            y=alt.Y('cy_calc:Q', axis=None, scale=alt.Scale(reverse=True)),
            text='Label:N', 
            color=alt.Color('TextColor:N', scale=None)
        ).transform_calculate(cx_calc="datum.X + (datum.W / 2)", cy_calc="datum.Y + (datum.H / 2)")

        # Texto do Valor
        values = base.mark_text(dy=5, size=14, fontWeight='bold').encode(
            x=alt.X('cx_calc:Q', axis=None), 
            y=alt.Y('cy_calc:Q', axis=None, scale=alt.Scale(reverse=True)),
            text=alt.Text('Value:Q', format='.3f'), 
            color=alt.Color('TextColor:N', scale=None)
        ).transform_calculate(cx_calc="datum.X + (datum.W / 2)", cy_calc="datum.Y + (datum.H / 2)")

        # Aumentei a largura de 800 para 1000 para os textos caberem melhor
        return (rects + labels + values).properties(width=1000, height=150, title="Painel de Índices")

    def _build_monthly_trend_chart(self, orgao):
        """Cria os gráficos de tendência mensal (Linhas)."""
        caminho = os.path.join(self.pasta_relatorios_mensais, f"relatorio_mensal_{orgao}_aereo_{self.ano}.csv")
        if not os.path.exists(caminho): return None
        df = pd.read_csv(caminho)
        for col in ['Total_Emissoes_KgCO2eq', 'Total_Distancia_Km', 'Total_Passagens']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        base = alt.Chart(df).encode(x=alt.X('Mes_Num:O', title='Mês'))
        
        def make_line(y_col, title, fmt):
            line = base.mark_line(point=True).encode(y=alt.Y(y_col, title=title))
            text = base.mark_text(dy=-10).encode(
                x=alt.X('Mes_Num:O'),
                y=alt.Y(y_col),
                text=alt.Text(y_col, format=fmt, type='quantitative')
            )
            return (line + text).properties(title=title, width=600)

        c1 = make_line('Total_Emissoes_KgCO2eq', 'Emissões (Kg)', ',.0f')
        c2 = make_line('Total_Distancia_Km', 'Distância (Km)', ',.0f')
        c3 = make_line('Total_Passagens', 'Custos (R$)', ',.0f')
        return alt.vconcat(c1, c2, c3).properties(title=f"Tendência Mensal - {orgao}")

    def _build_metrics_charts(self, orgao):
        """Cria gráficos de barras (Baseline vs Atual)."""
        caminho = os.path.join(self.pasta_metricas, f"relatorio_metricas_scores_{orgao}_{self.ano}.csv")
        if not os.path.exists(caminho): return None
        df = pd.read_csv(caminho, sep=';')
        df['Valor_Num'] = df['Valor'].apply(self._clean_numeric_value)
        
        inds = ['ED1.1_Total_Emissions_KgCO2eq', 'ED1.1_Baseline_KgCO2eq', 'ED2.1_Total_Costs_R$', 'ED2.1_Baseline_R$']
        df_comp = df[df['Indicador/Métrica'].isin(inds)].copy()
        df_comp['Grupo'] = df_comp['Indicador/Métrica'].apply(lambda x: 'Emissões' if 'ED1.1' in x else 'Custos')
        df_comp['Legenda'] = df_comp['Tipo'].apply(lambda x: 'Baseline' if x == 'Baseline' else 'Atual')
        
        chart_comp = alt.Chart(df_comp).mark_bar().encode(
            x=alt.X('Legenda:N', title=None), y=alt.Y('Valor_Num:Q', title='Valor Total'),
            color='Legenda:N', column=alt.Column('Grupo:N', title='Comparativo vs Baseline'), tooltip=['Indicador/Métrica', 'Valor']
        ).properties(width=150)

        df_scores = df[df['Tipo'] == 'Score (0 a 1)'].copy()
        chart_scores = alt.Chart(df_scores).mark_bar().encode(
            x=alt.X('Indicador/Métrica', title=None), y=alt.Y('Valor_Num:Q', scale=alt.Scale(domain=[0, 1]), title='Score'),
            color=alt.Color('Valor_Num:Q', scale=alt.Scale(scheme='redyellowgreen', domain=[0, 1])),
            tooltip=['Indicador/Métrica', 'Valor']
        ).properties(width=300, title='Scores')

        return alt.hconcat(chart_comp, chart_scores).resolve_scale(y='independent')

    def _build_executive_charts(self, orgao):
        """Cria Pizza (Vínculo) e Barras (Categoria)."""
        df = self._load_master_file(orgao)
        if df.empty: return None
        for col in ['Emissões (KgCO2eq)', 'Distância (GCD)']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

        agg = df.groupby('Vínculo')['Emissões (KgCO2eq)'].sum().reset_index()
        agg['Pct'] = agg['Emissões (KgCO2eq)'] / agg['Emissões (KgCO2eq)'].sum()
        
        base = alt.Chart(agg).encode(theta=alt.Theta("Emissões (KgCO2eq)", stack=True))
        pie = base.mark_arc(outerRadius=100).encode(
            color=alt.Color("Vínculo", scale=alt.Scale(scheme='category10')),
            order=alt.Order("Emissões (KgCO2eq)", sort="descending"),
            tooltip=["Vínculo", alt.Tooltip("Pct", format=".1%")]
        )
        text = base.mark_text(radius=120).encode(text=alt.Text("Pct", format=".1%"), order=alt.Order("Emissões (KgCO2eq)", sort="descending"), color=alt.value("black"))
        chart_pie = (pie + text).properties(title="Emissões por Vínculo")

        df_bars = df.groupby('Categoria Distância')[['Distância (GCD)', 'Emissões (KgCO2eq)']].sum().reset_index()
        df_melt = df_bars.melt('Categoria Distância', var_name='Métrica', value_name='Valor')
        chart_bars = alt.Chart(df_melt).mark_bar().encode(
            x=alt.X('Categoria Distância', title=None, axis=alt.Axis(labels=True, labelAngle=0)),
            y=alt.Y('Valor', title='Total'),
            color='Categoria Distância', column='Métrica:N', tooltip=['Categoria Distância', 'Valor']
        ).properties(width=150, title="Por Categoria")

        return alt.hconcat(chart_pie, chart_bars).resolve_scale(color='independent')

    # --- GERADORES CSV/PDF PRINCIPAIS ---

    def generate_monthly_report(self, orgao: str):
        print(f"🔄 Gerando Relatório Mensal (CSV e Visual) com Rótulos para {orgao}...")
        
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
        
        # --- CORREÇÃO DO FORMATO DE MOEDA ---
        # Cria uma coluna de texto já formatada com R$ para o gráfico não dar erro
        def formatar_moeda(valor):
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
        df_mensal['Rotulo_Valor'] = df_mensal['Total_Passagens'].apply(formatar_moeda)

        caminho_csv = os.path.join(self.pasta_relatorios_mensais, f"relatorio_mensal_{orgao}_aereo_{self.ano}.csv")
        df_mensal.round(2).to_csv(caminho_csv, index=False)

        try:
            LARGURA_GRAFICO = 800
            ALTURA_GRAFICO = 400

            base_gastos = alt.Chart(df_mensal).encode(
                x=alt.X('Mes_Ano', title='Mês', axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Total_Passagens', title='Valor Gasto (R$)')
            )

            barras_gastos = base_gastos.mark_bar(color='#1f77b4').encode(
                tooltip=['Mes_Ano', 'Total_Passagens', 'Total_Viagens']
            )

            # Usa a coluna de texto pronta 'Rotulo_Valor' em vez de tentar formatar no Vega
            rotulos_gastos = base_gastos.mark_text(
                align='center', baseline='bottom', dy=-5, fontSize=11
            ).encode(
                text='Rotulo_Valor' 
            )

            grafico_gastos_final = alt.layer(barras_gastos, rotulos_gastos).properties(
                title=f'Gastos Mensais com Passagens - {orgao}',
                width=LARGURA_GRAFICO, height=ALTURA_GRAFICO
            )

            grafico_emissoes = alt.Chart(df_mensal).mark_line(point=True, color='red').encode(
                x=alt.X('Mes_Ano', title='Mês', axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Total_Emissoes_KgCO2eq', title='Emissões (Kg CO2eq)'),
                tooltip=['Mes_Ano', 'Total_Emissoes_KgCO2eq']
            ).properties(
                title=f'Pegada de Carbono Mensal - {orgao}',
                width=LARGURA_GRAFICO, height=ALTURA_GRAFICO
            )

            dashboard = alt.vconcat(grafico_gastos_final, grafico_emissoes).resolve_scale(x='shared').configure_view(strokeWidth=0)

            caminho_html = os.path.join(self.pasta_relatorios_mensais, f"dashboard_mensal_{orgao}_{self.ano}.html")
            dashboard.save(caminho_html)
            
            caminho_pdf = os.path.join(self.pasta_relatorios_mensais, f"dashboard_mensal_{orgao}_{self.ano}.pdf")
            dashboard.save(caminho_pdf)
            print(f"   - ✅ Dashboard (HTML/PDF) salvo para {orgao}.")

        except Exception as e:
            print(f"   - ❌ Erro ao gerar gráficos: {e}")

    def generate_excel_matrix(self, orgao: str, anos_selecionados=[2024, 2025]):
        print(f"   📊 Gerando Matriz Excel Consolidada para {orgao}...")
        
        # 1. Configuração da Tabela
        metricas = ['Distância', 'Gasto', 'Emissões']
        meses_nomes = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        
        colunas_multi = pd.MultiIndex.from_product([anos_selecionados, metricas], names=['Ano', 'Métrica'])
        df_final = pd.DataFrame(index=meses_nomes, columns=colunas_multi)
        
        # 2. Busca os dados (CAMINHO CORRIGIDO BASEADO NA IMAGEM)
        for ano_leitura in anos_selecionados:
            
            # Caminho exato conforme sua imagem:
            # dadosViagens > dados_viagens2025 > Relatorios_Mensais > arquivo.csv
            caminho_arquivo = os.path.join(
                "dadosViagens", 
                f"dados_viagens{ano_leitura}", 
                "Relatorios_Mensais", 
                f"relatorio_mensal_{orgao}_aereo_{ano_leitura}.csv"
            )
            
            if os.path.exists(caminho_arquivo):
                print(f"      - Lendo dados de: {caminho_arquivo}")
                try:
                    df_origem = pd.read_csv(caminho_arquivo)
                    
                    # Mapeia colunas
                    cols_map = {
                        'Total_Distancia_Km': 'Distância',
                        'Total_Passagens': 'Gasto',
                        'Total_Emissoes_KgCO2eq': 'Emissões'
                    }
                    
                    for _, row in df_origem.iterrows():
                        # Garante índice correto (0 a 11)
                        mes_idx = int(row['Mes_Num']) - 1
                        if 0 <= mes_idx < 12:
                            mes_nome = meses_nomes[mes_idx]
                            for col_csv, col_excel in cols_map.items():
                                # Converte para float para garantir que o Excel entenda como número
                                valor = float(str(row[col_csv]).replace(',', '.'))
                                df_final.loc[mes_nome, (ano_leitura, col_excel)] = valor
                                
                except Exception as e:
                    print(f"      ❌ Erro ao ler arquivo {ano_leitura}: {e}")
            else:
                print(f"      ⚠️ Arquivo NÃO encontrado: {caminho_arquivo}")

        # 3. Finalização
        # O comando infer_objects() ajusta os tipos das colunas (de Object para Float/Int)
        # ANTES de preencher os zeros, eliminando o aviso.
        df_final = df_final.infer_objects(copy=False).fillna(0)
        
        # Totais
        df_final.loc['Anual'] = df_final.sum()
        df_final.loc['Média'] = df_final.iloc[0:12].mean()

        # 4. SALVAR NA PASTA 'dadosViagens' (Conforme pedido)
        caminho_excel = os.path.join("dadosViagens", f"matriz_completa_{orgao}.xlsx")
        
        # Garante que a pasta dadosViagens existe
        if not os.path.exists("dadosViagens"):
            os.makedirs("dadosViagens")

        try:
            with pd.ExcelWriter(caminho_excel, engine='openpyxl') as writer:
                df_final.to_excel(writer, sheet_name='Dados', startrow=2)
                
                # Formatação do Título
                worksheet = writer.sheets['Dados']
                worksheet['A1'] = f"Dados do deslocamento aéreo - {orgao}"
                from openpyxl.styles import Font
                worksheet['A1'].font = Font(size=14, bold=True)

            print(f"   ✅ Excel salvo com sucesso em: {os.path.abspath(caminho_excel)}")
            
        except Exception as e:
            print(f"   ❌ Erro ao salvar Excel: {e}")
    def generate_metrics_report(self, orgao: str):
        print(f"🔄 Gerando Relatório de Métricas (CSV) para {orgao}...")
        df = self._load_master_file(orgao)
        if df.empty: return
        colunas_numericas = ['Distância (GCD)', 'Emissões (KgCO2eq)', 'Valor passagens', 'Valor diárias', 'Valor outros gastos']
        for col in colunas_numericas:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        df['Custo_Total_Viagem'] = df[['Valor passagens', 'Valor diárias', 'Valor outros gastos']].sum(axis=1)
        
        totais = {
            'ED1.1_Total_Emissions_KgCO2eq': df['Emissões (KgCO2eq)'].sum(),
            'ED1.2_Avoidable_Emissions_KgCO2eq': df.loc[df['Categoria Distância'] == 'Muito Curta (Evitável)', 'Emissões (KgCO2eq)'].sum(),
            'ED2.1_Total_Costs_R$': df['Custo_Total_Viagem'].sum(),
            'ED2.3_Total_Trips': len(df),
            'ED3.1_Total_Distance_Km': df['Distância (GCD)'].sum()
        }
        n_viajantes = df['CPF viajante'].nunique(); n_viagens = len(df)
        
        totais.update({
            'ED1.3_Avg_Emissions_per_Traveler': totais['ED1.1_Total_Emissions_KgCO2eq'] / n_viajantes if n_viajantes else 0,
            'ED1.4_Avg_Emissions_per_Trip': totais['ED1.1_Total_Emissions_KgCO2eq'] / n_viagens if n_viagens else 0,
            'ED2.2_Avg_Cost_per_Traveler': totais['ED2.1_Total_Costs_R$'] / n_viajantes if n_viajantes else 0,
            'ED2.4_Avg_Cost_per_Trip': totais['ED2.1_Total_Costs_R$'] / n_viagens if n_viagens else 0,
            'ED2.5_Avg_Cost_per_Km': totais['ED2.1_Total_Costs_R$'] / totais['ED3.1_Total_Distance_Km'] if totais['ED3.1_Total_Distance_Km'] else 0,
            'ED3.2_Avg_Distance_per_Traveler': totais['ED3.1_Total_Distance_Km'] / n_viajantes if n_viajantes else 0,
            'ED3.3_Avg_Distance_per_Trip': totais['ED3.1_Total_Distance_Km'] / n_viagens if n_viagens else 0
        })
        
        urgentes = (df['Viagem Urgente'].astype(str).str.strip().str.upper() == 'SIM').sum()
        urg_s_just = df[(df['Viagem Urgente'].astype(str).str.strip().str.upper() == 'SIM') & (df['Justificativa Urgência Viagem'].astype(str).str.strip().fillna('Sem informação').str.upper() == 'SEM INFORMAÇÃO')].shape[0]
        totais.update({
            'DF1.4_Urgent_Trips_Percent': (urgentes / n_viagens * 100) if n_viagens else 0,
            'DF1.4_Urgent_Trips_Count': urgentes,
            'DF1.5_Urgent_Trips_wo_Justif_Percent': (urg_s_just / n_viagens * 100) if n_viagens else 0,
            'DF1.5_Urgent_Trips_wo_Justif_Count': urg_s_just
        })

        metrics_df = pd.DataFrame(totais.items(), columns=['Indicador/Métrica', 'Valor']); metrics_df['Tipo'] = 'Métrica Bruta'
        
        BASE_ED1, BASE_ED2 = self._get_baseline_values(orgao)
        baselines_df = pd.DataFrame([{'Indicador/Métrica': 'ED1.1_Baseline_KgCO2eq', 'Valor': BASE_ED1, 'Tipo': 'Baseline'}, {'Indicador/Métrica': 'ED2.1_Baseline_R$', 'Valor': BASE_ED2, 'Tipo': 'Baseline'}])
        
        scores = {'ED1.1_Score': 1.0 if totais['ED1.1_Total_Emissions_KgCO2eq'] <= BASE_ED1 else 0.5, 'ED2.1_Score': 1.0 if totais['ED2.1_Total_Costs_R$'] <= BASE_ED2 else 0.5, 'DF1.5_Score': max(0, 1.0 - (urg_s_just / n_viagens if n_viagens else 0))}
        scores_df = pd.DataFrame(scores.items(), columns=['Indicador/Métrica', 'Valor']); scores_df['Tipo'] = 'Score (0 a 1)'
        
        final_df = pd.concat([metrics_df, baselines_df, scores_df], ignore_index=True)
        final_df['Valor'] = final_df.apply(self._format_metric_value, axis=1)
        final_df.to_csv(os.path.join(self.pasta_metricas, f"relatorio_metricas_scores_{orgao}_{self.ano}.csv"), index=False, sep=';', decimal=',')
        print(f"   - ✅ Relatório de Métricas (Completo) salvo.")

    def generate_consolidated_dashboard(self, orgao: str):
        print(f"🔄 Gerando Dashboard Completo Consolidado para {orgao}...")
        
        c1 = self._build_monthly_trend_chart(orgao)
        c2 = self._build_metrics_charts(orgao)
        c3 = self._build_executive_charts(orgao)
        
        if not c1 or not c2 or not c3: return

        # Load Metrics for KPI
        caminho_metricas = os.path.join(self.pasta_metricas, f"relatorio_metricas_scores_{orgao}_{self.ano}.csv")
        if os.path.exists(caminho_metricas): df_metrics = pd.read_csv(caminho_metricas, sep=';')
        else: df_metrics = pd.DataFrame(columns=['Indicador/Métrica', 'Valor', 'Tipo'])
        
        chart_kpi = self._build_kpi_header(df_metrics)

        final_dash = alt.vconcat(
            chart_kpi,
            c1, 
            alt.vconcat(c2, c3).resolve_scale(color='independent')
        ).properties(
            title=f"Relatório Integrado - {orgao} {self.ano}"
        ).resolve_scale(color='independent')

        nome_base = f"dashboard_completo_{orgao}_{self.ano}"
        try:
            final_dash.save(os.path.join(self.pasta_metricas, f"{nome_base}.html"))
            print(f"   - ✅ Dashboard HTML salvo.")
            final_dash.save(os.path.join(self.pasta_metricas, f"{nome_base}_temp.png"), ppi=150)
            img = Image.open(os.path.join(self.pasta_metricas, f"{nome_base}_temp.png"))
            if img.mode == 'RGBA': img = img.convert('RGB')
            img.save(os.path.join(self.pasta_metricas, f"{nome_base}.pdf"), "PDF")
            if os.path.exists(os.path.join(self.pasta_metricas, f"{nome_base}_temp.png")):
                os.remove(os.path.join(self.pasta_metricas, f"{nome_base}_temp.png"))
            print(f"   - ✅ Dashboard PDF salvo.")
        except Exception as e:
            print(f"   - ⚠️ Erro ao salvar Dashboard: {e}")

    def generate_comparison_pdf(self):
        print(f"🔄 Gerando Comparativo para {self.ano}...")
        search_pattern = os.path.join(self.pasta_relatorios_mensais, f"relatorio_mensal_*_aereo_{self.ano}.csv")
        all_files = sorted(glob.glob(search_pattern))
        if not all_files: return
        all_data = []
        for f in all_files:
            try:
                org = re.search(f'relatorio_mensal_(.*?)_aereo_{self.ano}\\.csv$', os.path.basename(f)).group(1)
                df = pd.read_csv(f)
                for c in ['Total_Emissoes_KgCO2eq', 'Total_Distancia_Km', 'Total_Passagens']:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                df['Instituicao'] = org
                all_data.append(df)
            except: pass
        if not all_data: return
        df_comp = pd.concat(all_data)
        
        base = alt.Chart(df_comp).encode(x=alt.X('Mes_Num:O', title='Mês'), color='Instituicao:N', tooltip=['Instituicao', 'Mes_Ano', 'Total_Emissoes_KgCO2eq'])
        c1 = self._create_chart_with_text(base, 'Total_Emissoes_KgCO2eq', 'Emissões (Kg)', ',.0f')
        c2 = self._create_chart_with_text(base, 'Total_Distancia_Km', 'Distância (Km)', ',.0f')
        c3 = self._create_chart_with_text(base, 'Total_Passagens', 'Custos (R$)', ',.0f')
        
        dash = alt.vconcat(c1, c2, c3).properties(title=f"Comparativo Institucional {self.ano}")
        name = f"dashboard_comparativo_institucional_{self.ano}"
        try: 
            dash.save(os.path.join(self.pasta_relatorios_mensais, f"{name}.html"))
            dash.save(os.path.join(self.pasta_relatorios_mensais, f"{name}_temp.png"), ppi=200)
            img = Image.open(os.path.join(self.pasta_relatorios_mensais, f"{name}_temp.png"))
            if img.mode == 'RGBA': img = img.convert('RGB')
            img.save(os.path.join(self.pasta_relatorios_mensais, f"{name}.pdf"), "PDF")
            if os.path.exists(os.path.join(self.pasta_relatorios_mensais, f"{name}_temp.png")):
                os.remove(os.path.join(self.pasta_relatorios_mensais, f"{name}_temp.png"))
            print(f"   - ✅ Comparativo salvo (HTML e PDF).")
        except: pass