# main.py
import time
from viagens.downloader import ViagensDownloader
from viagens.geocoder import GeoCacheManager
from viagens.processor import ViagemProcessor
from viagens.reporting import ReportGenerator
from viagens.filtro import Filtro

# --- CONFIGURAÇÃO GLOBAL ---
ANOS_PARA_PROCESSAR = [2023,2024,2025] 
ORGS_PARA_PROCESSAR = ['UFPB', 'UFCG'] 
BAIXAR_NOVOS_DADOS = False 
# BAIXAR_NOVOS_DADOS = True 

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



def main():
    start_time = time.time()
    print("--- INICIALIZANDO GEOCODER (CACHE MANAGER) ---")
    geocoder = GeoCacheManager(user_agent="MeuProjetoSustentabilidade/1.0")
    
    # Loop principal (Processamento Anual)
    for ano in ANOS_PARA_PROCESSAR:
        print(f"\n{'='*30} INICIANDO ANO: {ano} {'='*30}")
        
        dados_brutos = etapa_obter_dados(ano)
        if dados_brutos:
            etapa_processar_geral(ano, dados_brutos, geocoder)
        else:
            continue

        for org in ORGS_PARA_PROCESSAR:
            etapa_relatorios_instituicao(ano, org)

        etapa_comparativo_ano(ano)

    # --- NOVA ETAPA FINAL: GERAÇÃO DA MATRIZ EXCEL CONSOLIDADA ---
    print(f"\n{'='*30} GERANDO MATRIZES EXCEL CONSOLIDADAS {'='*30}")
    
    # Instanciamos o gerador (o ano aqui é irrelevante, usamos só os métodos)
    reporter_final = ReportGenerator(ano=2025) 
    
    for org in ORGS_PARA_PROCESSAR:
        # Gera a matriz contendo apenas os anos que você quer
        reporter_final.generate_excel_matrix(orgao=org, anos_selecionados=[2024, 2025])

    end_time = time.time()
    print(f"\n{'='*50}")
    print(f"✅ FLUXO DE TRABALHO CONCLUÍDO COM SUCESSO!")
    print(f"   Tempo total: {end_time - start_time:.2f} segundos.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()