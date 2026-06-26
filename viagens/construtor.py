# viagens/construtor.py
import pandas as pd
import os

class ConstrutorMestre:
    """Responsável exclusivo por classificar os vínculos e salvar o arquivo final."""
    def __init__(self, ano):
        self.ano = ano
        self.pasta_saida = f'dadosViagens/dados_viagens{self.ano}'
        self.arquivo_master_out = os.path.join(self.pasta_saida, f'df_master_ALL_aereo_{self.ano}.csv')

    def _classificar_vinculo(self, row):
        cargo = row.get('Cargo')
        motivo = row.get('Motivo')
        
        cargo_str = str(cargo).upper().strip() if pd.notna(cargo) else ""
        motivo_str = str(motivo).upper().strip() if pd.notna(motivo) else ""
        
        if cargo_str in ['NAN', 'SEM INFORMAÇÃO', '']:
            cargo_str = None
            
        if cargo_str and any(k in cargo_str for k in ['PROFESSOR', 'DOCENTE', 'MAGISTERIO', 'VISITANTE', 'REGENTE']):
            return 'Professor'

        if cargo_str and any(k in cargo_str for k in ['ESTUDANTE', 'DISCENTE', 'ALUNO', 'ACADEMICO', 'MESTRANDO', 'DOUTORANDO', 'BOLSISTA', 'ESTAGIARIO', 'POS-GRADUACAO']):
            return 'Acadêmico'

        if cargo_str and any(k in cargo_str for k in ['COLABORADOR', 'CONVIDADO', 'EXTERNO', 'CONSULTOR']):
            return 'Externo'

        if motivo_str:
            if any(k in motivo_str for k in ['ESTUDANTE', 'DISCENTE', 'ALUNO', 'ACADEMICO', 'MESTRANDO', 'DOUTORANDO', 'BOLSISTA', 'APRESENTAÇÃO DE TRABALHO']):
                 return 'Acadêmico'
            
            if any(k in motivo_str for k in ['CONVIDADO', 'COLABORADOR', 'PALESTRANTE', 'EXTERNO', 'MEMBRO EXTERNO', 'BANCA EXAMINADORA']):
                 return 'Externo'

        if cargo_str:
             return 'Servidor'

        return 'Não Informado'

    def executar(self, df_viagens_agregadas, viagem_df, passagem_df):
        print("🔄 Processo 4: Construindo Arquivo Mestre (ALL)...")
        viagem_df_unique = viagem_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        passagem_df_unique = passagem_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        
        colunas_viagem = [col for col in viagem_df_unique.columns if col not in ['Origem - Cidade', 'Destino - Cidade']]
        colunas_passagem = [col for col in passagem_df_unique.columns if col != "Identificador do processo de viagem"]

        df_master = pd.merge(df_viagens_agregadas, viagem_df_unique[colunas_viagem], on="Identificador do processo de viagem", how='left')
        df_master = pd.merge(df_master, passagem_df_unique[colunas_passagem + ["Identificador do processo de viagem"]], on="Identificador do processo de viagem", how='left', suffixes=('', '_PASSAGEM'))
        
        df_master['Distância (GCD)'] = df_master['Distância (GCD)'].round().astype(int)
        df_master['Emissões (KgCO2eq)'] = df_master['Emissões (KgCO2eq)'].round().astype(int)
        
        print("   - Classificando vínculos (Professor / Servidor / Acadêmico / Externo)...")
        df_master['Vínculo'] = df_master.apply(self._classificar_vinculo, axis=1)
        
        print("   -> Contagem de Vínculos:")
        print(df_master['Vínculo'].value_counts())
        
        # Salva o arquivo mestre
        if not os.path.exists(self.pasta_saida):
            os.makedirs(self.pasta_saida)
            
        df_master.to_csv(self.arquivo_master_out, index=False)
        print(f"   - ✅ Processo Concluído: Arquivo mestre salvo em '{self.arquivo_master_out}'")
        
        return df_master