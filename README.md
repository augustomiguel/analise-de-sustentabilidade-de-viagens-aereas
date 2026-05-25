# Calculadora de Pegada de Carbono - Viagens Institucionais
Este projeto automatiza a extração, o tratamento e a análise de dados de viagens a serviço da Administração Pública Federal a partir do Portal da Transparência. O objetivo principal é calcular a pegada de carbono (emissões de KgCO2eq) proveniente de trechos aéreos e gerar painéis de indicadores de sustentabilidade, aplicando uma metodologia de avaliação de desempenho institucional.

# 📋 Pré-requisitos
Para executar o projeto, você precisará do Python 3 instalado e das seguintes bibliotecas:

pandas (Manipulação e estruturação de dados)

numpy (Cálculos matemáticos e vetorização)

requests (Comunicação com APIs externas e download de bases)

matplotlib (Plotar os graficos)

PyPDF2 (Gerar PDF)

# 📁 Estrutura do Projeto
A arquitetura do sistema foi desenhada dividindo responsabilidades entre classes especialistas, orquestradas por um processador central:

main.py: Ponto de entrada do sistema. Controla o fluxo de execução, os anos de análise e as instituições filtradas.

downloader.py: Faz o download automático dos arquivos ZIP do Portal da Transparência, descompacta e realiza uma limpeza agressiva nos cabeçalhos dos arquivos CSV.

processor.py: Classe Facade que orquestra as etapas de limpeza, cálculo de distâncias, cálculo de emissões e construção do arquivo final.

limpador.py: Filtra exclusivamente viagens com trechos aéreos e cruza os identificadores de processo de viagem para garantir a integridade dos dados.

geocoder.py: Consulta a API do Nominatim (OpenStreetMap) para obter as coordenadas (Latitude/Longitude) das cidades e calcula a Distância do Grande Círculo (GCD) usando a fórmula de Haversine. Possui um sistema robusto de cache local para evitar bloqueios de API.

emissoes.py: Aplica fatores de emissão categorizados por distância (Muito Curta, Curta, Longa) para calcular os valores em KgCO2eq e tCO2eq.

construtor.py: Mescla todas as tabelas (Viagem, Passagem, Trechos) e classifica o vínculo do passageiro (Ex: Professor, Acadêmico, Servidor, Externo) com base nos cargos e motivos.

filtro.py: Separa o arquivo mestre consolidado em bases específicas por instituição (ex: UFPB, UFCG) usando expressões regulares.

metricas.py: Implementa as equações de indicadores (ED, DF, IB) e correção monetária pelo IPCA (trazendo valores para o ano-base) para compor a pontuação institucional.

# ⚙️ Como Configurar e Executar
Toda a configuração de escopo da pesquisa é feita diretamente no cabeçalho do arquivo main.py.

## Configuração de Escopo:
Abra o main.py e ajuste as variáveis globais conforme a necessidade da análise:

ANOS_PARA_PROCESSAR: Lista de anos (ex: [2023, 2024, 2025]) que serão baixados e analisados.

ORGS_PARA_PROCESSAR: Siglas das instituições alvo (ex: ['UFPB', 'UFCG']).

QTD_ANOS_BASELINE: Quantidade de anos no início da lista usados exclusivamente para calcular a linha de base dinâmica.

## Controle de Execução:
Ative ou desative as chaves booleanas para pular etapas demoradas durante o desenvolvimento:

RODAR_PROCESSAMENTO_PESADO: Se True, executa o pipeline completo (leitura, geocodificação, emissões).

RODAR_GERACAO_EXCEL_FINAL: Se True, gera as matrizes consolidadas no final.

BAIXAR_NOVOS_DADOS: Se True, força um novo download do Portal da Transparência. Se False, usa os CSVs já existentes na pasta local.

## Iniciando o Script:
Com as configurações ajustadas, rode o comando na raiz do projeto:

    Bash
    python main.py

# 🔄 Fluxo de Dados e Resultados
Durante a execução, o sistema criará as seguintes saídas e caches:

Cache de Coordenadas: O arquivo coordenadas_api_cache.csv e cidades_nao_encontradas.csv armazenam consultas prévias para economizar tempo nas próximas execuções.

Arquivos Mestres: Na pasta dadosViagens/dados_viagens{ano}/, o sistema gera o df_master_ALL_aereo_{ano}.csv contendo todos os órgãos, e arquivos específicos como df_master_UFPB_aereo_{ano}.csv filtrados.

Relatórios Finais: Se os módulos de Reporting estiverem ativos, PDFs consolidados e matrizes Excel serão gerados para os anos que não compõem a linha de base (baseline).