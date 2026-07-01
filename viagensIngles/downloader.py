# downloader.py
import os
import requests
import zipfile
import pandas as pd
import re # Imports regex

class TravelDownloader:
    def __init__(self, year: int):
        self.year = year
        self.base_data_folder = "travelData"
        self.zip_file_name = os.path.join(self.base_data_folder, f"viagens_{self.year}.zip")
        self.csv_dest_folder = os.path.join(self.base_data_folder, f"travel_data{self.year}")
        os.makedirs(self.csv_dest_folder, exist_ok=True)
        
        print(f"TravelDownloader: Ready for year {self.year}.")
        print(f"  -> CSV Folder: {self.csv_dest_folder}")

    def _download_csv(self):
        url = f"https://portaldatransparencia.gov.br/download-de-dados/viagens/{self.year}"
        print(f"🔄 Downloading from: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            csv_url = response.url # Final URL after redirect
            
            print(f"➡️ Redirected to: {csv_url}")
            content = requests.get(csv_url)
            content.raise_for_status()

            with open(self.zip_file_name, "wb") as f:
                f.write(content.content)
            print(f"✅ Download saved at: {self.zip_file_name}")
            return True
        except Exception as e:
            print(f"❌ Download error for year {self.year}: {e}")
            return False

    def _unzip_file(self):
        print(f"🔄 Unzipping '{self.zip_file_name}'...")
        try:
            with zipfile.ZipFile(self.zip_file_name, 'r') as zip_ref:
                zip_ref.extractall(self.csv_dest_folder)
            print(f"✅ Files extracted to: {self.csv_dest_folder}")
            
            # Cleanup .zip and Payment CSV
            os.remove(self.zip_file_name)
            print(f"   - .zip file removed.")
            
            payment_file = os.path.join(self.csv_dest_folder, f"{self.year}_Pagamento.csv")
            if os.path.exists(payment_file):
                os.remove(payment_file)
                print(f"   - Payment file removed.")
            return True
        except Exception as e:
            print(f"❌ Error while unzipping or cleaning up: {e}")
            return False

    def _normalize_whitespace(self, text):
        """Aggressively cleans the text, removing hidden spaces."""
        if isinstance(text, str):
            # Replaces multiple spaces (including \n, \t, \xa0) with a single space
            text = re.sub(r'\s+', ' ', text, flags=re.UNICODE)
            return text.strip()
        return text

    def _normalize_columns(self, df, var_name):
        """
        Checks for known column names and renames them to an internal standard.
        """
        
        # *** AGGRESSIVE CLEANING STEP ***
        df.columns = [self._normalize_whitespace(col) for col in df.columns]
        
        # *** LOGIC MOVED FOR 'travel_df' ***
        if var_name == "travel_df":
            # Key: Internal standard name
            # Value: List of possible names (UPPERCASE AND CLEANED)
            column_map = {
                'Nome órgão solicitante': ['NOME ÓRGÃO SOLICITANTE', 'ÓRGÃO SOLICITANTE'],
            }
            
            renamed_columns = {}
            standard_column_found = False

            # Iterates over CURRENT DataFrame columns
            for current_col in df.columns:
                clean_upper_col = current_col.upper() # Compares in uppercase
                
                for standard_name, possible_upper_names in column_map.items():
                    if clean_upper_col in possible_upper_names:
                        if current_col != standard_name: # If needs renaming
                            renamed_columns[current_col] = standard_name
                        standard_column_found = True # Marks as found
                        break # Stops inner loop
            
            if renamed_columns:
                df = df.rename(columns=renamed_columns)
                print(f"      -> Normalized columns: {renamed_columns}")

            # Final verification
            if not standard_column_found:
                print(f"      -> ⚠️ WARNING: Column 'Nome órgão solicitante' not found in {var_name}.")
                print(f"         Current columns: {list(df.columns)}")
                raise KeyError(f"Failed to normalize column 'Nome órgão solicitante' in {var_name}.")
        
        # Mapping for 'segment_df'
        if var_name == "segment_df":
            if "Identificador do processo de viagem " in df.columns:
                df = df.rename(columns={"Identificador do processo de viagem ": "Identificador do processo de viagem"})
        
        return df

    def load_csvs(self):
        """Loads essential CSVs into DataFrames."""
        print(f"🔄 Loading CSVs to DataFrames for year {self.year}...")
        file_names = {
            "ticket_df": f"{self.year}_Passagem.csv",
            "segment_df": f"{self.year}_Trecho.csv",
            "travel_df": f"{self.year}_Viagem.csv"
        }
        results = {}
        
        for var_name, file_name in file_names.items():
            full_path = os.path.join(self.csv_dest_folder, file_name)
            try:
                raw_df = pd.read_csv(full_path, sep=";", encoding="latin1", header=None, low_memory=False)
                # Cleans HEADER before assigning
                raw_df.columns = [self._normalize_whitespace(col) for col in raw_df.iloc[0]]
                df = raw_df.drop(index=0).reset_index(drop=True)
                
                # *** NORMALIZATION STEP ***
                df = self._normalize_columns(df, var_name)
                    
                results[var_name] = df
                print(f"✅ {file_name} loaded ({len(df)} rows).")
            except FileNotFoundError:
                print(f"❌ File not found: {full_path}. Run 'fetch_raw_data()' first.")
                return None, None, None
            except Exception as e:
                print(f"❌ Error loading {file_name}: {e}")
                return None, None, None
        
        return results.get("travel_df"), results.get("ticket_df"), results.get("segment_df")


    def fetch_raw_data(self):
        """Main method: Downloads, unzips, and loads the data."""
        if not self._download_csv():
            return None, None, None
        if not self._unzip_file():
            return None, None, None
        return self.load_csvs()