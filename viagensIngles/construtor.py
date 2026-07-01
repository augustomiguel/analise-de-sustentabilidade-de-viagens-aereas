# travels/construtor.py
import pandas as pd
import os

class MasterBuilder:
    """Exclusively responsible for classifying affiliations and saving the final file."""
    def __init__(self, year):
        self.year = year
        self.output_folder = f'travelData/travel_data{self.year}'
        self.master_out_file = os.path.join(self.output_folder, f'df_master_ALL_air_{self.year}.csv')

    def _classify_affiliation(self, row):
        role = row.get('Cargo')
        reason = row.get('Motivo')
        
        role_str = str(role).upper().strip() if pd.notna(role) else ""
        reason_str = str(reason).upper().strip() if pd.notna(reason) else ""
        
        if role_str in ['NAN', 'SEM INFORMAÇÃO', '']:
            role_str = None
            
        if role_str and any(k in role_str for k in ['PROFESSOR', 'DOCENTE', 'MAGISTERIO', 'VISITANTE', 'REGENTE']):
            return 'Professor'

        if role_str and any(k in role_str for k in ['ESTUDANTE', 'DISCENTE', 'ALUNO', 'ACADEMICO', 'MESTRANDO', 'DOUTORANDO', 'BOLSISTA', 'ESTAGIARIO', 'POS-GRADUACAO']):
            return 'Academic'

        if role_str and any(k in role_str for k in ['COLABORADOR', 'CONVIDADO', 'EXTERNO', 'CONSULTOR']):
            return 'External'

        if reason_str:
            if any(k in reason_str for k in ['ESTUDANTE', 'DISCENTE', 'ALUNO', 'ACADEMICO', 'MESTRANDO', 'DOUTORANDO', 'BOLSISTA', 'APRESENTAÇÃO DE TRABALHO']):
                 return 'Academic'
            
            if any(k in reason_str for k in ['CONVIDADO', 'COLABORADOR', 'PALESTRANTE', 'EXTERNO', 'MEMBRO EXTERNO', 'BANCA EXAMINADORA']):
                 return 'External'

        if role_str:
             return 'Public Servant'

        return 'Not Informed'

    def execute(self, df_aggregated_travels, travel_df, ticket_df):
        print("🔄 Process 4: Building Master File (ALL)...")
        unique_travel_df = travel_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        unique_ticket_df = ticket_df.drop_duplicates(subset=["Identificador do processo de viagem"], keep='first')
        
        travel_columns = [col for col in unique_travel_df.columns if col not in ['Origem - Cidade', 'Destino - Cidade']]
        ticket_columns = [col for col in unique_ticket_df.columns if col != "Identificador do processo de viagem"]

        df_master = pd.merge(df_aggregated_travels, unique_travel_df[travel_columns], on="Identificador do processo de viagem", how='left')
        df_master = pd.merge(df_master, unique_ticket_df[ticket_columns + ["Identificador do processo de viagem"]], on="Identificador do processo de viagem", how='left', suffixes=('', '_PASSAGEM'))
        
        df_master['Distance (GCD)'] = df_master['Distance (GCD)'].round().astype(int)
        df_master['Emissions (KgCO2eq)'] = df_master['Emissions (KgCO2eq)'].round().astype(int)
        
        print("   - Classifying affiliations (Professor / Public Servant / Academic / External)...")
        df_master['Affiliation'] = df_master.apply(self._classify_affiliation, axis=1)
        
        print("   -> Affiliation Count:")
        print(df_master['Affiliation'].value_counts())
        
        # Saves the master file
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            
        df_master.to_csv(self.master_out_file, index=False)
        print(f"   - ✅ Process Completed: Master file saved at '{self.master_out_file}'")
        
        return df_master