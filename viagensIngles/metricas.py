import pandas as pd
import os

class MetricsCalculator:
    """
    Centralized class for mathematical calculations and PIBIC model business rules.
    Implements indicator equations (ED, DF, IB) and scoring.
    """
    def __init__(self, year):
        self.year = year
        
        # Official IPCA (IBGE) Accumulated to bring everything to Present Value (2025 BRL)
        self.correction_factors = {
            2011: 2.2221, 2012: 2.0864, 2013: 1.9713, 2014: 1.8613,
            2015: 1.7492, 2016: 1.5805, 2017: 1.4870, 2018: 1.4444,
            2019: 1.3922, 2020: 1.3347, 2021: 1.2770, 2022: 1.1602,
            2023: 1.0967, 2024: 1.0483, 2025: 1.0000
        }

    def prepare_numeric_data(self, df):
        """Prepares and cleans raw data."""
        clean_df = df.copy()
        
        if 'Período - Data de início' in clean_df.columns:
            clean_df['Travel_Date'] = pd.to_datetime(clean_df['Período - Data de início'], format='%d/%m/%Y', errors='coerce')
            clean_df.dropna(subset=['Travel_Date'], inplace=True)
            clean_df['Month_Num'] = clean_df['Travel_Date'].dt.month
            clean_df['Month_Year'] = clean_df['Month_Num'].apply(lambda x: f"{self.year}-{x:02d}")

        numeric_columns = ['Distance (GCD)', 'Emissions (KgCO2eq)', 'Valor passagens']
        for col in numeric_columns:
            if col in clean_df.columns:
                clean_df[col] = pd.to_numeric(clean_df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
                
        return clean_df

    def calculate_monthly_summary(self, df):
        """Generates dataframe grouped by month for charts and spreadsheets."""
        df = self.prepare_numeric_data(df)
        if df.empty: return pd.DataFrame()

        # APPLIES INFLATION TO MONTHLY EXPENSES FOR PRESENT VALUE (2025)
        year_factor = self.correction_factors.get(self.year, 1.0)
        df['Valor passagens'] = df['Valor passagens'] * year_factor

        grouped_df = df.groupby(['Month_Year', 'Month_Num']).agg(
            Total_Distance_Km = ('Distance (GCD)', 'sum'),
            Total_Emissions_KgCO2eq = ('Emissions (KgCO2eq)', 'sum'),
            Total_Travels = ('Identificador do processo de viagem', 'count'),
            Total_Tickets = ('Valor passagens', 'sum')
        ).reset_index()

        months_template = pd.DataFrame({'Month_Num': range(1, 13)})
        months_template['Month_Year'] = months_template['Month_Num'].apply(lambda x: f"{self.year}-{x:02d}")
        
        monthly_df = pd.merge(months_template, grouped_df, on=['Month_Num', 'Month_Year'], how='left')
        monthly_df = monthly_df.infer_objects(copy=False).fillna(0)
        monthly_df['Total_Travels'] = monthly_df['Total_Travels'].astype(int)
        
        return monthly_df

    def calculate_dynamic_baseline(self, org: str, processing_years: list):
        """Calculates baseline with IPCA correction reading directly from Master."""
        if len(processing_years) < 2: return None
        baseline_years = processing_years[:2]
        
        total_spent, total_emissions, total_distance = 0, 0, 0
        years_found = 0

        for base_year in baseline_years:
            csv_path = os.path.join("travelData", f"travel_data{base_year}", f"df_master_{org}_air_{base_year}.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, low_memory=False)
                df = self.prepare_numeric_data(df)
                
                year_factor = self.correction_factors.get(base_year, 1.0)
                spent_sum = df['Valor passagens'].sum() * year_factor
                
                total_spent += spent_sum
                total_emissions += df['Emissions (KgCO2eq)'].sum()
                total_distance += df['Distance (GCD)'].sum()
                years_found += 1

        if years_found == 0: return None

        return {
            'Years_Used': baseline_years,
            'Average_Annual_Spent': total_spent / years_found,
            'Average_Annual_Emissions': total_emissions / years_found,
            'Average_Annual_Distance': total_distance / years_found
        }

    def calculate_indicators_and_scores(self, raw_df, baseline):
        """Maps PIBIC Methodology formulas (Levels 4 and 5) and assigns S score (Level 3)."""
        df = self.prepare_numeric_data(raw_df)
        total_travels = len(df)
        
        if total_travels == 0: return {}

        ed1_1_total_emissions = df['Emissions (KgCO2eq)'].sum()
        ed2_1_total_distance = df['Distance (GCD)'].sum()
        
        very_short_travels = len(df[df['Distance (GCD)'] < 600])
        short_travels = len(df[(df['Distance (GCD)'] >= 600) & (df['Distance (GCD)'] <= 3700)])
        long_travels = len(df[df['Distance (GCD)'] > 3700])

        df1_4_avoidable_rate = 0.0
        df1_5_urgent_rate = 0.0

        if 'Período - Data de fim' in df.columns:
            df['End_Date'] = pd.to_datetime(df['Período - Data de fim'], format='%d/%m/%Y', errors='coerce')
            df['Duration_Days'] = (df['End_Date'] - df['Travel_Date']).dt.days
            travels_0_1_day = len(df[df['Duration_Days'] <= 1])
            df1_4_avoidable_rate = travels_0_1_day / total_travels if total_travels > 0 else 0

        urgency_column = [col for col in df.columns if 'urgência' in col.lower() or 'urgente' in col.lower()]
        if urgency_column:
            urgent_count = len(df[df[urgency_column[0]].astype(str).str.upper().isin(['SIM', 'S', 'TRUE'])])
            df1_5_urgent_rate = urgent_count / total_travels if total_travels > 0 else 0

        scores = {}

        if baseline and baseline['Average_Annual_Emissions'] > 0:
            if ed1_1_total_emissions < baseline['Average_Annual_Emissions']: scores['ED1.1_Score'] = 1.0 
            elif ed1_1_total_emissions < (baseline['Average_Annual_Emissions'] * 1.1): scores['ED1.1_Score'] = 0.5 
            else: scores['ED1.1_Score'] = 0.0 
        else: scores['ED1.1_Score'] = 0.5 

        if baseline and baseline['Average_Annual_Distance'] > 0:
            scores['ED2.1_Score'] = 1.0 if ed2_1_total_distance < baseline['Average_Annual_Distance'] else 0.5
        else: scores['ED2.1_Score'] = 0.5

        if df1_5_urgent_rate < 0.05: scores['DF1.5_Score'] = 1.0
        elif df1_5_urgent_rate < 0.15: scores['DF1.5_Score'] = 0.5
        else: scores['DF1.5_Score'] = 0.0

        scores['Raw_Indicators'] = {
            'ED1.1_Emissions': ed1_1_total_emissions, 'ED2.1_Distance': ed2_1_total_distance,
            'DF1.4_Avoidable_Rate': df1_4_avoidable_rate, 'DF1.5_Urgent_Rate': df1_5_urgent_rate,
            'ED2.3.1_Short': very_short_travels
        }
        return scores

    def calculate_index_panel(self, score_dict):
        """Consolidates Level 3 scores into Level 2 averages and the General Index (Level 1)."""
        ed1 = score_dict.get('ED1.1_Score', 0.500)
        ed2 = score_dict.get('ED2.1_Score', 0.500)
        ed3 = 0.500  
        
        df1 = score_dict.get('DF1.5_Score', 0.500)
        df2 = 1.000  
        
        ib1, ib2, ib3 = 0.667, 0.000, 0.250  
        
        ed_total = (ed1 + ed2 + ed3) / 3
        df_total = (df1 + df2) / 2
        ib_total = (ib1 + ib2 + ib3) / 3
        
        general_index = (ed_total + df_total + ib_total) / 3
        
        return {
            'N3': {'ED1': ed1, 'ED2': ed2, 'ED3': ed3, 'DF1': df1, 'DF2': df2, 'IB1': ib1, 'IB2': ib2, 'IB3': ib3},
            'N2': {'ED': ed_total, 'DF': df_total, 'IB': ib_total},
            'N1': {'General': general_index}
        }