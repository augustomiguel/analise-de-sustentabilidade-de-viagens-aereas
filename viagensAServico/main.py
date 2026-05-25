# main.py
import time
from viagens.downloader import ViagensDownloader
from viagens.geocoder import GeoCacheManager
from viagens.processor import ViagemProcessor
from viagens.reporting import ReportGenerator
from viagens.filtro import Filtro

# --- CONFIGURAÇÃO GLOBAL ---
ANOS_PARA_PROCESSAR = [2024,2025]
ORGS_PARA_PROCESSAR = ['UFPB', 'UFCG']

# Define quantos anos no INÍCIO da lista serão usados APENAS para calcular a linha de base
QTD_ANOS_BASELINE = 1

# --- CONTROLE DE EXECUÇÃO (Onde você decide o que roda) ---
RODAR_PROCESSAMENTO_PESADO = True  
RODAR_GERACAO_EXCEL_FINAL = True    

# --- CONFIGURAÇÕES DO DOWNLOADER ---
BAIXAR_NOVOS_DADOS = False 

# ==============================================================================
# FUNÇÕES AUXILIARES (ETAPAS INDIVIDUAIS)
# ==============================================================================
def etapa_obter_dados(ano):
    print(f"--- 1. OBTENDO DADOS BRUTOS PARA {ano} ---")
    downloader = ViagensDownloader(ano=ano)
    if BAIXAR_NOVOS_DADOS: return downloader.obter_dados_brutos()
    else: return downloader.carregar_csvs()

def etapa_processar_geral(ano, dados_brutos, geocoder):
    print(f"\n--- 2. PROCESSANDO ARQUIVO MESTRE 'ALL' PARA {ano} ---")
    viagem_df, passagem_df, trecho_df = dados_brutos
    processor = ViagemProcessor(ano=ano, geocoder=geocoder)
    processor.load_data(viagem_df, passagem_df, trecho_df)
    processor.process_all() 

def etapa_filtrar_e_reportar(ano, orgao, is_baseline):
    print(f"\n--- 3. FILTRANDO E REPORTANDO PARA: {orgao} / {ano} ---")
    
    # O filtro SEMPRE precisa rodar, pois o Baseline lê o df_master do órgão desses anos
    filtro = Filtro(ano=ano)
    filtro.filtrar_e_salvar(orgao)
    
    # SE FOR ANO DE BASELINE, ENCERRA AQUI E NÃO GERA GRÁFICOS
    if is_baseline:
        print(f"   -> ⏭️ Ano {ano} reservado para Baseline. Pulando geração de Dashboards e PDFs.")
        return
        
    reporter = ReportGenerator(ano=ano)
    baseline_dinamico = reporter.calcular_baseline_dinamico(orgao, ANOS_PARA_PROCESSAR)
    
    reporter.generate_monthly_report(orgao=orgao)
    reporter.generate_metrics_report(orgao=orgao, baseline=baseline_dinamico)
    reporter.generate_consolidated_dashboard(orgao=orgao, baseline=baseline_dinamico)
    reporter.generate_index_panel(orgao=orgao, baseline=baseline_dinamico)
    reporter.juntar_pdfs_em_um(orgao=orgao)

# ==============================================================================
# GRANDES BLOCOS DE EXECUÇÃO
# ==============================================================================

def executar_fluxo_anual():
    """Executa o download, processamento e relatórios anuais."""
    print("\n🚀 INICIANDO FLUXO DE PROCESSAMENTO ANUAL COMPLETO...")
    
    print("--- INICIALIZANDO GEOCODER (CACHE MANAGER) ---")
    geocoder = GeoCacheManager(user_agent="MeuProjetoSustentabilidade/1.0")

    # Identifica quais são os anos de baseline (Ex: 2011 e 2012)
    anos_baseline = ANOS_PARA_PROCESSAR[:QTD_ANOS_BASELINE]

    for ano in ANOS_PARA_PROCESSAR:
        print(f"\n{'='*30} INICIANDO ANO: {ano} {'='*30}")
        
        # Etapa 1: Obter Dados
        dados_brutos = etapa_obter_dados(ano)
        
        # Etapa 2: Processar Mestre (Necessário para achar a distância e emissões)
        if dados_brutos:
            etapa_processar_geral(ano, dados_brutos, geocoder)
        else:
            print(f"❌ Pulei o ano {ano} por falta de dados.")
            continue

        is_baseline = (ano in anos_baseline)

        # Etapa 3: Relatórios por Instituição
        for org in ORGS_PARA_PROCESSAR:
            etapa_filtrar_e_reportar(ano, org, is_baseline)


def executar_consolidacao_excel():
    """Gera apenas a planilha Excel final consolidando todos os anos reais da pesquisa."""
    print(f"\n{'='*30} GERANDO MATRIZES EXCEL CONSOLIDADAS {'='*30}")
    
    # Exclui os anos de baseline da tabela do Excel!
    anos_relatorios = ANOS_PARA_PROCESSAR[QTD_ANOS_BASELINE:]

    
    if not anos_relatorios:
        print("⚠️ Não há anos suficientes para gerar relatório além do baseline.")
        return
        
    reporter_final = ReportGenerator(ano=anos_relatorios) 
    
    for org in ORGS_PARA_PROCESSAR:
        reporter_final.generate_excel_matrix(orgao=org, anos_selecionados=anos_relatorios)

# ==============================================================================
# MAIN (PONTO DE ENTRADA)
# ==============================================================================

def main():
    start_time = time.time()

    if RODAR_PROCESSAMENTO_PESADO:
        executar_fluxo_anual()
    else:
        print("⏭️  PULA: Processamento pesado desativado.")

    if RODAR_GERACAO_EXCEL_FINAL:
        executar_consolidacao_excel()
    else:
        print("⏭️  PULA: Geração de Excel desativada.")

    end_time = time.time()
    print(f"\n{'='*50}")
    print(f"✅ FIM DO SCRIPT!")
    print(f"   Tempo total: {end_time - start_time:.2f} segundos.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()