import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import matplotlib.patches as patches
from PyPDF2 import PdfMerger
from viagens.metricas import MetricsCalculator

class ReportGenerator:
    def __init__(self, year: int):
        self.year = year
        self.data_folder = f'travelData/travel_data{self.year}'
        self.monthly_reports_folder = os.path.join(self.data_folder, 'Monthly_Reports')
        if not os.path.exists(self.monthly_reports_folder): os.makedirs(self.monthly_reports_folder)
        self.calculator = MetricsCalculator(year=self.year)

    def _load_master_file(self, org: str) -> pd.DataFrame:
        path = os.path.join(self.data_folder, f'df_master_{org}_air_{self.year}.csv')
        if os.path.exists(path): return pd.read_csv(path, low_memory=False)
        else: return pd.DataFrame()

    def calculate_dynamic_baseline(self, org: str, processing_years: list):
        return self.calculator.calculate_dynamic_baseline(org, processing_years)

    def generate_monthly_report(self, org: str):
        print(f"🔄 Generating Monthly Report (Matplotlib) for {org}...")
        raw_df = self._load_master_file(org)
        if raw_df.empty: return

        monthly_df = self.calculator.calculate_monthly_summary(raw_df)
        if monthly_df.empty: return
        monthly_df.round(2).to_csv(os.path.join(self.monthly_reports_folder, f"monthly_report_{org}_air_{self.year}.csv"), index=False)

        try:
            fig, ax1 = plt.subplots(figsize=(10, 5))
            ax1.bar(monthly_df['Month_Year'], monthly_df['Total_Tickets'], color='#1f77b4', label='Expenses (BRL)')
            ax1.set_ylabel('Amount Spent (2025 BRL)', color='#1f77b4', fontweight='bold')
            ax1.tick_params(axis='y', labelcolor='#1f77b4')
            ax1.set_xticks(range(len(monthly_df['Month_Year'])))
            ax1.set_xticklabels(monthly_df['Month_Year'], rotation=45, ha='right')
            ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('R$ {x:,.0f}'))

            ax2 = ax1.twinx()
            ax2.plot(monthly_df['Month_Year'], monthly_df['Total_Emissions_KgCO2eq'], color='#d62728', marker='o', linewidth=2, label='Emissions')
            ax2.set_ylabel('Emissions (Kg CO2eq)', color='#d62728', fontweight='bold')
            ax2.tick_params(axis='y', labelcolor='#d62728')
            ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f} kg'))

            plt.title(f'Expenses vs Monthly Carbon Footprint - {org}', fontsize=14, fontweight='bold', pad=15)
            fig.tight_layout()
            fig.savefig(os.path.join(self.monthly_reports_folder, f"monthly_dashboard_{org}_{self.year}.pdf"))
            plt.close(fig)
        except Exception as e: print(f"   - ❌ Error generating charts: {e}")

    def generate_metrics_report(self, org: str, baseline=None):
        df = self._load_master_file(org)
        if df.empty: return
        df.describe().to_csv(os.path.join(self.monthly_reports_folder, f"raw_metrics_report_{org}_{self.year}.csv"))

    def generate_consolidated_dashboard(self, org: str, baseline=None):
        print(f"🔄 Generating Full Consolidated Dashboard (Matplotlib) for {org}...")
        current_df = self._load_master_file(org)
        if current_df.empty: return

        current_df['Emissions (KgCO2eq)'] = pd.to_numeric(current_df['Emissions (KgCO2eq)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        current_df['Valor passagens'] = pd.to_numeric(current_df['Valor passagens'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        current_df['Distance (GCD)'] = pd.to_numeric(current_df['Distance (GCD)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        year_factor = self.calculator.correction_factors.get(self.year, 1.0)

        fig = plt.figure(figsize=(16, 10), constrained_layout=True)
        gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1, 1, 1.2])

        ax_costs = fig.add_subplot(gs[0, 0])
        ax_emissions = fig.add_subplot(gs[0, 1])
        ax_scores = fig.add_subplot(gs[0, 2])
        ax_pie = fig.add_subplot(gs[1, 0])
        ax_cat_dist = fig.add_subplot(gs[1, 1])
        ax_cat_emiss = fig.add_subplot(gs[1, 2])

        baseline_colors = ['#4c78a8', '#f58518']
        
        # APPLYING INFLATION FACTOR ON CURRENT COST
        current_spent = current_df['Valor passagens'].sum() * year_factor
        current_emissions = current_df['Emissions (KgCO2eq)'].sum()
        baseline_spent = baseline['Average_Annual_Spent'] if baseline else 0
        baseline_emissions = baseline['Average_Annual_Emissions'] if baseline else 0

        ax_costs.bar(['Current', 'Baseline'], [current_spent, baseline_spent], color=baseline_colors, edgecolor='black')
        ax_costs.set_title('Cost Comparison (2025 BRL)', fontweight='bold')
        ax_costs.yaxis.set_major_formatter(ticker.StrMethodFormatter('R$ {x:,.0f}'))

        ax_emissions.bar(['Current', 'Baseline'], [current_emissions, baseline_emissions], color=baseline_colors, edgecolor='black')
        ax_emissions.set_title('Emissions Comparison', fontweight='bold')
        ax_emissions.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f} kg'))

        score_dict = self.calculator.calculate_indicators_and_scores(current_df, baseline)
        score_list = [{'Indicator': k.replace('_Score', ''), 'Score': v} for k, v in score_dict.items() if k.endswith('_Score')]
        df_scores = pd.DataFrame(score_list)

        if not df_scores.empty:
            def score_color(val): return '#d62728' if val < 0.35 else '#ffdd57' if val < 0.70 else '#2ca02c'
            ax_scores.bar(df_scores['Indicator'], df_scores['Score'], color=[score_color(v) for v in df_scores['Score']], edgecolor='black')
            ax_scores.set_title('Sustainability Model Scores', fontweight='bold')
            ax_scores.set_ylim(0, 1.1)
            ax_scores.set_xticks(range(len(df_scores['Indicator'])))
            ax_scores.set_xticklabels(df_scores['Indicator'], rotation=45, ha='right')

        if 'Affiliation' in current_df.columns:
            df_affiliation = current_df.groupby('Affiliation')['Emissions (KgCO2eq)'].sum().reset_index()
            df_affiliation = df_affiliation[df_affiliation['Emissions (KgCO2eq)'] > 0]
            if not df_affiliation.empty:
                wedges, texts, autotexts = ax_pie.pie(
                    df_affiliation['Emissions (KgCO2eq)'], autopct='%1.1f%%', startangle=140, pctdistance=0.75, wedgeprops={'edgecolor': 'white'}
                )
                plt.setp(autotexts, size=9, weight="bold")
                ax_pie.set_title('Emissions by Affiliation', fontweight='bold')
                ax_pie.legend(wedges, df_affiliation['Affiliation'], title="Affiliation", loc="center left", bbox_to_anchor=(0.9, 0.5), fontsize=9)

        if 'Distance Category' in current_df.columns:
            df_cat = current_df.groupby('Distance Category').agg({'Distance (GCD)': 'sum', 'Emissions (KgCO2eq)': 'sum'}).reset_index()
            cat_labels = df_cat['Distance Category']
            mapped_colors = [{'Short Distance': '#4c78a8', 'Long Distance': '#f58518', 'Very Short (Avoidable)': '#d62728'}.get(cat, 'gray') for cat in cat_labels]

            ax_cat_dist.bar(cat_labels, df_cat['Distance (GCD)'], color=mapped_colors, edgecolor='black')
            ax_cat_dist.set_title('Distance (Km) by Category', fontweight='bold')
            ax_cat_dist.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
            ax_cat_dist.set_xticks(range(len(cat_labels)))
            ax_cat_dist.set_xticklabels(cat_labels, rotation=45, ha='right') 

            ax_cat_emiss.bar(cat_labels, df_cat['Emissions (KgCO2eq)'], color=mapped_colors, edgecolor='black')
            ax_cat_emiss.set_title('Emissions by Category', fontweight='bold')
            ax_cat_emiss.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
            ax_cat_emiss.set_xticks(range(len(cat_labels)))
            ax_cat_emiss.set_xticklabels(cat_labels, rotation=45, ha='right')

        fig.suptitle(f'Strategic Air Travel Dashboard - {org} ({self.year})', fontsize=18, fontweight='bold')
        fig.savefig(os.path.join(self.monthly_reports_folder, f"full_dashboard_{org}_{self.year}.pdf"), bbox_inches='tight', facecolor='white')
        plt.close(fig)

    def generate_index_panel(self, org: str, baseline=None):
        print(f"🔄 Generating Hierarchical Index Panel for {org}...")
        current_df = self._load_master_file(org)
        if current_df.empty: return
        
        raw_scores = self.calculator.calculate_indicators_and_scores(current_df, baseline)
        indices = self.calculator.calculate_index_panel(raw_scores)

        fig, ax = plt.subplots(figsize=(16, 5))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off') 

        def draw_box(x, y, w, h, title, value, color, text_color='black'):
            rect = patches.Rectangle((x, y), w, h, linewidth=0.5, edgecolor='gray', facecolor=color)
            ax.add_patch(rect)
            ax.text(x + w/2, y + h*0.65, title, ha='center', va='center', fontsize=10, wrap=True, color=text_color)
            ax.text(x + w/2, y + h*0.25, f"{value:.3f}", ha='center', va='center', fontsize=14, fontweight='bold', color=text_color)

        draw_box(0.05, 0.65, 0.30, 0.30, "GENERAL INDEX", indices['N1']['General'], '#ffffff')
        draw_box(0.05, 0.35, 0.30, 0.30, "Emissions, Displacement and Cost", indices['N2']['ED'], '#e2efd9')
        draw_box(0.36, 0.35, 0.30, 0.30, "Motivations for flight", indices['N2']['DF'], '#ddebf7')
        draw_box(0.67, 0.35, 0.30, 0.30, "Institutional Barriers", indices['N2']['IB'], '#fff2cc')
        draw_box(0.05, 0.10, 0.10, 0.25, "Emissions\nAnalysis", indices['N3']['ED1'], '#e2efd9')
        draw_box(0.15, 0.10, 0.10, 0.25, "Displacement\nAnalysis", indices['N3']['ED2'], '#e2efd9')
        draw_box(0.25, 0.10, 0.10, 0.25, "Costs\nAnalysis", indices['N3']['ED3'], '#a8d08d')
        draw_box(0.36, 0.10, 0.15, 0.25, "Hypermobility\nIncentive", indices['N3']['DF1'], '#ddebf7')
        draw_box(0.51, 0.10, 0.15, 0.25, "Flight\nPurposes", indices['N3']['DF2'], '#ddebf7')
        draw_box(0.67, 0.10, 0.10, 0.25, "Restrictions", indices['N3']['IB1'], '#fff2cc')
        draw_box(0.77, 0.10, 0.10, 0.25, "Incentive", indices['N3']['IB2'], '#ffe699')
        draw_box(0.87, 0.10, 0.10, 0.25, "Organizational\nChange", indices['N3']['IB3'], '#bf8f00', text_color='white')

        plt.suptitle(f"Integrated Report - {org} {self.year}", x=0.05, y=0.95, ha='left', fontsize=16, fontweight='bold')
        ax.text(0.5, 0.95, "Index Panel", ha='center', va='center', fontsize=16, fontweight='bold')

        fig.savefig(os.path.join(self.monthly_reports_folder, f"index_panel_{org}_{self.year}.pdf"), bbox_inches='tight')
        plt.close(fig)

    def merge_pdfs_into_one(self, org: str):
        panel_path = os.path.join(self.monthly_reports_folder, f"index_panel_{org}_{self.year}.pdf")
        monthly_path = os.path.join(self.monthly_reports_folder, f"monthly_dashboard_{org}_{self.year}.pdf")
        full_path = os.path.join(self.monthly_reports_folder, f"full_dashboard_{org}_{self.year}.pdf")
        final_path = os.path.join(self.monthly_reports_folder, f"Official_Report_{org}_{self.year}.pdf")

        try:
            merger = PdfMerger()
            if os.path.exists(panel_path): merger.append(panel_path)
            if os.path.exists(monthly_path): merger.append(monthly_path)
            if os.path.exists(full_path): merger.append(full_path)
            merger.write(final_path)
            merger.close()
        except Exception as e: print(f"   - ❌ Error merging PDFs: {e}")

    def generate_excel_matrix(self, org: str, selected_years: list):
        print(f"   📊 Generating Consolidated Excel Matrix for {org} (in Tonnes)...")
        # 1. We changed the metric name to make it clear it's Tonnes
        metrics = ['Distance', 'Spent', 'Emissions (t)']
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        multi_columns = pd.MultiIndex.from_product([selected_years, metrics], names=['Year', 'Metric'])
        final_df = pd.DataFrame(index=month_names, columns=multi_columns)
        
        for year in selected_years:
            file_path = os.path.join("travelData", f"travel_data{year}", "Monthly_Reports", f"monthly_report_{org}_air_{year}.csv")
            if os.path.exists(file_path):
                source_df = pd.read_csv(file_path)
                
                # 2. Mapping
                cols_map = {'Total_Distance_Km': 'Distance', 'Total_Tickets': 'Spent', 'Total_Emissions_KgCO2eq': 'Emissions (t)'}
                
                for _, row in source_df.iterrows():
                    month_idx = int(row['Month_Num']) - 1
                    if 0 <= month_idx < 12:
                        for csv_col, excel_col in cols_map.items():
                            val = float(str(row[csv_col]).replace(',', '.'))
                            
                            # 3. divide by 1000!
                            if csv_col == 'Total_Emissions_KgCO2eq':
                                val = val / 1000
                                
                            final_df.loc[month_names[month_idx], (year, excel_col)] = val

        final_df = final_df.infer_objects(copy=False).fillna(0)
        final_df.loc['Annual'] = final_df.sum()
        final_df.loc['Average'] = final_df.iloc[0:12].mean()

        excel_path = os.path.join("travelData", f"full_matrix_{org}.xlsx")
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name='Data', startrow=2)
            # Updated Title
            writer.sheets['Data']['A1'] = f"Air travel displacement data - {org} (Emissions in Tonnes of CO2eq)"
            writer.sheets['Data']['A1'].font = __import__('openpyxl').styles.Font(size=14, bold=True)
        print(f"   ✅ Excel saved at: {os.path.abspath(excel_path)}")