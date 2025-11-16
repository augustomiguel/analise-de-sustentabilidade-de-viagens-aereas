# classes/filtro.py
import pandas as pd
import os

class Filtro:
    """
    Esta classe carrega o arquivo mestre 'ALL' e o filtra
    para criar arquivos mestre específicos por instituição.
    """
    
    def __init__(self, ano: int):
        self.ano = ano
        self.pasta_dados_ano = f'dadosViagens/dados_viagens{self.ano}'
        self.master_all_file = os.path.join(self.pasta_dados_ano, f'df_master_ALL_aereo_{self.ano}.csv')
        self.df_all = self._load_master_all_file()

    def _load_master_all_file(self):
        """Carrega o arquivo mestre que contém todas as instituições."""
        print(f"🔄 Filtro: Carregando arquivo mestre '{self.master_all_file}'...")
        try:
            # low_memory=False para evitar avisos de tipo misto
            df = pd.read_csv(self.master_all_file, low_memory=False) 
            print("   - ✅ Mestre (ALL) carregado.")
            return df
        except FileNotFoundError:
            print(f"   - ❌ ERRO: Arquivo mestre (ALL) não encontrado. Execute o 'processor.process_all()' primeiro.")
            return pd.DataFrame()
        except Exception as e:
            print(f"   - ❌ ERRO ao carregar mestre (ALL): {e}")
            return pd.DataFrame()

    def _get_filtro_str(self, orgao_nome_curto: str) -> str:
        """Retorna a string de regex para filtrar o órgão."""
        if orgao_nome_curto == 'UFPB':
            return 'UFPB|UNIVERSIDADE FEDERAL DA PARAIBA|UNIVERSIDADE FEDERAL DA PARAÍBA'
        elif orgao_nome_curto == 'UFCG':
            return 'UFCG|UNIVERSIDADE FEDERAL DE CAMPINA GRANDE'
        else:
            # Fallback para outros nomes
            return orgao_nome_curto

    def filtrar_e_salvar(self, orgao_nome_curto: str):
        """Filtra o DataFrame mestre para um órgão e salva o resultado."""
        if self.df_all.empty:
            print(f"   - ⚠️ Filtro pulado para {orgao_nome_curto} (Mestre 'ALL' está vazio).")
            return
            
        print(f"🔄 Filtrando dados para: {orgao_nome_curto}...")
        
        filtro_str = self._get_filtro_str(orgao_nome_curto)
        
        # Filtra usando a coluna 'Nome órgão solicitante'
        df_filtrado = self.df_all[
            self.df_all['Nome órgão solicitante'].astype(str).str.upper().str.contains(filtro_str, na=False)
        ].copy()
        
        # Define o caminho de saída
        arquivo_saida = os.path.join(self.pasta_dados_ano, f'df_master_{orgao_nome_curto}_aereo_{self.ano}.csv')
        
        # Salva o arquivo CSV específico do órgão
        df_filtrado.to_csv(arquivo_saida, index=False)
        
        print(f"   - ✅ Arquivo filtrado salvo: '{arquivo_saida}' ({len(df_filtrado)} linhas)")