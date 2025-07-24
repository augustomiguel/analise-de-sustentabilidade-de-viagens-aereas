import requests
import pandas as pd
import matplotlib.pyplot as plt
import logging
from datetime import datetime
import time

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def obter_dados_api(codigo_orgao, data_inicial, chave_api, max_paginas=10):
    """
    Obtém dados de contratos da API do Portal da Transparência com tratamento de erros
    
    Args:
        codigo_orgao (str): Código do órgão no SIAPE
        data_inicial (str): Data inicial no formato DD/MM/YYYY
        chave_api (str): Chave de acesso à API
        max_paginas (int): Número máximo de páginas a serem consultadas
        
    Returns:
        list: Lista de contratos ou None em caso de erro
    """
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/contratos"
    params = {
        "codigoOrgao": codigo_orgao,
        "quantidade": 100,  # Máximo permitido por página
        "dataInicial": data_inicial,
        "pagina": 1
    }
    headers = {
        "accept": "*/*",
        "chave-api-dados": chave_api
    }

    dados_paginas = []
    total_contratos = 0

    try:
        logging.info(f"Iniciando coleta de dados para órgão {codigo_orgao}")
        
        while params["pagina"] <= max_paginas:
            logging.info(f"Coletando página {params['pagina']}...")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            dados_json = response.json()
            if not dados_json:
                break
                
            dados_paginas.extend(dados_json)
            total_contratos += len(dados_json)
            params["pagina"] += 1
            
            # Pequena pausa para evitar sobrecarga na API
            time.sleep(0.5)
        
        logging.info(f"Coleta concluída. Total de contratos obtidos: {total_contratos}")
        return dados_paginas
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição à API: {str(e)}")
        return None

def processar_dataframe(dados_brutos):
    """
    Processa os dados brutos da API e retorna um DataFrame organizado
    
    Args:
        dados_brutos (list): Lista de dicionários com dados da API
        
    Returns:
        pd.DataFrame: DataFrame processado ou None em caso de erro
    """
    if not dados_brutos:
        return None
        
    try:
        # Criar DataFrame base
        df = pd.DataFrame(dados_brutos)
        
        # Renomear colunas para evitar conflitos
        df = df.rename(columns={
            'id': 'id_contrato',
            'objeto': 'objeto_contrato',
            'numero': 'numero_contrato'
        })
        
        # Normalizar colunas aninhadas
        colunas_aninhadas = ['compra', 'unidadeGestora', 'fornecedor']
        dfs_normalizados = []
        
        for col in colunas_aninhadas:
            if col in df.columns:
                temp_df = pd.json_normalize(df[col])
                temp_df.columns = [f"{col}_{subcol}" for subcol in temp_df.columns]
                dfs_normalizados.append(temp_df)
        
        # Combinar todos os DataFrames
        df_final = pd.concat([df] + dfs_normalizados, axis=1)
        
        # Remover colunas desnecessárias
        colunas_remover = [
            'compra', 'unidadeGestora', 'fornecedor',
            'orgaoVinculado.codigoSIAFI', 'orgaoVinculado.cnpj',
            'orgaoVinculado.sigla', 'orgaoVinculado.nome',
            'orgaoMaximo.codigo', 'orgaoMaximo.sigla', 'orgaoMaximo.nome',
            'numeroProcesso', 'unidadeGestoraCompras', 'descricaoPoder',
            'cpfFormatado', 'numeroInscricaoSocial', 'tipo'
        ]
        
        # Remover apenas colunas que existem
        colunas_remover = [col for col in colunas_remover if col in df_final.columns]
        df_final = df_final.drop(columns=colunas_remover)
        
        # Renomear colunas após normalização
        df_final = df_final.rename(columns={
            'unidadeGestora_codigo': 'codigo_uge',
            'unidadeGestora_nome': 'nome_uge'
        })
        
        # Converter tipos de dados
        date_cols = [col for col in df_final.columns if 'data' in col.lower()]
        for col in date_cols:
            df_final[col] = pd.to_datetime(df_final[col], format='%d/%m/%Y', errors='coerce')
            
        money_cols = [col for col in df_final.columns if 'valor' in col.lower()]
        for col in money_cols:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
        
        # Remover duplicatas baseadas em valores de contrato
        df_final = df_final.drop_duplicates(
            subset=['valorInicialCompra', 'valorFinalCompra'],
            keep='first'
        )
        
        return df_final
        
    except Exception as e:
        logging.error(f"Erro no processamento dos dados: {str(e)}")
        return None

