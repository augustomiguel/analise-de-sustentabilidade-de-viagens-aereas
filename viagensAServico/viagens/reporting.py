import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import matplotlib.patches as patches
from PyPDF2 import PdfMerger
from viagens.metricas import CalculadoraMetricas

class ReportGenerator:
    def __init__(self, ano: int):
        self.ano = ano
        self.pasta_dados = f'dadosViagens/dados_viagens{self.ano}'
        self.pasta_relatorios_mensais = os.path.join(self.pasta_dados, 'Relatorios_Mensais')
        if not os.path.exists(self.pasta_relatorios_mensais): os.makedirs(self.pasta_relatorios_mensais)
        self.calculadora = CalculadoraMetricas(ano=self.ano)

    def _load_master_file(self, orgao: str) -> pd.DataFrame:
        caminho = os.path.join(self.pasta_dados, f'df_master_{orgao}_aereo_{self.ano}.csv')
        if os.path.exists(caminho): return pd.read_csv(caminho, low_memory=False)
        else: return pd.DataFrame()

    def calcular_baseline_dinamico(self, orgao: str, anos_processamento: list):
        return self.calculadora.calcular_baseline_dinamico(orgao, anos_processamento)

    def generate_monthly_report(self, orgao: str):
        print(f"🔄 Gerando Relatório Mensal (Matplotlib) para {orgao}...")
        df_bruto = self._load_master_file(orgao)
        if df_bruto.empty: return

        df_mensal = self.calculadora.calcular_resumo_mensal(df_bruto)
        if df_mensal.empty: return
        df_mensal.round(2).to_csv(os.path.join(self.pasta_relatorios_mensais, f"relatorio_mensal_{orgao}_aereo_{self.ano}.csv"), index=False)

        try:
            fig, ax1 = plt.subplots(figsize=(10, 5))
            ax1.bar(df_mensal['Mes_Ano'], df_mensal['Total_Passagens'], color='#1f77b4', label='Gastos (R$)')
            ax1.set_ylabel('Valor Gasto (R$ de 2025)', color='#1f77b4', fontweight='bold')
            ax1.tick_params(axis='y', labelcolor='#1f77b4')
            ax1.set_xticks(range(len(df_mensal['Mes_Ano'])))
            ax1.set_xticklabels(df_mensal['Mes_Ano'], rotation=45, ha='right')
            ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('R$ {x:,.0f}'))

            ax2 = ax1.twinx()
            ax2.plot(df_mensal['Mes_Ano'], df_mensal['Total_Emissoes_KgCO2eq'], color='#d62728', marker='o', linewidth=2, label='Emissões')
            ax2.set_ylabel('Emissões (Kg CO2eq)', color='#d62728', fontweight='bold')
            ax2.tick_params(axis='y', labelcolor='#d62728')
            ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f} kg'))

            plt.title(f'Gastos vs Pegada de Carbono Mensal - {orgao}', fontsize=14, fontweight='bold', pad=15)
            fig.tight_layout()
            fig.savefig(os.path.join(self.pasta_relatorios_mensais, f"dashboard_mensal_{orgao}_{self.ano}.pdf"))
            plt.close(fig)
        except Exception as e: print(f"   - ❌ Erro ao gerar gráficos: {e}")

    def generate_metrics_report(self, orgao: str, baseline=None):
        df = self._load_master_file(orgao)
        if df.empty: return
        df.describe().to_csv(os.path.join(self.pasta_relatorios_mensais, f"relatorio_metricas_brutas_{orgao}_{self.ano}.csv"))

    def generate_consolidated_dashboard(self, orgao: str, baseline=None):
        print(f"🔄 Gerando Dashboard Completo Consolidado (Matplotlib) para {orgao}...")
        df_atual = self._load_master_file(orgao)
        if df_atual.empty: return

        df_atual['Emissões (KgCO2eq)'] = pd.to_numeric(df_atual['Emissões (KgCO2eq)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df_atual['Valor passagens'] = pd.to_numeric(df_atual['Valor passagens'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df_atual['Distância (GCD)'] = pd.to_numeric(df_atual['Distância (GCD)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        fator_ano = self.calculadora.fatores_correcao.get(self.ano, 1.0)

        fig = plt.figure(figsize=(16, 10), constrained_layout=True)
        gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1, 1, 1.2])

        ax_custos = fig.add_subplot(gs[0, 0])
        ax_emissoes = fig.add_subplot(gs[0, 1])
        ax_scores = fig.add_subplot(gs[0, 2])
        ax_pizza = fig.add_subplot(gs[1, 0])
        ax_cat_dist = fig.add_subplot(gs[1, 1])
        ax_cat_emiss = fig.add_subplot(gs[1, 2])

        cores_baseline = ['#4c78a8', '#f58518']
        
        # APLICAÇÃO DO FATOR DE INFLAÇÃO NO CUSTO ATUAL
        gasto_atual = df_atual['Valor passagens'].sum() * fator_ano
        emissoes_atual = df_atual['Emissões (KgCO2eq)'].sum()
        gasto_baseline = baseline['Gasto_Medio_Anual'] if baseline else 0
        emissoes_baseline = baseline['Emissoes_Medias_Anuais'] if baseline else 0

        ax_custos.bar(['Atual', 'Baseline'], [gasto_atual, gasto_baseline], color=cores_baseline, edgecolor='black')
        ax_custos.set_title('Comparativo de Custos (R$ de 2025)', fontweight='bold')
        ax_custos.yaxis.set_major_formatter(ticker.StrMethodFormatter('R$ {x:,.0f}'))

        ax_emissoes.bar(['Atual', 'Baseline'], [emissoes_atual, emissoes_baseline], color=cores_baseline, edgecolor='black')
        ax_emissoes.set_title('Comparativo de Emissões', fontweight='bold')
        ax_emissoes.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f} kg'))

        dict_scores = self.calculadora.calcular_indicadores_e_scores(df_atual, baseline)
        lista_scores = [{'Indicador': k.replace('_Score', ''), 'Score': v} for k, v in dict_scores.items() if k.endswith('_Score')]
        df_scores = pd.DataFrame(lista_scores)

        if not df_scores.empty:
            def cor_score(val): return '#d62728' if val < 0.35 else '#ffdd57' if val < 0.70 else '#2ca02c'
            ax_scores.bar(df_scores['Indicador'], df_scores['Score'], color=[cor_score(v) for v in df_scores['Score']], edgecolor='black')
            ax_scores.set_title('Scores do Modelo de Sustentabilidade', fontweight='bold')
            ax_scores.set_ylim(0, 1.1)
            ax_scores.set_xticks(range(len(df_scores['Indicador'])))
            ax_scores.set_xticklabels(df_scores['Indicador'], rotation=45, ha='right')

        if 'Vínculo' in df_atual.columns:
            df_vinculo = df_atual.groupby('Vínculo')['Emissões (KgCO2eq)'].sum().reset_index()
            df_vinculo = df_vinculo[df_vinculo['Emissões (KgCO2eq)'] > 0]
            if not df_vinculo.empty:
                wedges, texts, autotexts = ax_pizza.pie(
                    df_vinculo['Emissões (KgCO2eq)'], autopct='%1.1f%%', startangle=140, pctdistance=0.75, wedgeprops={'edgecolor': 'white'}
                )
                plt.setp(autotexts, size=9, weight="bold")
                ax_pizza.set_title('Emissões por Vínculo', fontweight='bold')
                ax_pizza.legend(wedges, df_vinculo['Vínculo'], title="Vínculo", loc="center left", bbox_to_anchor=(0.9, 0.5), fontsize=9)

        if 'Categoria Distância' in df_atual.columns:
            df_cat = df_atual.groupby('Categoria Distância').agg({'Distância (GCD)': 'sum', 'Emissões (KgCO2eq)': 'sum'}).reset_index()
            labels_cat = df_cat['Categoria Distância']
            cores_mapeadas = [{'Curta Distância': '#4c78a8', 'Longa Distância': '#f58518', 'Muito Curta (Evitável)': '#d62728'}.get(cat, 'gray') for cat in labels_cat]

            ax_cat_dist.bar(labels_cat, df_cat['Distância (GCD)'], color=cores_mapeadas, edgecolor='black')
            ax_cat_dist.set_title('Distância (Km) por Categoria', fontweight='bold')
            ax_cat_dist.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
            ax_cat_dist.set_xticks(range(len(labels_cat)))
            ax_cat_dist.set_xticklabels(labels_cat, rotation=45, ha='right') 

            ax_cat_emiss.bar(labels_cat, df_cat['Emissões (KgCO2eq)'], color=cores_mapeadas, edgecolor='black')
            ax_cat_emiss.set_title('Emissões por Categoria', fontweight='bold')
            ax_cat_emiss.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
            ax_cat_emiss.set_xticks(range(len(labels_cat)))
            ax_cat_emiss.set_xticklabels(labels_cat, rotation=45, ha='right')

        fig.suptitle(f'Dashboard Estratégico de Viagens Aéreas - {orgao} ({self.ano})', fontsize=18, fontweight='bold')
        fig.savefig(os.path.join(self.pasta_relatorios_mensais, f"dashboard_completo_{orgao}_{self.ano}.pdf"), bbox_inches='tight', facecolor='white')
        plt.close(fig)

    def generate_index_panel(self, orgao: str, baseline=None):
        print(f"🔄 Gerando Painel de Índices Hierárquico para {orgao}...")
        df_atual = self._load_master_file(orgao)
        if df_atual.empty: return
        
        scores_brutos = self.calculadora.calcular_indicadores_e_scores(df_atual, baseline)
        indices = self.calculadora.calcular_painel_indices(scores_brutos)

        fig, ax = plt.subplots(figsize=(16, 5))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off') 

        def draw_box(x, y, w, h, title, value, color, text_color='black'):
            rect = patches.Rectangle((x, y), w, h, linewidth=0.5, edgecolor='gray', facecolor=color)
            ax.add_patch(rect)
            ax.text(x + w/2, y + h*0.65, title, ha='center', va='center', fontsize=10, wrap=True, color=text_color)
            ax.text(x + w/2, y + h*0.25, f"{value:.3f}", ha='center', va='center', fontsize=14, fontweight='bold', color=text_color)

        draw_box(0.05, 0.65, 0.30, 0.30, "ÍNDICE GERAL", indices['N1']['Geral'], '#ffffff')
        draw_box(0.05, 0.35, 0.30, 0.30, "Emissões, Deslocamento e Custo", indices['N2']['ED'], '#e2efd9')
        draw_box(0.36, 0.35, 0.30, 0.30, "Motivações para o voo", indices['N2']['DF'], '#ddebf7')
        draw_box(0.67, 0.35, 0.30, 0.30, "Barreiras Institucionais", indices['N2']['IB'], '#fff2cc')
        draw_box(0.05, 0.10, 0.10, 0.25, "Análise de\nEmissões", indices['N3']['ED1'], '#e2efd9')
        draw_box(0.15, 0.10, 0.10, 0.25, "Análise do\nDeslocamento", indices['N3']['ED2'], '#e2efd9')
        draw_box(0.25, 0.10, 0.10, 0.25, "Análise dos\nCustos", indices['N3']['ED3'], '#a8d08d')
        draw_box(0.36, 0.10, 0.15, 0.25, "Incentivo à\nhipermobilidade", indices['N3']['DF1'], '#ddebf7')
        draw_box(0.51, 0.10, 0.15, 0.25, "Propósitos do\nvoo", indices['N3']['DF2'], '#ddebf7')
        draw_box(0.67, 0.10, 0.10, 0.25, "Restrições", indices['N3']['IB1'], '#fff2cc')
        draw_box(0.77, 0.10, 0.10, 0.25, "Incentivo", indices['N3']['IB2'], '#ffe699')
        draw_box(0.87, 0.10, 0.10, 0.25, "Mudança\nOrganizacional", indices['N3']['IB3'], '#bf8f00', text_color='white')

        plt.suptitle(f"Relatório Integrado - {orgao} {self.ano}", x=0.05, y=0.95, ha='left', fontsize=16, fontweight='bold')
        ax.text(0.5, 0.95, "Painel de Índices", ha='center', va='center', fontsize=16, fontweight='bold')

        fig.savefig(os.path.join(self.pasta_relatorios_mensais, f"painel_indices_{orgao}_{self.ano}.pdf"), bbox_inches='tight')
        plt.close(fig)

    def juntar_pdfs_em_um(self, orgao: str):
        caminho_painel = os.path.join(self.pasta_relatorios_mensais, f"painel_indices_{orgao}_{self.ano}.pdf")
        caminho_mensal = os.path.join(self.pasta_relatorios_mensais, f"dashboard_mensal_{orgao}_{self.ano}.pdf")
        caminho_completo = os.path.join(self.pasta_relatorios_mensais, f"dashboard_completo_{orgao}_{self.ano}.pdf")
        caminho_final = os.path.join(self.pasta_relatorios_mensais, f"Relatorio_Oficial_{orgao}_{self.ano}.pdf")

        try:
            merger = PdfMerger()
            if os.path.exists(caminho_painel): merger.append(caminho_painel)
            if os.path.exists(caminho_mensal): merger.append(caminho_mensal)
            if os.path.exists(caminho_completo): merger.append(caminho_completo)
            merger.write(caminho_final)
            merger.close()
        except Exception as e: print(f"   - ❌ Erro ao juntar PDFs: {e}")

    def generate_excel_matrix(self, orgao: str, anos_selecionados: list):
        print(f"   📊 Gerando Matriz Excel Consolidada para {orgao}...")
        metricas = ['Distância', 'Gasto', 'Emissões']
        meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        colunas_multi = pd.MultiIndex.from_product([anos_selecionados, metricas], names=['Ano', 'Métrica'])
        df_final = pd.DataFrame(index=meses_nomes, columns=colunas_multi)
        
        for ano in anos_selecionados:
            caminho_arquivo = os.path.join("dadosViagens", f"dados_viagens{ano}", "Relatorios_Mensais", f"relatorio_mensal_{orgao}_aereo_{ano}.csv")
            if os.path.exists(caminho_arquivo):
                df_origem = pd.read_csv(caminho_arquivo)
                cols_map = {'Total_Distancia_Km': 'Distância', 'Total_Passagens': 'Gasto', 'Total_Emissoes_KgCO2eq': 'Emissões'}
                for _, row in df_origem.iterrows():
                    mes_idx = int(row['Mes_Num']) - 1
                    if 0 <= mes_idx < 12:
                        for col_csv, col_excel in cols_map.items():
                            df_final.loc[meses_nomes[mes_idx], (ano, col_excel)] = float(str(row[col_csv]).replace(',', '.'))

        df_final = df_final.infer_objects(copy=False).fillna(0)
        df_final.loc['Anual'] = df_final.sum()
        df_final.loc['Média'] = df_final.iloc[0:12].mean()

        caminho_excel = os.path.join("dadosViagens", f"matriz_completa_{orgao}.xlsx")
        with pd.ExcelWriter(caminho_excel, engine='openpyxl') as writer:
            df_final.to_excel(writer, sheet_name='Dados', startrow=2)
            writer.sheets['Dados']['A1'] = f"Dados do deslocamento aéreo - {orgao}"
            writer.sheets['Dados']['A1'].font = __import__('openpyxl').styles.Font(size=14, bold=True)