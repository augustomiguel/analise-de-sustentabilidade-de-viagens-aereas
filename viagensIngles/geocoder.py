# travels/geocoder.py
import requests
import math
import pandas as pd
import numpy as np
import time
import os

class GeoCacheManager:
    # Path for main API cache (saved at project root)
    CACHE_API_FILE = 'api_coordinates_cache.csv'
    
    # Path for missing cities log (Errors/Typos)
    MISSING_LOG_FILE = 'cities_not_found.csv'
    
    # Path for local database (Excel)
    LOCAL_COORDINATES_FILE = "../documentosWalleci/CodTrechos.xlsx"
    LOCAL_SHEET_NAME = "ID_Cidades"
    
    WAIT_TIME = 1.1 
    BATCH_CHECKPOINT = 50 

    def __init__(self, user_agent='SustainabilityApp/1.0'):
        self.user_agent = user_agent
        self.coordinates_map = None
        self.not_found_cities = set()
        
        # Load caches into memory
        self._load_not_found_cities()
        self._load_coordinates_map()

    def _load_not_found_cities(self):
        """Loads the list of cities the API already failed to find to save time."""
        if os.path.exists(self.MISSING_LOG_FILE):
            try:
                df_missing = pd.read_csv(self.MISSING_LOG_FILE, encoding='utf-8')
                if 'City' in df_missing.columns:
                    self.not_found_cities = set(df_missing['City'].astype(str).str.strip())
                    print(f"   -> Failure Cache loaded: {len(self.not_found_cities)} ignored cities.", flush=True)
            except Exception as e:
                print(f"   ❌ Error reading failure log: {e}")
        else:
            self.not_found_cities = set()

    def _register_failure(self, city):
        """Saves the city to the missing log for the user to fix later."""
        self.not_found_cities.add(city)
        file_exists = os.path.exists(self.MISSING_LOG_FILE)
        try:
            with open(self.MISSING_LOG_FILE, 'a', encoding='utf-8') as f:
                if not file_exists:
                    f.write("City\n") # Writes header if file is new
                f.write(f'"{city}"\n')
        except Exception as e:
            print(f"   ❌ Error writing to failure log: {e}")

    def _load_local_db(self):
        """Loads the coordinates database from the Excel file (ID_Cidades)."""
        try:
            df_local = pd.read_excel(
                self.LOCAL_COORDINATES_FILE, 
                sheet_name=self.LOCAL_SHEET_NAME
            )
            df_local = df_local.rename(columns={
                'nome': 'City', 'LATITUDE': 'Latitude', 'LONGITUDE': 'Longitude'
            })
            df_local = df_local[['City', 'Latitude', 'Longitude']].copy()
            df_local['City'] = df_local['City'].astype(str).str.strip()
            return df_local
        except FileNotFoundError:
            print("   - Warning: Local database Excel file not found. Using API cache only.")
            return pd.DataFrame(columns=['City', 'Latitude', 'Longitude'])
        except Exception as e:
            print(f"   - ❌ Error loading local database (sheet '{self.LOCAL_SHEET_NAME}'): {e}", flush=True)
            return pd.DataFrame(columns=['City', 'Latitude', 'Longitude'])

    def _load_api_cache(self):
        """Loads the API coordinate cache tolerantly to errors."""
        if not os.path.exists(self.CACHE_API_FILE) or os.stat(self.CACHE_API_FILE).st_size == 0:
            return pd.DataFrame(columns=['City', 'Latitude', 'Longitude'])
        
        try:
            df_cache = pd.read_csv(self.CACHE_API_FILE, encoding='latin1', on_bad_lines='warn', engine='python')
            if df_cache.empty or 'City' not in df_cache.columns:
                return pd.DataFrame(columns=['City', 'Latitude', 'Longitude'])
                
            df_cache['City'] = df_cache['City'].astype(str).str.strip()
            print(f"   -> API Cache successfully loaded: {len(df_cache)} entries.", flush=True)
            return df_cache
            
        except Exception as e:
            print(f"   ❌ FATAL ERROR reading API cache '{self.CACHE_API_FILE}': {e}. Suggestion: Delete the file.", flush=True)
            return pd.DataFrame(columns=['City', 'Latitude', 'Longitude'])

    def _load_coordinates_map(self):
        """Loads the complete coordinates map (PRIMARY API Cache + SECONDARY Local DB)."""
        df_api_cache = self._load_api_cache()
        df_local = self._load_local_db()
        
        dfs_to_concat = [df for df in [df_api_cache, df_local] if not df.empty]

        if dfs_to_concat:
            self.coordinates_map = pd.concat(dfs_to_concat, ignore_index=True)
        else:
            self.coordinates_map = pd.DataFrame(columns=['City', 'Latitude', 'Longitude'])

        self.coordinates_map = self.coordinates_map.drop_duplicates(subset=['City'], keep='first')
        print(f"✅ GeoCacheManager: Coordinates map initialized with {len(self.coordinates_map)} valid cities.", flush=True)

    def _get_api_coordinates(self, location):
        """Private method to get location coordinates via API."""
        try:
            url = f"https://nominatim.openstreetmap.org/search?format=json&q={location}&limit=1"
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=5) 
            response.raise_for_status()
            data = response.json()
            if data:
                result = data[0]
                return {
                    'City': location,
                    'Latitude': float(result['lat']),
                    'Longitude': float(result['lon'])
                }
            return None
        except Exception:
            return None

    def get_coordinates(self, cities_list: list):
        """
        Ensures all cities in the list have coordinates.
        Queries the API only if the city is not in cache AND not in the failure log.
        """
        cities_list = [str(c).strip() for c in cities_list if pd.notna(c)]
        unique_cities_df = pd.DataFrame(np.unique(cities_list), columns=['City'])

        # Cities we already have coordinates for
        df_known = pd.merge(
            unique_cities_df,
            self.coordinates_map,
            on='City',
            how='inner'
        )
        
        known_cities = set(df_known['City'])
        
        # Filter cities: No coordinates AND Haven't tried and failed before
        cities_for_geocoding = [
            c for c in unique_cities_df['City'] 
            if c not in known_cities and c not in self.not_found_cities
        ]
        
        if not cities_for_geocoding:
            print("   -> Geocoding: All cities are already in cache or marked as failed.", flush=True)
            return df_known

        missing_count = len(cities_for_geocoding)
        print(f"\n   -> 🔄 API Geocoding: {missing_count} unknown cities. Starting query ({self.WAIT_TIME}s/req).", flush=True)
        
        api_results = []
        header_needs_to_be_written = not os.path.exists(self.CACHE_API_FILE) or os.stat(self.CACHE_API_FILE).st_size == 0
        
        for i, city in enumerate(cities_for_geocoding):
            
            if i % 10 == 0 or i == 0:
                print(f"      -> Processing: {i}/{missing_count}. City: {city}", flush=True)
            
            coord = self._get_api_coordinates(city)

            if coord:
                api_results.append(coord)
            else:
                # IF API FAILED, ADD TO FAILURE LOG FOR LATER CORRECTION
                self._register_failure(city)
                print(f"      ⚠️ Not found: {city} (Saved to failure log)")
                
            # Checkpoint: Save in batches to avoid losing everything on error
            if (i + 1) % self.BATCH_CHECKPOINT == 0 or (i + 1) == missing_count:
                if api_results:
                    df_new_coords_batch = pd.DataFrame(api_results)
                    df_new_coords_batch.to_csv(
                        self.CACHE_API_FILE, 
                        index=False, 
                        mode='a', 
                        header=header_needs_to_be_written,
                        encoding='latin1'
                    )
                    header_needs_to_be_written = False # Only writes header once
                    print(f"      >>> CHECKPOINT SAVED: {len(api_results)} new valid cities in cache.", flush=True)
                    
                    # Adds to in-memory coordinates map
                    self.coordinates_map = pd.concat([self.coordinates_map, df_new_coords_batch], ignore_index=True)
                    self.coordinates_map.drop_duplicates(subset=['City'], keep='last', inplace=True)
                    api_results = [] 
            
            time.sleep(self.WAIT_TIME)
        
        print(f"   -> ✅ API Geocoding completed.", flush=True)
        
        # Returns the full DataFrame
        df_final_coords = pd.merge(
            unique_cities_df,
            self.coordinates_map,
            on='City',
            how='left'
        )
        return df_final_coords

    @staticmethod
    def calculate_haversine(lat1, lon1, lat2, lon2):
        """Calculates the Haversine Distance (GCD) using a vectorized method (NumPy)."""
        R = 6371.0 # Earth's radius in km
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distance_km = R * c
        return distance_km