#!/usr/bin/env python3
"""
Script to analyze the Uniswap V3 Pool Analysis Excel file
"""
import pandas as pd
import json
import sys

def analyze_excel(filename):
    """Analyze the Excel file and extract all information"""
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(filename)

        results = {
            'sheets': excel_file.sheet_names,
            'sheet_data': {}
        }

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(filename, sheet_name=sheet_name)

            results['sheet_data'][sheet_name] = {
                'shape': df.shape,
                'columns': df.columns.tolist(),
                'first_10_rows': df.head(10).to_dict(orient='records'),
                'data_types': df.dtypes.astype(str).to_dict(),
                'non_null_counts': df.count().to_dict(),
                'basic_stats': {}
            }

            # Get basic statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                stats = df[numeric_cols].describe().to_dict()
                results['sheet_data'][sheet_name]['basic_stats'] = stats

        return results
    except Exception as e:
        return {'error': str(e), 'traceback': str(sys.exc_info())}

if __name__ == '__main__':
    filename = 'STAIKINGII.xlsx'
    results = analyze_excel(filename)

    # Save results to JSON for easier reading
    with open('excel_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
