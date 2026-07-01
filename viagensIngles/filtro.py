# classes/filtro.py
import pandas as pd
import os

class Filter:
    """
    This class loads the master 'ALL' file and filters it
    to create specific master files per institution.
    """
    
    def __init__(self, year: int):
        self.year = year
        self.year_data_folder = f'travelData/travel_data{self.year}'
        self.master_all_file = os.path.join(self.year_data_folder, f'df_master_ALL_air_{self.year}.csv')
        self.df_all = self._load_master_all_file()

    def _load_master_all_file(self):
        """Loads the master file containing all institutions."""
        print(f"🔄 Filter: Loading master file '{self.master_all_file}'...")
        try:
            # low_memory=False to avoid mixed type warnings
            df = pd.read_csv(self.master_all_file, low_memory=False) 
            print("   - ✅ Master (ALL) loaded.")
            return df
        except FileNotFoundError:
            print(f"   - ❌ ERROR: Master file (ALL) not found. Run 'processor.process_all()' first.")
            return pd.DataFrame()
        except Exception as e:
            print(f"   - ❌ ERROR loading master (ALL): {e}")
            return pd.DataFrame()

    def _get_filter_str(self, org_short_name: str) -> str:
        """Returns the regex string to filter the institution."""
        if org_short_name == 'UFPB':
            return 'UFPB|UNIVERSIDADE FEDERAL DA PARAIBA|UNIVERSIDADE FEDERAL DA PARAÍBA'
        elif org_short_name == 'UFCG':
            return 'UFCG|UNIVERSIDADE FEDERAL DE CAMPINA GRANDE'
        else:
            # Fallback for other names
            return org_short_name

    def filter_and_save(self, org_short_name: str):
        """Filters the master DataFrame for an institution and saves the result."""
        if self.df_all.empty:
            print(f"   - ⚠️ Filter skipped for {org_short_name} (Master 'ALL' is empty).")
            return
            
        print(f"🔄 Filtering data for: {org_short_name}...")
        
        filter_str = self._get_filter_str(org_short_name)
        
        # Filters using the 'Nome órgão solicitante' column
        filtered_df = self.df_all[
            self.df_all['Nome órgão solicitante'].astype(str).str.upper().str.contains(filter_str, na=False)
        ].copy()
        
        # Defines the output path
        output_file = os.path.join(self.year_data_folder, f'df_master_{org_short_name}_air_{self.year}.csv')
        
        # Saves the institution-specific CSV file
        filtered_df.to_csv(output_file, index=False)
        
        print(f"   - ✅ Filtered file saved: '{output_file}' ({len(filtered_df)} rows)")