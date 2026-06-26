import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import time

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ViagensAPI:
    def __init__(self, chave_api):
        """
        Inicializa o cliente da API de Viagens
        
        Args:
            chave_api (str): Chave de acesso à API do Portal da Transparência
        """
        self.base_url = "https://api.portaldatransparencia.gov.br/api-de-dados/viagens"
        self.headers = {
            "accept": "*/*",
            "chave-api-dados": chave_api
        }
        self.max_paginas = 10  # Limite de páginas para evitar loops infinitos
        self.timeout = 30  # Tempo máximo de espera por requisição (segundos)

    def _fazer_requisicao(self, params):
        """
        Faz uma requisição à API com tratamento de erros
        
        Args:
            params (dict): Parâmetros da consulta
            
        Returns:
            dict or None: Resposta da API ou None em caso de erro
        """
        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição: {str(e)}")
            return None

    def consultar_viagens(self, codigo_orgao, data_ida_de, data_ida_ate, 
                         data_retorno_de=None, data_retorno_ate=None, 
                         pagina_inicial=1):
        """
        Consulta viagens por período e órgão
        
        Args:
            codigo_orgao (str): Código do órgão no SIAFI
            data_ida_de (str): Data de ida inicial (DD/MM/AAAA)
            data_ida_ate (str): Data de ida final (DD/MM/AAAA)
            data_retorno_de (str, optional): Data de retorno inicial (DD/MM/AAAA)
            data_retorno_ate (str, optional): Data de retorno final (DD/MM/AAAA)
            pagina_inicial (int): Página inicial da consulta
            
        Returns:
            list: Lista de viagens ou None em caso de erro
        """
        # Validar período máximo de 1 mês
        data_de = datetime.strptime(data_ida_de, "%d/%m/%Y")
        data_ate = datetime.strptime(data_ida_ate, "%d/%m/%Y")
        
        if (data_ate - data_de).days > 31:
            logging.error("Período máximo de consulta é de 1 mês")
            return None

        params = {
            "dataIdaDe": data_ida_de,
            "dataIdaAte": data_ida_ate,
            "codigoOrgao": codigo_orgao,
            "pagina": pagina_inicial
        }

        # Adicionar filtros de retorno se fornecidos
        if data_retorno_de and data_retorno_ate:
            params.update({
                "dataRetornoDe": data_retorno_de,
                "dataRetornoAte": data_retorno_ate
            })

        todas_viagens = []
        total_registros = 0

        logging.info("Iniciando consulta de viagens...")
        
        while params["pagina"] <= self.max_paginas:
            logging.info(f"Consultando página {params['pagina']}")
            
            dados = self._fazer_requisicao(params)
            if not dados:
                break
                
            if not isinstance(dados, list):
                logging.error(f"Resposta inesperada: {type(dados)}")
                break
                
            if not dados:  # Lista vazia - fim dos dados
                break
                
            todas_viagens.extend(dados)
            total_registros += len(dados)
            params["pagina"] += 1
            
            # Pausa para evitar sobrecarga na API
            time.sleep(0.5)
        
        logging.info(f"Consulta concluída. Total de viagens: {total_registros}")
        return todas_viagens if todas_viagens else None

    @staticmethod
    def processar_dados_viagens(dados_viagens):
        """
        Processa os dados brutos das viagens e retorna um DataFrame
        
        Args:
            dados_viagens (list): Lista de dicionários com dados das viagens
            
        Returns:
            pd.DataFrame: DataFrame com os dados processados ou None em caso de erro
        """
        if not dados_viagens:
            return None
            
        try:
            df = pd.DataFrame(dados_viagens)
            
            # Converter datas
            date_cols = [col for col in df.columns if 'data' in col.lower()]
            for col in date_cols:
                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
            
            # Converter valores monetários
            money_cols = [col for col in df.columns if 'valor' in col.lower()]
            for col in money_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            logging.error(f"Erro no processamento dos dados: {str(e)}")
            return None

def main():
    # Configurações (substitua pela sua chave real)
    CHAVE_API = "9b8e00db8253945fc8e90aa1cd4423be"
    CODIGO_ORGAO = "00018"  # Código do órgão no SIAFI
    
    # Definir período de consulta (máximo 1 mês)
    data_hoje = datetime.now()
    data_um_mes_atras = data_hoje - timedelta(days=30)
    
    data_ida_de = data_um_mes_atras.strftime("%d/%m/%Y")
    data_ida_ate = data_hoje.strftime("%d/%m/%Y")
    
    # Inicializar cliente da API
    api = ViagensAPI(CHAVE_API)
    
    # Consultar viagens
    viagens = api.consultar_viagens(
        codigo_orgao=CODIGO_ORGAO,
        data_ida_de=data_ida_de,
        data_ida_ate=data_ida_ate
    )
    
    if not viagens:
        logging.error("Nenhum dado de viagem foi obtido")
        return
    
    # Processar dados
    df_viagens = ViagensAPI.processar_dados_viagens(viagens)
    
    if df_viagens is not None:
        print("\nDados das viagens:")
        print(df_viagens.head())  # Mostrar primeiras linhas
        print(f"\nTotal de viagens encontradas: {len(df_viagens)}")
        
        # Salvar em CSV se desejar
        # df_viagens.to_csv('viagens.csv', index=False, encoding='utf-8-sig')
    else:
        logging.error("Falha no processamento dos dados")

if __name__ == "__main__":
    main()