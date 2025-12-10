# main.py
import time
from viagens.downloader import ViagensDownloader
from viagens.geocoder import GeoCacheManager
from viagens.processor import ViagemProcessor
from viagens.reporting import ReportGenerator
from viagens.filtro import Filtro

# --- CONFIGURAÇÃO GLOBAL ---
ANOS_PARA_PROCESSAR = [2023, 2024, 2025] 
ORGS_PARA_PROCESSAR = ['UFPB', 'UFCG'] 
BAIXAR_NOVOS_DADOS = False 

# ==============================================================================
# FUNÇÕES DE CADA ETAPA DO PIPELINE
# ==============================================================================

def etapa_obter_dados(ano):
    """
    Etapa 1: Baixa (se necessário) e carrega os CSVs brutos (Viagem, Passagem, Trecho).
    Retorna uma tupla (viagem_df, passagem_df, trecho_df) ou None se falhar.
    """
    print(f"--- 1. OBTENDO DADOS BRUTOS PARA {ano} ---")
    downloader = ViagensDownloader(ano=ano)
    
    if BAIXAR_NOVOS_DADOS:
        return downloader.obter_dados_brutos()
    else:
        return downloader.carregar_csvs()

def etapa_processar_geral(ano, dados_brutos, geocoder):
    """
    Etapa 2: Processa TODAS as viagens (limpeza, geocoding, cálculo de emissões).
    Gera o arquivo 'df_master_ALL_aereo_[ano].csv'.
    """
    print(f"\n--- 2. PROCESSANDO ARQUIVO MESTRE 'ALL' PARA {ano} ---")
    viagem_df, passagem_df, trecho_df = dados_brutos
    
    # Instancia o processador com o geocoder compartilhado
    processor = ViagemProcessor(ano=ano, geocoder=geocoder)
    processor.load_data(viagem_df, passagem_df, trecho_df)
    
    # Executa o ETL pesado e salva o arquivo ALL
    processor.process_all() 

def etapa_relatorios_instituicao(ano, orgao):
    """
    Etapa 3: Filtra o arquivo 'ALL' para uma instituição específica e gera seus relatórios
    (CSV Mensal, CSV Métricas, PDF Dashboard Executivo, PDF Dashboard Métricas).
    """
    print(f"\n--- 3. FILTRANDO E REPORTANDO PARA: {orgao} / {ano} ---")
    
    # 3a. Filtrar (Cria o recorte da instituição)
    filtro = Filtro(ano=ano)
    filtro.filtrar_e_salvar(orgao)
    
    # 3b. Gerar Relatórios
    reporter = ReportGenerator(ano=ano)
    
    # Gera CSVs
    reporter.generate_monthly_report(orgao=orgao)
    reporter.generate_metrics_report(orgao=orgao)
    
    # Gera PDFs Visuais
    reporter.generate_metrics_dashboard(orgao=orgao)   # Barras (Scores)
    reporter.generate_executive_dashboard(orgao=orgao) # Pizza/Barras (Vínculo)

def etapa_comparativo_ano(ano):
    """
    Etapa 4: Gera o PDF comparativo entre as instituições processadas naquele ano.
    """
    print(f"\n--- 4. GERANDO PDF COMPARATIVO PARA {ano} ---")
    reporter = ReportGenerator(ano=ano)
    reporter.generate_comparison_pdf()

# ==============================================================================
# BLOCO PRINCIPAL (ORQUESTRAÇÃO)
# ==============================================================================

def main():
    start_time = time.time()
    
    # Inicializa o Geocoder uma única vez (cache compartilhado)
    print("--- INICIALIZANDO GEOCODER (CACHE MANAGER) ---")
    geocoder = GeoCacheManager(user_agent="MeuProjetoSustentabilidade/1.0")
    
    for ano in ANOS_PARA_PROCESSAR:
        print(f"\n{'='*30} INICIANDO ANO: {ano} {'='*30}")
        
        # ---------------------------------------------------------
        # ETAPA 1: Carregar Dados
        # ---------------------------------------------------------
        dados_brutos = etapa_obter_dados(ano)
        
        if dados_brutos[0] is None: # Se falhou ao carregar (viagem_df é None)
            print(f"❌ Ppulando ano {ano} por falha no carregamento de dados.")
            continue

        # ---------------------------------------------------------
        # ETAPA 2: Processamento Pesado (Gera df_master_ALL)
        # Comente esta linha se você já processou o arquivo 'ALL' e quer apenas refazer relatórios
        # ---------------------------------------------------------
        etapa_processar_geral(ano, dados_brutos, geocoder)

        # ---------------------------------------------------------
        # ETAPA 3: Relatórios Individuais (Por Órgão)
        # ---------------------------------------------------------
        for org in ORGS_PARA_PROCESSAR:
            etapa_relatorios_instituicao(ano, org)

        # ---------------------------------------------------------
        # ETAPA 4: Comparativo Final do Ano
        # ---------------------------------------------------------
        etapa_comparativo_ano(ano)

    end_time = time.time()
    print(f"\n{'='*50}")
    print(f"✅ FLUXO DE TRABALHO CONCLUÍDO COM SUCESSO!")
    print(f"   Tempo total: {end_time - start_time:.2f} segundos.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()