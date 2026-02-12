# main.py
import time
from viagens.downloader import ViagensDownloader
from viagens.geocoder import GeoCacheManager
from viagens.processor import ViagemProcessor
from viagens.reporting import ReportGenerator
from viagens.filtro import Filtro

# --- CONFIGURAÇÃO GLOBAL ---
ANOS_PARA_PROCESSAR = [2019,2020,2021,2022,2023,2024,2025]

ORGS_PARA_PROCESSAR = ['UFPB', 'UFCG']

# --- CONTROLE DE EXECUÇÃO (Onde você decide o que roda) ---
RODAR_PROCESSAMENTO_PESADO = False  # Coloque True se quiser processar tudo
RODAR_GERACAO_EXCEL_FINAL = True    # Coloque True para gerar a planilha consolidada

# --- CONFIGURAÇÕES DO DOWNLOADER ---
BAIXAR_NOVOS_DADOS = False # Se True, baixa do portal. Se False, usa os CSVs locais.

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

def etapa_relatorios_instituicao(ano, orgao):
    print(f"\n--- 3. FILTRANDO E REPORTANDO PARA: {orgao} / {ano} ---")
    filtro = Filtro(ano=ano)
    filtro.filtrar_e_salvar(orgao)
    
    reporter = ReportGenerator(ano=ano)
    reporter.generate_monthly_report(orgao=orgao)
    reporter.generate_metrics_report(orgao=orgao)
    reporter.generate_consolidated_dashboard(orgao=orgao)

def etapa_comparativo_ano(ano):
    print(f"\n--- 4. GERANDO PDF COMPARATIVO PARA {ano} ---")
    reporter = ReportGenerator(ano=ano)
    reporter.generate_comparison_pdf()

# ==============================================================================
# GRANDES BLOCOS DE EXECUÇÃO
# ==============================================================================

def executar_fluxo_anual():
    """Executa o download, processamento e relatórios anuais (Processo Demorado)."""
    print("\n🚀 INICIANDO FLUXO DE PROCESSAMENTO ANUAL COMPLETO...")
    
    # Inicializa o Geocoder apenas uma vez para reaproveitar o cache
    print("--- INICIALIZANDO GEOCODER (CACHE MANAGER) ---")
    geocoder = GeoCacheManager(user_agent="MeuProjetoSustentabilidade/1.0")

    for ano in ANOS_PARA_PROCESSAR:
        print(f"\n{'='*30} INICIANDO ANO: {ano} {'='*30}")
        
        # Etapa 1: Obter Dados
        dados_brutos = etapa_obter_dados(ano)
        
        # Etapa 2: Processar Mestre
        if dados_brutos:
            etapa_processar_geral(ano, dados_brutos, geocoder)
        else:
            print(f"❌ Pulei o ano {ano} por falta de dados.")
            continue

        # Etapa 3: Relatórios por Instituição
        for org in ORGS_PARA_PROCESSAR:
            etapa_relatorios_instituicao(ano, org)

        # Etapa 4: Comparativo do Ano
        etapa_comparativo_ano(ano)

def executar_consolidacao_excel():
    """Gera apenas a planilha Excel final consolidando todos os anos (Rápido)."""
    print(f"\n{'='*30} GERANDO MATRIZES EXCEL CONSOLIDADAS {'='*30}")
    
    # Instanciamos o gerador (o ano aqui é irrelevante, usamos só os métodos)
    reporter_final = ReportGenerator(ano=2025) 
    
    for org in ORGS_PARA_PROCESSAR:
        # CORREÇÃO IMPORTANTE: Passamos a lista direta ANOS_PARA_PROCESSAR
        # Sem colchetes extras ao redor dela!
        reporter_final.generate_excel_matrix(orgao=org, anos_selecionados=ANOS_PARA_PROCESSAR)

# ==============================================================================
# MAIN (PONTO DE ENTRADA)
# ==============================================================================

def main():
    start_time = time.time()

    # 1. Decide se roda o pesado
    if RODAR_PROCESSAMENTO_PESADO:
        executar_fluxo_anual()
    else:
        print("⏭️  PULA: Processamento pesado desativado na configuração.")

    # 2. Decide se roda o Excel final
    if RODAR_GERACAO_EXCEL_FINAL:
        executar_consolidacao_excel()
    else:
        print("⏭️  PULA: Geração de Excel desativada na configuração.")

    end_time = time.time()
    print(f"\n{'='*50}")
    print(f"✅ FIM DO SCRIPT!")
    print(f"   Tempo total: {end_time - start_time:.2f} segundos.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()