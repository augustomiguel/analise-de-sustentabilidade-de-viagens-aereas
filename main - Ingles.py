# main.py
import time
from viagensIngles.downloader import TravelDownloader
from viagensIngles.geocoder import GeoCacheManager
from viagensIngles.processor import TravelProcessor
from viagensIngles.reporting import ReportGenerator
from viagensIngles.filtro import Filter

# --- GLOBAL CONFIGURATION ---
YEARS_TO_PROCESS = [2023, 2024, 2025]
ORGS_TO_PROCESS = ['UFPB', 'UFCG']

# Defines how many years at the START of the list will be used ONLY to calculate the baseline
QTY_BASELINE_YEARS = 1

# --- EXECUTION CONTROL (Where you decide what runs) ---
RUN_HEAVY_PROCESSING = True  
RUN_FINAL_EXCEL_GENERATION = True    

# --- DOWNLOADER CONFIGURATIONS ---
DOWNLOAD_NEW_DATA = False 

# ==============================================================================
# HELPER FUNCTIONS (INDIVIDUAL STEPS)
# ==============================================================================
def step_fetch_data(year):
    print(f"--- 1. FETCHING RAW DATA FOR {year} ---")
    downloader = TravelDownloader(year=year)
    if DOWNLOAD_NEW_DATA: return downloader.fetch_raw_data()
    else: return downloader.load_csvs()

def step_process_general(year, raw_data, geocoder):
    print(f"\n--- 2. PROCESSING MASTER FILE 'ALL' FOR {year} ---")
    travel_df, ticket_df, segment_df = raw_data
    processor = TravelProcessor(year=year, geocoder=geocoder)
    processor.load_data(travel_df, ticket_df, segment_df)
    processor.process_all() 

def step_filter_and_report(year, org, is_baseline):
    print(f"\n--- 3. FILTERING AND REPORTING FOR: {org} / {year} ---")
    
    # The filter ALWAYS needs to run, as the Baseline reads the organ's df_master for these years
    filter_obj = Filter(year=year)
    filter_obj.filter_and_save(org)
    
    # IF IT'S A BASELINE YEAR, STOPS HERE AND DOESN'T GENERATE CHARTS
    if is_baseline:
        print(f"   -> ⏭️ Year {year} reserved for Baseline. Skipping Dashboards and PDFs generation.")
        return
        
    reporter = ReportGenerator(year=year)
    dynamic_baseline = reporter.calculate_dynamic_baseline(org, YEARS_TO_PROCESS)
    
    reporter.generate_monthly_report(org=org)
    reporter.generate_metrics_report(org=org, baseline=dynamic_baseline)
    reporter.generate_consolidated_dashboard(org=org, baseline=dynamic_baseline)
    reporter.generate_index_panel(org=org, baseline=dynamic_baseline)
    reporter.merge_pdfs_into_one(org=org)

# ==============================================================================
# MAIN EXECUTION BLOCKS
# ==============================================================================

def execute_annual_flow():
    """Executes the complete annual download, processing, and reporting flow."""
    print("\n🚀 STARTING COMPLETE ANNUAL PROCESSING FLOW...")
    
    print("--- INITIALIZING GEOCODER (CACHE MANAGER) ---")
    geocoder = GeoCacheManager(user_agent="MySustainabilityProject/1.0")

    # Identifies which are the baseline years (e.g., 2011 and 2012)
    baseline_years = YEARS_TO_PROCESS[:QTY_BASELINE_YEARS]

    for year in YEARS_TO_PROCESS:
        print(f"\n{'='*30} STARTING YEAR: {year} {'='*30}")
        
        # Step 1: Fetch Data
        raw_data = step_fetch_data(year)
        
        # Step 2: Process Master (Necessary to find distance and emissions)
        if raw_data:
            step_process_general(year, raw_data, geocoder)
        else:
            print(f"❌ Skipped year {year} due to lack of data.")
            continue

        is_baseline = (year in baseline_years)

        # Step 3: Reports per Institution
        for org in ORGS_TO_PROCESS:
            step_filter_and_report(year, org, is_baseline)


def execute_excel_consolidation():
    """Generates only the final consolidated Excel spreadsheet with all real research years."""
    print(f"\n{'='*30} GENERATING CONSOLIDATED EXCEL MATRICES {'='*30}")
    
    # Excludes baseline years from the Excel table!
    report_years = YEARS_TO_PROCESS[QTY_BASELINE_YEARS:]

    
    if not report_years:
        print("⚠️ Not enough years to generate reports beyond the baseline.")
        return
        
    final_reporter = ReportGenerator(year=report_years) 
    
    for org in ORGS_TO_PROCESS:
        final_reporter.generate_excel_matrix(org=org, selected_years=report_years)

# ==============================================================================
# MAIN (ENTRY POINT)
# ==============================================================================

def main():
    start_time = time.time()

    if RUN_HEAVY_PROCESSING:
        execute_annual_flow()
    else:
        print("⏭️  SKIP: Heavy processing disabled.")

    if RUN_FINAL_EXCEL_GENERATION:
        execute_excel_consolidation()
    else:
        print("⏭️  SKIP: Excel generation disabled.")

    end_time = time.time()
    print(f"\n{'='*50}")
    print(f"✅ END OF SCRIPT!")
    print(f"   Total time: {end_time - start_time:.2f} seconds.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()