def analisar_modalidades(df, uge=None):
    """
    Analisa a distribuição de contratos por modalidade de compra
    
    Args:
        df (pd.DataFrame): DataFrame com os dados dos contratos
        uge (str, optional): Código da UGE para filtrar
        
    Returns:
        pd.DataFrame: Contagem por modalidade ou None em caso de erro
    """
    if df is None or df.empty:
        return None
        
    try:
        if uge:
            if 'codigo_uge' not in df.columns:
                logging.warning("Coluna 'codigo_uge' não encontrada para filtrar")
                return None
            df = df[df['codigo_uge'] == uge]
        
        if 'modalidadeCompra' not in df.columns:
            logging.error("Coluna 'modalidadeCompra' não encontrada")
            return None
            
        contagem = (
            df['modalidadeCompra']
            .value_counts()
            .reset_index()
            .rename(columns={
                'index': 'Modalidade de Compra',
                'modalidadeCompra': 'Quantidade de Contratos'
            })
            .sort_values('Quantidade de Contratos', ascending=False)
        )
        
        return contagem
        
    except Exception as e:
        logging.error(f"Erro na análise de modalidades: {str(e)}")
        return None

def plotar_grafico(contagem_modalidades, titulo=None, salvar_arquivo=None):
    """
    Gera um gráfico de barras da distribuição por modalidade
    
    Args:
        contagem_modalidades (pd.DataFrame): DataFrame com os dados
        titulo (str, optional): Título do gráfico
        salvar_arquivo (str, optional): Caminho para salvar a imagem
    """
    if contagem_modalidades is None or contagem_modalidades.empty:
        logging.warning("Dados vazios para plotar gráfico")
        return
        
    try:
        plt.figure(figsize=(12, 6))
        
        # Gráfico de barras
        bars = plt.bar(
            contagem_modalidades['Modalidade de Compra'],
            contagem_modalidades['Quantidade de Contratos'],
            color='#1f77b4'
        )
        
        # Adicionar valores nas barras
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2.,
                height + 0.5,
                f'{int(height)}',
                ha='center',
                va='bottom'
            )
        
        # Formatação
        plt.xticks(rotation=45, ha='right')
        plt.xlabel('Modalidade de Compra', fontsize=12)
        plt.ylabel('Quantidade de Contratos', fontsize=12)
        
        titulo = titulo or 'Distribuição de Contratos por Modalidade de Compra'
        plt.title(titulo, fontsize=14, pad=20)
        
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        if salvar_arquivo:
            plt.savefig(salvar_arquivo, dpi=300, bbox_inches='tight')
            logging.info(f"Gráfico salvo em: {salvar_arquivo}")
        else:
            plt.show()
            
        plt.close()
        
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico: {str(e)}")

def main():
    # Configurações
    CODIGO_ORGAO = "52111"
    DATA_INICIAL = "01/01/2018"
    CHAVE_API = "9b8e00db8253945fc8e90aa1cd4423be"  # Sua chave da API
    UGE_FILTER = "120006"  # Código da UGE específica
    
    # 1. Obter dados da API
    dados_contratos = obter_dados_api(CODIGO_ORGAO, DATA_INICIAL, CHAVE_API)
    
    if not dados_contratos:
        logging.error("Não foi possível obter dados da API")
        return
    
    # 2. Processar os dados
    df_contratos = processar_dataframe(dados_contratos)
    
    if df_contratos is None:
        logging.error("Falha no processamento dos dados")
        return
    
    logging.info(f"Total de contratos processados: {len(df_contratos)}")
    
    # 3. Análise geral
    modalidades_geral = analisar_modalidades(df_contratos)
    if modalidades_geral is not None:
        print("\nDistribuição geral por modalidade:")
        print(modalidades_geral.to_string(index=False))
    
    # 4. Análise específica para UGE
    modalidades_uge = analisar_modalidades(df_contratos, UGE_FILTER)
    if modalidades_uge is not None:
        print(f"\nDistribuição para UGE {UGE_FILTER}:")
        print(modalidades_uge.to_string(index=False))
        
        # 5. Gerar gráfico
        plotar_grafico(
            modalidades_uge,
            titulo=f"Contratos por Modalidade - UGE {UGE_FILTER}",
            salvar_arquivo="contratos_por_modalidade.png"
        )

if __name__ == "__main__":
    main()