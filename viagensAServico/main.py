# main.py
import time
from viagens.downloader import ViagensDownloader
from viagens.geocoder import GeoCacheManager
from viagens.processor import ViagemProcessor
from viagens.reporting import ReportGenerator
from viagens.filtro import Filtro # <-- IMPORTA A NOVA CLASSE

# --- CONFIGURAÇÃO PRINCIPAL DO FLUXO ---
ANOS_PARA_PROCESSAR = [2023, 2024, 2025] 
ORGS_PARA_PROCESSAR = ['UFPB', 'UFCG'] # Instituições
BAIXAR_NOVOS_DADOS = False # Mude para True se quiser baixar os dados novamente

# ----------------------------------------

def main():
    start_time = time.time()
    
    # 1. Instanciar o Geocoder (ele é compartilhado)
    print("--- INICIALIZANDO GEOCODER (CACHE MANAGER) ---")
    geocoder = GeoCacheManager(user_agent="MeuProjetoSustentabilidade/1.0")
    
    for ano in ANOS_PARA_PROCESSAR:
        print(f"\n{'='*20} PROCESSANDO ANO: {ano} {'='*20}")
        
        # 2. Obter Dados Brutos (Baixar ou Carregar)
        downloader = ViagensDownloader(ano=ano)
        
        if BAIXAR_NOVOS_DADOS:
            print(f"--- 1. BAIXANDO DADOS PARA {ano} ---")
            viagem_df, passagem_df, trecho_df = downloader.obter_dados_brutos()
        else:
            print(f"--- 1. CARREGANDO DADOS LOCAIS PARA {ano} ---")
            viagem_df, passagem_df, trecho_df = downloader.carregar_csvs()
            
        if viagem_df is None:
            print(f"❌ Falha ao obter dados para {ano}. Pulando este ano.")
            continue
            
        # --- FLUXO MODIFICADO ---

        # 3. Processar (Cria o arquivo 'df_master_ALL_aereo_[ano].csv')
        print(f"\n--- 2. PROCESSANDO ARQUIVO MESTRE 'ALL' PARA {ano} ---")
        processor = ViagemProcessor(ano=ano, geocoder=geocoder)
        processor.load_data(viagem_df, passagem_df, trecho_df)
        processor.process_all() # Salva o arquivo 'ALL'

        # 4. Instanciar Filtro e Repórter
        # O Filtro carrega o arquivo 'ALL' que acabamos de criar
        filtro = Filtro(ano=ano) 
        reporter = ReportGenerator(ano=ano)

        # 5. Loop por Órgão para FILTRAR e REPORTAR
        for org in ORGS_PARA_PROCESSAR:
            print(f"\n--- 3. FILTRANDO E REPORTANDO PARA: {org} / {ano} ---")
            
            # 5a. Filtro: Cria 'df_master_[ORG]_aereo_[ano].csv'
            filtro.filtrar_e_salvar(org) 
            
            # 5b. Repórter: Lê o arquivo que o Filtro acabou de criar
            reporter.generate_monthly_report(orgao=org)
            reporter.generate_metrics_report(orgao=org)

        # 6. Gerar Comparativo (Lê os arquivos mensais que acabaram de ser criados)
        print(f"\n--- 4. GERANDO PDF COMPARATIVO PARA {ano} ---")
        reporter.generate_comparison_pdf()
        
        # --- FIM DO FLUXO MODIFICADO ---

    end_time = time.time()
    print(f"\n{'='*50}")
    print(f"✅ FLUXO DE TRABALHO CONCLUÍDO COM SUCESSO!")
    print(f"   Tempo total: {end_time - start_time:.2f} segundos.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()