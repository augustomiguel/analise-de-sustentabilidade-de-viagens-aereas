# lattes/extrator.py
import xml.etree.ElementTree as ET
import pandas as pd
import os

class ExtratorLattes:
    def __init__(self, pasta_xmls='dadosLattes/'):
        self.pasta_xmls = pasta_xmls
        # Cria a pasta se ela não existir
        if not os.path.exists(self.pasta_xmls):
            os.makedirs(self.pasta_xmls)

    def analisar_curriculo_xml(self, caminho_arquivo):
        print(f"📄 Analisando XML: {os.path.basename(caminho_arquivo)}")
        try:
            tree = ET.parse(caminho_arquivo)
            root = tree.getroot()
            
            # Dicionário com valores padrão para evitar planilha vazia
            dados = {
                'Nome_Pesquisador': 'Não Informado',
                'Instituicao_Atual': 'Não Informado',
                'Total_Artigos_Publicados': 0,
                'Total_Eventos_Participados': 0
            }
            
            # 1. Busca o Nome
            dados_gerais = root.find('DADOS-GERAIS')
            if dados_gerais is not None:
                dados['Nome_Pesquisador'] = dados_gerais.get('NOME-COMPLETO', 'Não Informado')
            
            # 2. Busca a Instituição (usando .// para buscar em qualquer nível)
            atuacoes = root.findall('.//ATUACAO-PROFISSIONAL')
            if atuacoes:
                insts = [a.get('NOME-INSTITUICAO', '') for a in atuacoes]
                # Pega apenas nomes válidos e remove duplicatas
                dados['Instituicao_Atual'] = " | ".join(filter(None, set(insts)))
            
            # 3. Conta as Publicações (Artigos)
            artigos = root.findall('.//ARTIGO-PUBLICADO')
            dados['Total_Artigos_Publicados'] = len(artigos)
            
            # 4. Conta os Eventos (Congressos e Simpósios)
            congressos = root.findall('.//PARTICIPACAO-EM-CONGRESSO')
            simposios = root.findall('.//PARTICIPACAO-EM-SIMPOSIO')
            dados['Total_Eventos_Participados'] = len(congressos) + len(simposios)
            
            return dados
            
        except Exception as e:
            print(f"❌ Erro ao processar {caminho_arquivo}: {e}")
            return None

    def processar_todos(self):
        print("\n--- INICIANDO EXTRAÇÃO DO LATTES ---")
        resultados = []
        
        for arquivo in os.listdir(self.pasta_xmls):
            if arquivo.endswith('.xml'):
                caminho = os.path.join(self.pasta_xmls, arquivo)
                dados = self.analisar_curriculo_xml(caminho)
                if dados:
                    resultados.append(dados)
        
        if resultados:
            df = pd.DataFrame(resultados)
            caminho_csv = os.path.join(self.pasta_xmls, 'base_lattes_consolidada.csv')
            df.to_csv(caminho_csv, index=False)
            print(f"✅ Sucesso! Planilha gerada em '{caminho_csv}' com {len(df)} currículos.")
            return df
        else:
            print("⚠️ Nenhum dado foi extraído.")
            return pd.DataFrame()