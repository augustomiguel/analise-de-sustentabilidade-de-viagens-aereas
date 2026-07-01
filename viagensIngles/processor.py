# travels/processor.py
import pandas as pd
from .geocoder import GeoCacheManager 

# Importing the specialists we just separated
from .limpador import DataCleaner
from .distancias import DistanceManager
from .emissoes import EmissionsCalculator
from .construtor import MasterBuilder

class TravelProcessor:
    """
    Orchestrator Class (Facade). Performs no calculations, solely coordinates the execution 
    of specialist classes which are separated into their own files.
    """
    def __init__(self, year: int, geocoder: GeoCacheManager):
        self.year = year
        self.geocoder = geocoder
        
        # Initializes the team of specialists
        self.cleaner = DataCleaner()
        self.distance_manager = DistanceManager(geocoder)
        self.emissions_calculator = EmissionsCalculator()
        self.builder = MasterBuilder(year)
        
        # State variables
        self.travel_df = None
        self.ticket_df = None
        self.segment_df = None
        
        print(f"TravelProcessor: Ready to process year {self.year} (ALL institutions)")

    def load_data(self, travel_df, ticket_df, segment_df):
        self.travel_df = travel_df.copy()
        self.ticket_df = ticket_df.copy()
        self.segment_df = segment_df.copy()
        print("  -> Raw data loaded into processor.")

    def process_all(self):
        if self.travel_df is None: return

        # Step 1: Cleaning and Merge (will call cleaner.py)
        t_df, tk_df, seg_df = self.cleaner.execute(self.travel_df, self.ticket_df, self.segment_df)

        # Handles the case of having no valid segments after cleaning
        if seg_df.empty:
            empty_df = pd.DataFrame(columns=['Identificador do processo de viagem', 'Affiliation'])
            empty_df.to_csv(self.builder.master_out_file, index=False)
            print("⚠️ Empty Master File saved (no valid air segments).")
            return

        # Step 2: Distances (will call distances.py)
        seg_df_with_dist = self.distance_manager.execute(seg_df)

        # Step 3: Carbon Footprint (will call emissions.py)
        aggregated_df = self.emissions_calculator.execute(seg_df_with_dist)

        # Step 4: Classification and Saving (will call builder.py)
        final_df = self.builder.execute(aggregated_df, t_df, tk_df)

        return final_df