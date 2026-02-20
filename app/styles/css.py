"""
CSS styles for the CAF.SPACE Web UI.
"""


def get_css_styles():
    """
    Get the CSS styles for the dashboard.
    
    Returns:
        str: CSS styles as string
    """
    return """
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f2f5;
            color: #333;
        }
        
        .header-section {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .summary-container {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }
        
        .summary-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .summary-stats > div:last-child {
            grid-column: 1 / -1;
            margin-top: 20px;
        }
        
        .summary-stats h4 {
            background-color: white;
            padding: 20px 30px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .summary-stats h4:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .dash-graph {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }
        
        .dash-tabs-container {
            margin-top: 20px;
        }
        
        .dash-tab {
            padding: 15px 20px;
            background-color: white;
            border-radius: 8px 8px 0 0;
        }
        
        .dash-tab--selected {
            border-top: 3px solid #119DFF;
        }
        
        /* Custom chart layout classes */
        .chart-row {
            display: grid !important;
            grid-template-columns: 2fr 2fr !important;
            gap: 25px !important;
            margin-bottom: 20px !important;
        }

        .chart-single {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 25px !important;
            margin-bottom: 20px !important;
        }
        
        .chart-container {
            background-color: white !important;
            padding: 20px !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }
        
        .chart-container:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }
        
        /* Responsive design */
        @media (max-width: 1200px) {
            .chart-row {
                grid-template-columns: 1fr !important;
                gap: 20px !important;
            }
        }
        
        table {
            width: 100%;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
        
        tr:last-child td {
            border-bottom: none;
        }
        
        tr:hover {
            background-color: #f5f5f5;
        }
        
        .dash-dropdown {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 8px;
        }
        
        .dash-dropdown:focus {
            border-color: #119DFF;
            outline: none;
            box-shadow: 0 0 0 2px rgba(17, 157, 255, 0.2);
        }
        
        h1, h2, h3 {
            color: #2c3e50;
            margin-bottom: 20px;
        }
        
        h1 {
            font-size: 2.2em;
            font-weight: 600;
        }
        
        h2 {
            font-size: 1.8em;
            font-weight: 500;
        }
        
        h3 {
            font-size: 1.4em;
            font-weight: 500;
            color: #34495e;
        }
        
        /* Date selection styles */
        .date-preset-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 15px;
            justify-content: center;
        }
        
        .date-preset-buttons button {
            transition: all 0.3s ease;
            font-weight: 500;
            background-color: #00dec6 !important;
            color: #0d0f3d !important;
        }
        
        .date-preset-buttons button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        .date-preset-buttons button:active {
            transform: translateY(0);
        }
        
        .year-month-selectors {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            border: 1px solid #dee2e6;
        }
        
        .year-month-selectors > div {
            margin-bottom: 10px;
        }
        
        .year-month-selectors label {
            font-weight: 600;
            color: #495057;
            margin-right: 8px;
        }
        
        .year-month-selectors .Select-control {
            border-radius: 4px;
            border: 1px solid #ced4da;
        }
        
        .year-month-selectors .Select-control:hover {
            border-color: #80bdff;
        }
        
        .year-month-selectors .Select-control.is-focused {
            border-color: #007bff;
            box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
        }
        
        /* All-time summary bar styles */
        .all-time-summary-container {
            background-color: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            padding: 8px 0;
            margin-bottom: 0;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .all-time-summary {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        .all-time-summary span {
            display: inline-block;
            margin-right: 20px;
        }
        
        .all-time-summary span:last-child {
            margin-right: 0;
        }
        
        /* Cumulative metrics container */
        .cumulative-metrics-container {
            background-color: #f8f9fa;
        }
        
        /* Tooltip styles */
        .tooltip {
            position: relative;
            display: inline-block;
        }
        
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 8px 12px;
            position: absolute;
            z-index: 1000;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
            line-height: 1.4;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        
        .tooltip .tooltiptext::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #333 transparent transparent transparent;
        }
        
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        .metric-card {
            cursor: help;
        }
        
        /* Header logo styles */
        .header-content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
        }
        
        .header-logo {
            height: 60px;
            width: auto;
            max-width: 250px;
            object-fit: contain;
        }
        
        .header-title {
            margin: 0;
            font-size: 2.2em;
            font-weight: 600;
            color: #2c3e50;
        }
        
        /* All Time section styles - matching Year-to-Date */
        .all-time-section-container {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin: 20px;
            border: 2px solid #dee2e6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .all-time-metrics {
            display: flex;
            justify-content: center;
            flex-wrap: nowrap;
            gap: 10px;
        }
        
        .all-time-metrics .metric-card {
            text-align: center;
            padding: 12px 8px;
            border-radius: 8px;
            margin: 0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            flex: 1;
            min-width: 100px;
            max-width: 150px;
        }
        
        .all-time-metrics .metric-card h4 {
            font-size: 1.4em !important;
            margin: 0 !important;
        }
        
        .all-time-metrics .metric-card p {
            font-size: 0.9em !important;
            margin: 0 !important;
        }
        
        .all-time-metrics .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
    """


def get_index_string():
    """
    Get the complete HTML index string with embedded styles.
    
    Returns:
        str: Complete HTML index string
    """
    return f'''
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>TfN Offer Analysis</title>
        {{%favicon%}}
        {{%css%}}
        <style>
            {get_css_styles()}
        </style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
'''
