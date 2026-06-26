# viagens/processor.py
import pandas as pd
from .geocoder import GeoCacheManager 

# Importando os especialistas que acabamos de separar
from .limpador import LimpadorDados
from .distancias import GerenciadorDistancias
from .emissoes import CalculadoraEmissoes
from .construtor import ConstrutorMestre

class ViagemProcessor:
    """
    Classe Orquestradora (Facade). Não faz cálculos, apenas coordena a execução 
    das classes especialistas que estão separadas em seus próprios arquivos.
    """
    def __init__(self, ano: int, geocoder: GeoCacheManager):
        self.ano = ano
        self.geocoder = geocoder
        
        # Inicializa a equipe de especialistas
        self.limpador = LimpadorDados()
        self.gerenciador_distancias = GerenciadorDistancias(geocoder)
        self.calculadora_emissoes = CalculadoraEmissoes()
        self.construtor = ConstrutorMestre(ano)
        
        # Variáveis de estado
        self.viagem_df = None
        self.passagem_df = None
        self.trecho_df = None
        
        print(f"ViagemProcessor: Pronto para processar o ano {self.ano} (TODAS as instituições)")

    def load_data(self, viagem_df, passagem_df, trecho_df):
        self.viagem_df = viagem_df.copy()
        self.passagem_df = passagem_df.copy()
        self.trecho_df = trecho_df.copy()
        print("  -> Dados brutos carregados no processador.")

    def process_all(self):
        if self.viagem_df is None: return

        # Passo 1: Limpeza e Merge (vai chamar o limpador.py)
        v_df, p_df, t_df = self.limpador.executar(self.viagem_df, self.passagem_df, self.trecho_df)

        # Trata o caso de não haver trechos válidos após limpeza
        if t_df.empty:
            df_vazio = pd.DataFrame(columns=['Identificador do processo de viagem', 'Vínculo'])
            df_vazio.to_csv(self.construtor.arquivo_master_out, index=False)
            print("⚠️ Arquivo Mestre vazio salvo (nenhum trecho aéreo válido).")
            return

        # Passo 2: Distâncias (vai chamar o distancias.py)
        t_df_com_dist = self.gerenciador_distancias.executar(t_df)

        # Passo 3: Pegada de Carbono (vai chamar o emissoes.py)
        df_agregadas = self.calculadora_emissoes.executar(t_df_com_dist)

        # Passo 4: Classificação e Salvamento (vai chamar o construtor.py)
        df_final = self.construtor.executar(df_agregadas, v_df, p_df)

        return df_final