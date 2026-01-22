"""
Visualize Lineage for Mirrored Databases and Shortcuts
"""
import os
import sys
import glob
import logging
import argparse
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Add src to path to maintain project structure compatibility
sys.path.insert(0, str(Path(__file__).parents[2]))

def setup_logging():
    """Setup logging configuration."""
    Path("logs").mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            TimedRotatingFileHandler(
                'logs/lineage_visualization.log',
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
        ]
    )
    return logging.getLogger(__name__)

class LineageVisualizer:
    def __init__(self, input_file=None):
        self.logger = setup_logging()
        self.input_file = input_file
        # Base directory for exports
        self.output_dir = Path("exports/lineage")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_input_file(self):
        """Find the latest CSV file in exports/lineage/"""
        if self.input_file:
            if os.path.exists(self.input_file):
                return self.input_file
            else:
                self.logger.error(f"Provided input file does not exist: {self.input_file}")
                sys.exit(1)
        
        # Look for default pattern from extract_lineage.py
        files = glob.glob(str(self.output_dir / "*.csv"))
        if not files:
            self.logger.error(f"No CSV files found in {self.output_dir}. Please run extract_lineage.py first.")
            sys.exit(1)
            
        latest_file = max(files, key=os.path.getctime)
        self.logger.info(f"Using latest lineage file: {latest_file}")
        return latest_file

    def load_data(self, filepath):
        """Load and clean the lineage data."""
        try:
            df = pd.read_csv(filepath)
            self.logger.info(f"Loaded {len(df)} records from {filepath}")
            
            # Ensure required columns exist
            required_cols = ['Workspace Name', 'Item Type', 'Source Type', 'Source Connection']
            for col in required_cols:
                if col not in df.columns:
                    self.logger.warning(f"Column '{col}' missing in dataset. Filling with 'Unknown'.")
                    df[col] = 'Unknown'

            # Handle optional columns or specific data cleaning behavior
            # Example: If 'Shortcut Name' is missing (e.g. older extracts), fill it
            if 'Shortcut Name' not in df.columns:
                df['Shortcut Name'] = 'N/A'

            # Fill any remaining NaNs to ensure charts don't break
            df = df.fillna('Unknown')
            return df
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            sys.exit(1)

    def create_sunburst_chart(self, df):
        """Hierarchy: Workspace Name -> Item Type -> Source Type"""
        try:
            fig = px.sunburst(
                df, 
                path=['Workspace Name', 'Item Type', 'Source Type'],
                title="Lineage Hierarchy: Workspace -> Item -> Source",
                height=700
            )
            return fig
        except Exception as e:
            self.logger.error(f"Failed to create sunburst chart: {e}")
            return None

    def create_bar_chart(self, df):
        """Count of items by Source Connection (Top 20), colored by Source Type"""
        try:
            # Group by Connection and Source Type
            counts = df.groupby(['Source Connection', 'Source Type']).size().reset_index(name='Count')
            
            # Identify Top 20 Connections by total volume
            top_connections = df['Source Connection'].value_counts().nlargest(20).index
            filtered_counts = counts[counts['Source Connection'].isin(top_connections)]
            
            fig = px.bar(
                filtered_counts,
                x='Source Connection',
                y='Count',
                color='Source Type',
                title="Top 20 Source Connections by Usage",
                labels={'Count': 'Number of Artifacts'},
                height=600
            )
            # Ensure the bars are ordered descending by total size
            fig.update_layout(xaxis={'categoryorder':'total descending'})
            return fig
        except Exception as e:
            self.logger.error(f"Failed to create bar chart: {e}")
            return None

    def create_pie_chart(self, df):
        """Distribution of Item Type (MirroredDatabase vs Lakehouse Shortcut, etc.)"""
        try:
            item_counts = df['Item Type'].value_counts().reset_index()
            # Rename columns to handle different pandas versions (reset_index behavior)
            if len(item_counts.columns) == 2:
                item_counts.columns = ['Item Type', 'Count']
            
            fig = px.pie(
                item_counts,
                values='Count',
                names='Item Type',
                title="Distribution of Fabric Item Types",
                height=500
            )
            return fig
        except Exception as e:
            self.logger.error(f"Failed to create pie chart: {e}")
            return None

    def save_report(self, figures, source_file):
        """Save all figures to a single HTML report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"lineage_report_{timestamp}.html"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"""
                <html>
                <head>
                    <title>Fabric Lineage Analysis Report - {timestamp}</title>
                    <style>
                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f4f4; }}
                        .container {{ max-width: 1200px; margin: auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                        h1 {{ color: #0078d4; }}
                        .metadata {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
                        .chart-container {{ margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Fabric Lineage Analysis Report</h1>
                        <div class="metadata">
                            <p><strong>Generated at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                            <p><strong>Source File:</strong> {source_file}</p>
                        </div>
                """)
                
                for fig in figures:
                    if fig:
                        f.write('<div class="chart-container">')
                        # include_plotlyjs='cdn' ensures the file is standalone but lightweight (fetches JS from CDN)
                        f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))
                        f.write('</div>')
                    
                f.write("""
                    </div>
                </body>
                </html>
                """)
                
            self.logger.info(f"Report successfully saved to {output_file}")
            print(f"Success! Report generated at: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save HTML report: {e}")

    def run(self):
        input_path = self.get_latest_input_file()
        df = self.load_data(input_path)
        
        if df.empty:
            self.logger.warning("Dataframe is empty. No charts to generate.")
            return

        self.logger.info("Generating visualizations...")
        figs = []
        
        sunburst = self.create_sunburst_chart(df)
        if sunburst: figs.append(sunburst)
        
        bar = self.create_bar_chart(df)
        if bar: figs.append(bar)
        
        pie = self.create_pie_chart(df)
        if pie: figs.append(pie)
        
        if figs:
            self.save_report(figs, input_path)
        else:
            self.logger.warning("No charts were generated successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize Fabric Lineage Data")
    parser.add_argument("--input", "-i", type=str, help="Path to input CSV file (optional). Defaults to latest in exports/lineage/.")
    args = parser.parse_args()
    
    visualizer = LineageVisualizer(args.input)
    visualizer.run()
