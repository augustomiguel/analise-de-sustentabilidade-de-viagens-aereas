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
            print(f"   - Arquivo mestre '{arquivo_master}' carregado.")
            return df
        except FileNotFoundError:
            print(f"   - ❌ Erro: Arquivo mestre '{arquivo_master}' não encontrado.")
            return pd.DataFrame()

    def generate_monthly_report(self, orgao: str):
        """Gera o CSV mensal (lógica de 'teste_mensal.ipynb')."""
        print(f"🔄 Gerando Relatório Mensal para {orgao}...")
        df = self._load_master_file(orgao)
        if df.empty:
            print(f"   - ⚠️ Relatório mensal pulado para {orgao} (arquivo mestre vazio ou não encontrado).")
            return

        # 1. Preparar Dados
        df['Data_Viagem'] = pd.to_datetime(df['Período - Data de início'], format='%d/%m/%Y', errors='coerce')
        df.dropna(subset=['Data_Viagem'], inplace=True)
        
        df['Mes_Num'] = df['Data_Viagem'].dt.month
        df['Mes_Ano'] = df['Mes_Num'].apply(lambda x: f"{self.ano}-{x:02d}")
        
        # Converte valores de texto com VÍRGULA para número
        df['Distância (GCD)'] = pd.to_numeric(df['Distância (GCD)'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        df['Emissões (KgCO2eq)'] = pd.to_numeric(df['Emissões (KgCO2eq)'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        df['Valor passagens'] = pd.to_numeric(df['Valor passagens'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

        # 2. Agrupar
        df_agrupado = df.groupby(['Mes_Ano', 'Mes_Num']).agg(
            Total_Distancia_Km = ('Distância (GCD)', 'sum'),
            Total_Emissoes_KgCO2eq = ('Emissões (KgCO2eq)', 'sum'),
            Total_Viagens = ('Identificador do processo de viagem', 'count'),
            Total_Passagens = ('Valor passagens', 'sum')
        ).reset_index()

        # 3. Garantir 12 Meses
        meses_template = pd.DataFrame({'Mes_Num': range(1, 13)})
        meses_template['Mes_Ano'] = meses_template['Mes_Num'].apply(lambda x: f"{self.ano}-{x:02d}")
        
        df_mensal = pd.merge(meses_template, df_agrupado, on=['Mes_Num', 'Mes_Ano'], how='left')
        df_mensal.fillna(0, inplace=True)
        df_mensal['Total_Viagens'] = df_mensal['Total_Viagens'].astype(int)

        # 4. Salvar
        nome_arquivo_saida = f"relatorio_mensal_{orgao}_aereo_{self.ano}.csv"
        caminho_saida = os.path.join(self.pasta_relatorios_mensais, nome_arquivo_saida)
        df_mensal.round(2).to_csv(caminho_saida, index=False)
        print(f"   - ✅ Relatório mensal salvo em: '{caminho_saida}'")

    def _create_chart_with_text(self, base, y_col, y_title, y_format):
        """Helper interno para criar um gráfico de linha com rótulos de texto."""
        line = base.mark_line(point=True).encode(
            y=alt.Y(y_col, title=y_title)
        )
        
        text = base.mark_text(dy=-10, color='black').encode(
            x=alt.X('Mes_Num:O'), 
            y=alt.Y(y_col),
            text=alt.condition(
                alt.datum[y_col] > 0,
                alt.Text(y_col, format=y_format, type='quantitative'),
                alt.value('') # Mostra nada se for 0
            )
        )
        return (line + text).properties(title=f'Comparativo Institucional de {y_title}')

    def generate_comparison_pdf(self):
        """Gera o PDF comparativo (lógica de 'comparacao.ipynb')."""
        print(f"🔄 Gerando PDF Comparativo para {self.ano}...")
        
        # 1. Carregar Dados Comparativos
        search_pattern = os.path.join(self.pasta_relatorios_mensais, f"relatorio_mensal_*_aereo_{self.ano}.csv")
        all_files = sorted(glob.glob(search_pattern))
        
        if not all_files:
            print("   - ⚠️ Nenhum relatório mensal encontrado. PDF comparativo pulado.")
            return
            
        all_data_list = []
        for f in all_files:
            try:
                org_match = re.search(f'relatorio_mensal_(.*?)_aereo_{self.ano}\\.csv$', os.path.basename(f))
                if org_match:
                    instituicao_arquivo = org_match.group(1)
                    df_report = pd.read_csv(f)
                    
                    df_report['Total_Distancia_Km'] = pd.to_numeric(df_report['Total_Distancia_Km'], errors='coerce').fillna(0)
                    df_report['Total_Emissoes_KgCO2eq'] = pd.to_numeric(df_report['Total_Emissoes_KgCO2eq'], errors='coerce').fillna(0)
                    df_report['Total_Passagens'] = pd.to_numeric(df_report['Total_Passagens'], errors='coerce').fillna(0)
                    df_report['Total_Viagens'] = pd.to_numeric(df_report['Total_Viagens'], errors='coerce').fillna(0)
                    
                    df_report['Instituicao'] = instituicao_arquivo
                    all_data_list.append(df_report)
            except Exception as e:
                print(f"   - ❌ Erro ao carregar '{f}': {e}")

        if not all_data_list:
            print("   - ⚠️ Nenhum dado comparativo carregado. PDF pulado.")
            return
            
        df_comparativo = pd.concat(all_data_list, ignore_index=True)
        print(f"   - Dados de {df_comparativo['Instituicao'].unique()} carregados.")
        
        # 2. Gerar Gráfico
        base_comp = alt.Chart(df_comparativo).encode(
            x=alt.X('Mes_Num:O', axis=alt.Axis(title='Mês')),
            color=alt.Color('Instituicao:N', title='Instituição'),
            tooltip=['Instituicao', 'Mes_Ano', 
                     alt.Tooltip('Total_Emissoes_KgCO2eq', title='Emissões ($KgCO_2eq$)', format=',.0f'),
                     alt.Tooltip('Total_Distancia_Km', title='Distância (km)', format=',.0f'),
                     alt.Tooltip('Total_Passagens', title='Passagens (R$)', format=',.2f')]
        ).properties(width=700)

        # Usa o helper
        chart_comp_emissoes = self._create_chart_with_text(base_comp, 'Total_Emissoes_KgCO2eq', 'Total Emissões ($KgCO_2eq$)', ',.0f')
        chart_comp_distancia = self._create_chart_with_text(base_comp, 'Total_Distancia_Km', 'Total Distância (km)', ',.0f')
        chart_comp_passagens = self._create_chart_with_text(base_comp, 'Total_Passagens', 'Total Passagens (R$)', ',.0f')

        dashboard_comparativo = alt.vconcat(
            chart_comp_emissoes, chart_comp_distancia, chart_comp_passagens
        ).properties(
            title=f"Comparativo Institucional de Tendências Mensais - Ano {self.ano}"
        )
        
        # 3. Salvar PDF
        instituicoes_list = sorted(df_comparativo['Instituicao'].unique())
        instituicoes_suffix = "_".join(instituicoes_list)
        nome_arquivo = f'dashboard_comparativo_institucional_{self.ano}_{instituicoes_suffix}.pdf'
        arquivo_dashboard_comp = os.path.join(self.pasta_relatorios_mensais, nome_arquivo)
        
        try:
            dashboard_comparativo.save(arquivo_dashboard_comp)
            print(f"   - ✅ PDF comparativo salvo em: '{arquivo_dashboard_comp}'")
        except Exception as e:
            print(f"   - ❌ Erro ao salvar PDF: {e}")
            print("   -    -> Certifique-se de ter 'vl-convert-python' instalado (pip install vl-convert-python)")
            
    # --- FUNÇÃO DE LIMPEZA DO BASELINE CORRIGIDA ---

    def _clean_numeric_value(self, value_in):
        """
        Helper para limpar valores numéricos formatados (R$, %, Km) de um CSV,
        lidando com formatos PT-BR (1.234,56) e US (1,234.56).
        """
        if pd.isna(value_in): return np.nan
        if isinstance(value_in, (int, float)): return float(value_in)
        try:
            s = str(value_in).strip()
            # Remove R$, KgCO2eq, Km, % e espaços
            s = re.sub(r'(R\$|\s?KgCO2eq|\s?Km|%)', '', s, flags=re.IGNORECASE).strip()
            
            # *** LÓGICA DE LIMPEZA CORRIGIDA ***
            
            # Detecta se a vírgula é o decimal (formato PT: 1.234,56 ou 1234,56)
            is_pt_br = ',' in s and ('.' not in s or s.rfind(',') > s.rfind('.'))
            
            if is_pt_br:
                # Formato PT-BR: Remove '.' de milhar, troca ',' por '.' decimal
                s = s.replace('.', '').replace(',', '.')
            else:
                # Formato US: Remove ',' de milhar. O '.' decimal já está correto.
                s = s.replace(',', '')
            
            num = float(s)
            return num
        except: 
            return np.nan
    # --- FIM DA CORREÇÃO ---

    def _get_baseline_values(self, orgao):
        """Carrega o baseline do ano anterior (lógica da Célula 55a3cf76)."""
        ano_anterior = self.ano - 1
        pasta_metricas_anterior = f'dadosViagens/dados_viagens{ano_anterior}/metricas_scores'
        # Nome de arquivo agora usa o padrão exato que estamos salvando
        padrao_arquivo = os.path.join(pasta_metricas_anterior, f"relatorio_metricas_scores_{orgao}_{ano_anterior}.csv")
        
        lista_arquivos = glob.glob(padrao_arquivo)
        if lista_arquivos:
            try:
                # Pega o arquivo (não precisa do 'max' se só houver um)
                arquivo_relatorio_anterior = lista_arquivos[0]
                print(f"   - 🔄 Lendo baseline do arquivo: '{os.path.basename(arquivo_relatorio_anterior)}'")
                # Lê o CSV salvo com separador ;
                # NÃO definimos 'decimal' aqui, pois a coluna 'Valor' é mista (strings e números)
                df_anterior = pd.read_csv(arquivo_relatorio_anterior, sep=';') 
                
                # Extrai valores de Emissões e Custo Total do ano anterior
                valor_emissao_anterior_str = df_anterior.loc[(df_anterior['Indicador/Métrica'] == 'ED1.1_Total_Emissions_KgCO2eq') & (df_anterior['Tipo'] == 'Métrica Bruta'), 'Valor'].iloc[0]
                valor_custo_anterior_str = df_anterior.loc[(df_anterior['Indicador/Métrica'] == 'ED2.1_Total_Costs_R$') & (df_anterior['Tipo'] == 'Métrica Bruta'), 'Valor'].iloc[0]
                
                # Usa a função de limpeza corrigida
                valor_emissao_anterior_num = self._clean_numeric_value(valor_emissao_anterior_str)
                valor_custo_anterior_num = self._clean_numeric_value(valor_custo_anterior_str)

                if pd.notna(valor_emissao_anterior_num) and pd.notna(valor_custo_anterior_num):
                    print(f"   - ✅ Baseline dinâmico carregado: Emissões={valor_emissao_anterior_num:,.2f} | Custo={valor_custo_anterior_num:,.2f}")
                    return valor_emissao_anterior_num, valor_custo_anterior_num
                else:
                    print("   - ⚠️ Não foi possível extrair valores do baseline anterior. Usando fallback.")
                    return self.BASELINE_HISTORICO_ED1_1, self.BASELINE_HISTORICO_ED2_1
                
            except Exception as e:
                print(f"   - ❌ Erro ao ler baseline anterior: {e}. Usando fallback histórico.")
                return self.BASELINE_HISTORICO_ED1_1, self.BASELINE_HISTORICO_ED2_1
        else:
            print(f"   - Nenhum relatório de {ano_anterior} encontrado (padrão: {padrao_arquivo}). Usando fallback histórico.")
            return self.BASELINE_HISTORICO_ED1_1, self.BASELINE_HISTORICO_ED2_1
            
    def _format_metric_value(self, row): 
        """Helper para formatar a coluna 'Valor' do relatório final. FORÇA o formato PT-BR."""
        indicador = row['Indicador/Métrica']; valor = row['Valor']; tipo = row['Tipo']
        if pd.isna(valor): return 'N/A'
        
        # Função interna para formatar PT-BR
        def format_pt_br(val, decimals=2):
            return f"{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

        if tipo == 'Score (0 a 1)': return format_pt_br(valor, 4)
        if tipo == 'Variação vs Baseline': return f"{format_pt_br(valor * 100)}%"
        if tipo == 'Baseline':
            if 'R$' in indicador: return f"R$ {format_pt_br(valor)}"
            if 'KgCO2eq' in indicador: return f"{format_pt_br(valor)}"
        
        # Métrica Bruta
        if 'Percent' in indicador: return f"{format_pt_br(valor)}%"
        if 'R$' in indicador or 'Cost' in indicador: return f"R$ {format_pt_br(valor)}"
        if 'KgCO2eq' in indicador or 'Emissions' in indicador: return f"{format_pt_br(valor)} KgCO2eq"
        if 'Km' in indicador or 'Distance' in indicador: return f"{format_pt_br(valor)} Km"
        if 'Count' in indicador or 'Trips' in indicador: return f"{int(valor)}" 
        return f"{format_pt_br(valor)}"

    def generate_metrics_report(self, orgao: str):
        """Gera o relatório de métricas e scores (lógica de 'metricas.ipynb')."""
        print(f"🔄 Gerando Relatório de Métricas para {orgao}...")
        df = self._load_master_file(orgao)
        if df.empty:
            print(f"   - ⚠️ Relatório de métricas pulado para {orgao} (arquivo mestre vazio ou não encontrado).")
            return
            
        # --- 1. Preparar Dados ---
        colunas_numericas = ['Distância (GCD)', 'Emissões (KgCO2eq)', 'Valor passagens', 'Valor diárias', 'Valor outros gastos']
        
        for col in colunas_numericas:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
            
        df['Custo_Total_Viagem'] = df[['Valor passagens', 'Valor diárias', 'Valor outros gastos']].sum(axis=1)
        total_viajantes_unicos = df['CPF viajante'].nunique()
        total_viagens = len(df)
        total_distancia = df['Distância (GCD)'].sum()
        total_emissoes = df['Emissões (KgCO2eq)'].sum()
        custo_total_geral = df['Custo_Total_Viagem'].sum()

        # --- 2. Calcular Métricas Brutas ---
        metrics_brutas = {}
        metrics_brutas['ED1.1_Total_Emissions_KgCO2eq'] = total_emissoes
        emiss_evitaveis = df.loc[df['Categoria Distância'] == 'Muito Curta (Evitável)', 'Emissões (KgCO2eq)'].sum()
        metrics_brutas['ED1.2_Avoidable_Emissions_KgCO2eq'] = emiss_evitaveis
        metrics_brutas['ED1.3_Avg_Emissions_per_Traveler'] = (total_emissoes / total_viajantes_unicos) if total_viajantes_unicos > 0 else 0
        metrics_brutas['ED1.4_Avg_Emissions_per_Trip'] = (total_emissoes / total_viagens) if total_viagens > 0 else 0
        metrics_brutas['ED2.1_Total_Costs_R$'] = custo_total_geral
        metrics_brutas['ED2.2_Avg_Cost_per_Traveler'] = (custo_total_geral / total_viajantes_unicos) if total_viajantes_unicos > 0 else 0
        metrics_brutas['ED2.3_Total_Trips'] = total_viagens
        metrics_brutas['ED2.4_Avg_Cost_per_Trip'] = (custo_total_geral / total_viagens) if total_viagens > 0 else 0
        metrics_brutas['ED2.5_Avg_Cost_per_Km'] = (custo_total_geral / total_distancia) if total_distancia > 0 else 0
        metrics_brutas['ED3.1_Total_Distance_Km'] = total_distancia
        metrics_brutas['ED3.2_Avg_Distance_per_Traveler'] = (total_distancia / total_viajantes_unicos) if total_viajantes_unicos > 0 else 0
        metrics_brutas['ED3.3_Avg_Distance_per_Trip'] = (total_distancia / total_viagens) if total_viagens > 0 else 0
        
        # Métricas DF1 (Governança)
        total_urgentes = (df['Viagem Urgente'].astype(str).str.strip().str.upper() == 'SIM').sum()
        perc_urgentes = (total_urgentes / total_viagens * 100) if total_viagens > 0 else 0
        metrics_brutas['DF1.4_Urgent_Trips_Percent'] = perc_urgentes
        metrics_brutas['DF1.4_Urgent_Trips_Count'] = total_urgentes
        
        urgente_mask = df['Viagem Urgente'].astype(str).str.strip().str.upper() == 'SIM'
        sem_justif_mask = df['Justificativa Urgência Viagem'].astype(str).str.strip().fillna('Sem informação').str.upper() == 'SEM INFORMAÇÃO'
        urgentes_sem_justificativa_count = df[urgente_mask & sem_justif_mask].shape[0]
        perc_urgentes_sem_justif = (urgentes_sem_justificativa_count / total_viagens * 100) if total_viagens > 0 else 0
        metrics_brutas['DF1.5_Urgent_Trips_wo_Justif_Percent'] = perc_urgentes_sem_justif
        metrics_brutas['DF1.5_Urgent_Trips_wo_Justif_Count'] = urgentes_sem_justificativa_count

        metrics_df = pd.DataFrame(metrics_brutas.items(), columns=['Indicador/Métrica', 'Valor'])
        metrics_df['Tipo'] = 'Métrica Bruta'
        
        # --- 3. Carregar Baseline ---
        BASELINE_ED1_1, BASELINE_ED2_1 = self._get_baseline_values(orgao)
        baselines_df = pd.DataFrame([
            {'Indicador/Métrica': 'ED1.1_Baseline_KgCO2eq', 'Valor': BASELINE_ED1_1, 'Tipo': 'Baseline'},
            {'Indicador/Métrica': 'ED2.1_Baseline_R$', 'Valor': BASELINE_ED2_1, 'Tipo': 'Baseline'}
        ])
        
        # --- 4. Calcular Scores e Variações ---
        scores = {}
        variacoes = {}

        # Score DF1.5
        df1_5_proporcao = (urgentes_sem_justificativa_count / total_viagens) if total_viagens > 0 else 0
        scores['DF1.5_Score'] = max(0, 1.0 - df1_5_proporcao)
        variacoes['DF1.5_Proporção_Urg_s_Just'] = df1_5_proporcao
        
        # Score ED1.1
        variacao_ed1_1 = (total_emissoes - BASELINE_ED1_1) / BASELINE_ED1_1 if BASELINE_ED1_1 > 0 else 0
        scores['ED1.1_Score'] = 1.0 if total_emissoes <= BASELINE_ED1_1 else max(0, 1.0 - (variacao_ed1_1 / 2.0))
        variacoes['ED1.1_Variação_vs_Baseline'] = variacao_ed1_1
        
        # Score ED2.1
        variacao_ed2_1 = (custo_total_geral - BASELINE_ED2_1) / BASELINE_ED2_1 if BASELINE_ED2_1 > 0 else 0
        scores['ED2.1_Score'] = 1.0 if custo_total_geral <= BASELINE_ED2_1 else max(0, 1.0 - (variacao_ed2_1 / 2.0))
        variacoes['ED2.1_Variação_vs_Baseline'] = variacao_ed2_1

        scores_df = pd.DataFrame(scores.items(), columns=['Indicador/Métrica', 'Valor'])
        scores_df['Tipo'] = 'Score (0 a 1)'
        variacoes_df = pd.DataFrame(variacoes.items(), columns=['Indicador/Métrica', 'Valor'])
        variacoes_df['Tipo'] = 'Variação vs Baseline'
        
        # --- 5. Combinar e Salvar Relatório ---
        relatorio_final = pd.concat([
            metrics_df,
            baselines_df,
            variacoes_df,
            scores_df
        ], ignore_index=True)

        # Ordenar
        ordem_indicadores = [
            'ED1.1_Total_Emissions_KgCO2eq', 'ED1.1_Baseline_KgCO2eq', 'ED1.1_Variação_vs_Baseline', 'ED1.1_Score',
            'ED1.2_Avoidable_Emissions_KgCO2eq', 'ED1.3_Avg_Emissions_per_Traveler', 'ED1.4_Avg_Emissions_per_Trip',
            'ED2.1_Total_Costs_R$', 'ED2.1_Baseline_R$', 'ED2.1_Variação_vs_Baseline', 'ED2.1_Score',
            'ED2.2_Avg_Cost_per_Traveler', 'ED2.3_Total_Trips', 'ED2.4_Avg_Cost_per_Trip', 'ED2.5_Avg_Cost_per_Km',
            'ED3.1_Total_Distance_Km', 'ED3.2_Avg_Distance_per_Traveler', 'ED3.3_Avg_Distance_per_Trip',
            'DF1.4_Urgent_Trips_Percent', 'DF1.4_Urgent_Trips_Count',
            'DF1.5_Urgent_Trips_wo_Justif_Percent', 'DF1.5_Urgent_Trips_wo_Justif_Count', 'DF1.5_Proporção_Urg_s_Just', 'DF1.5_Score'
        ]
        relatorio_final['Indicador/Métrica'] = pd.Categorical(relatorio_final['Indicador/Métrica'], categories=ordem_indicadores, ordered=True)
        relatorio_final.sort_values('Indicador/Métrica', inplace=True)
        
        # Formatar a coluna Valor ANTES de salvar
        relatorio_final_formatado = relatorio_final.copy()
        relatorio_final_formatado['Valor'] = relatorio_final_formatado.apply(self._format_metric_value, axis=1)
        
        relatorio_final_formatado = relatorio_final_formatado[['Indicador/Métrica', 'Tipo', 'Valor']] # Reordena colunas

        # Salvar
        nome_arquivo_saida = f"relatorio_metricas_scores_{orgao}_{self.ano}.csv"
        caminho_saida = os.path.join(self.pasta_metricas, nome_arquivo_saida)
        
        # Salva o CSV com ; e , para compatibilidade com Excel-PTBR
        relatorio_final_formatado.to_csv(caminho_saida, index=False, sep=';', decimal=',')
        print(f"   - ✅ Relatório de Métricas (Completo) salvo em: '{caminho_saida}'")