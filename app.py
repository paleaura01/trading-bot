import os
import time
from datetime import datetime
import pandas as pd
import numpy as np
import dash
from dash import html, dcc, callback, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
from dotenv import load_dotenv

from scripts.utils import (
    fetch_historical_prices,
    fetch_fear_greed,
    fetch_tradeogre_ticker,
    fetch_tradeogre_orderbook,
    prepare_price_data,
    prepare_fg_data
)
from scripts.backtest import run_backtest, get_live_trade_signal, execute_live_trade

# Load environment variables
load_dotenv()
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 1800))  # Default to 30 minutes

# Initialize app with custom styling
app = dash.Dash(
    __name__,
    title="Trading Bot Dashboard",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# Define colors
colors = {
    'background': '#f8f9fa',
    'card': '#ffffff',
    'text': '#212529',
    'accent': '#4361ee',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'neutral': '#3498db'
}

# Fetch initial data on startup
price_data = fetch_historical_prices(force_refresh=True)
fg_data = fetch_fear_greed(force_refresh=True)
backtest_results = run_backtest()

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Poppins', sans-serif;
                background-color: #f8f9fa;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            .card {
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 20px;
                margin-bottom: 20px;
                transition: transform 0.2s;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .header {
                background-color: #4361ee;
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .tabs {
                margin-bottom: 20px;
            }
            .tab-content {
                padding: 20px 0;
            }
            .btn {
                background-color: #4361ee;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            .btn:hover {
                background-color: #3a56d4;
            }
            .btn:disabled {
                background-color: #a0a0a0;
                cursor: not-allowed;
            }
            .btn-success {
                background-color: #2ecc71;
            }
            .btn-success:hover {
                background-color: #27ae60;
            }
            .btn-danger {
                background-color: #e74c3c;
            }
            .btn-danger:hover {
                background-color: #c0392b;
            }
            .form-group {
                margin-bottom: 15px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
            }
            .form-group input {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .trade-log {
                height: 300px;
                overflow-y: auto;
            }
            .trade-log table {
                width: 100%;
                border-collapse: collapse;
            }
            .trade-log th, .trade-log td {
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            .trade-log th {
                background-color: #f1f1f1;
                position: sticky;
                top: 0;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }
            @media (max-width: 1200px) {
                .dashboard-grid {
                    grid-template-columns: 1fr;
                }
            }
            .market-data {
                display: flex;
                justify-content: space-between;
                flex-wrap: wrap;
            }
            .market-data-item {
                background-color: #f1f1f1;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
                flex: 1;
                min-width: 150px;
                text-align: center;
            }
            .market-data-item h4 {
                margin: 0;
                font-size: 1.2rem;
            }
            .market-data-item p {
                margin: 5px 0 0;
                font-size: 0.9rem;
            }
            .left-panel, .right-panel {
                display: flex;
                flex-direction: column;
            }
            .signal-output {
                margin: 15px 0;
                padding: 15px;
                border-radius: 5px;
                background-color: #f1f1f1;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout with tabs for better organization
app.layout = html.Div(className="container", children=[
    # Header with title and last updated
    html.Div(className="header", children=[
        html.H1("Crypto Trading Bot", style={'margin': 0}),
        html.Div(id="last-updated")
    ]),
    
    # Main content with tabs
    dcc.Tabs(id="tabs", value="dashboard-tab", className="tabs", children=[
        # Dashboard Tab
        dcc.Tab(label="Dashboard", value="dashboard-tab", children=[
            html.Div(className="tab-content", children=[
                # Top row with F&G Gauge and Market Data
                html.Div(className="dashboard-grid", children=[
                    # Left panel - Fear & Greed Gauge
                    html.Div(className="card", children=[
                        html.H3("Fear & Greed Index", style={'textAlign': 'center', 'marginTop': 0}),
                        dcc.Graph(id="fg-gauge", config={'displayModeBar': False}, style={'height': '250px'})
                    ]),
                    
                    # Right panel - Live Market Data
                    html.Div(className="card", children=[
                        html.H3("Market Status", style={'textAlign': 'center', 'marginTop': 0}),
                        html.Div(id="live-market-data")
                    ])
                ]),
                
                # Middle row with Price and Portfolio charts
                html.Div(className="dashboard-grid", children=[
                    # Price Chart
                    html.Div(className="card", children=[
                        html.H3("BTC Price History", style={'textAlign': 'center', 'marginTop': 0}),
                        dcc.Graph(id="price-chart")
                    ]),
                    
                    # Portfolio Chart
                    html.Div(className="card", children=[
                        html.H3("Portfolio Performance", style={'textAlign': 'center', 'marginTop': 0}),
                        dcc.Graph(id="portfolio-chart")
                    ])
                ]),
                
                # Bottom row with Trade Log
                html.Div(className="card", children=[
                    html.H3("Recent Trades", style={'textAlign': 'center', 'marginTop': 0}),
                    html.Div(id="trade-log-table", className="trade-log")
                ])
            ])
        ]),
        
        # Strategy Tab
        dcc.Tab(label="Strategy & Controls", value="strategy-tab", children=[
            html.Div(className="tab-content", children=[
                html.Div(className="dashboard-grid", children=[
                    # Backtest Controls
                    html.Div(className="card", children=[
                        html.H3("Backtest Configuration", style={'textAlign': 'center', 'marginTop': 0}),
                        html.Div(className="form-group", children=[
                            html.Label("Initial USDC:"),
                            dcc.Input(id="input-usdc", type="number", value=100, min=1, step=1)
                        ]),
                        html.Div(className="form-group", children=[
                            html.Label("Initial BTC:"),
                            dcc.Input(id="input-btc", type="number", value=0.0011, min=0.0001, step=0.0001)
                        ]),
                        html.Div(className="form-group", children=[
                            html.Label("Fear Threshold (<):"),
                            dcc.Input(id="input-fear", type="number", value=40, min=0, max=100, step=1)
                        ]),
                        html.Div(className="form-group", children=[
                            html.Label("Greed Threshold (>):"),
                            dcc.Input(id="input-greed", type="number", value=60, min=0, max=100, step=1)
                        ]),
                        html.Button("Run Backtest", id="btn-backtest", n_clicks=0, className="btn")
                    ]),
                    
                    # Live Trading Controls
                    html.Div(className="card", children=[
                        html.H3("Live Trading", style={'textAlign': 'center', 'marginTop': 0}),
                        html.Div(className="form-group", children=[
                            html.Label("Current USDC Balance:"),
                            dcc.Input(id="live-usdc", type="number", value=100, min=0, step=1)
                        ]),
                        html.Div(className="form-group", children=[
                            html.Label("Current BTC Balance:"),
                            dcc.Input(id="live-btc", type="number", value=0.0011, min=0, step=0.0001)
                        ]),
                        html.Button("Check Trade Signal", id="btn-check-signal", n_clicks=0, className="btn"),
                        html.Div(id="trade-signal-output", className="signal-output"),
                        html.Div(style={'display': 'flex', 'justifyContent': 'center'}, children=[
                            html.Button("Execute Trade", id="btn-execute", n_clicks=0, disabled=True, 
                                      className="btn btn-success", style={'marginTop': '10px'})
                        ]),
                        html.Div(id="trade-execution-output", style={'marginTop': '15px'})
                    ])
                ])
            ])
        ])
    ]),
    
    # Auto-update interval
    dcc.Interval(
        id='interval-component',
        interval=UPDATE_INTERVAL * 1000,  # milliseconds
        n_intervals=0
    ),
    
    # Store backtest results in browser
    dcc.Store(id='backtest-store')
])

# Callbacks
@callback(
    Output('last-updated', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_time(n):
    """Update the last updated timestamp."""
    return html.Div([
        html.P(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
    ])

@callback(
    Output('backtest-store', 'data'),
    Input('btn-backtest', 'n_clicks'),
    State('input-usdc', 'value'),
    State('input-btc', 'value'),
    State('input-fear', 'value'),
    State('input-greed', 'value'),
    prevent_initial_call=True
)
def update_backtest(n_clicks, usdc, btc, fear, greed):
    """Run backtest with user-defined parameters and store results."""
    if n_clicks > 0:
        results = run_backtest(
            start_usdc=usdc,
            start_btc=btc,
            fg_fear=fear,
            fg_greed=greed
        )
        return results.to_dict('records')
    return []

@callback(
    Output('fg-gauge', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_fg_gauge(n):
    """Update Fear & Greed gauge with latest data."""
    fg_data = fetch_fear_greed()
    latest = fg_data['data'][0]
    value = int(latest['value'])
    classification = latest['value_classification']
    
    # Create gauge figure
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': classification, 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 20], 'color': "firebrick"},
                {'range': [20, 40], 'color': "orange"},
                {'range': [40, 60], 'color': "lightgray"},
                {'range': [60, 80], 'color': "lightgreen"},
                {'range': [80, 100], 'color': "green"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        margin={"t": 30, "b": 0, "l": 30, "r": 30},
        height=250,
        paper_bgcolor="white",
        font={'size': 16}
    )
    return fig

@callback(
    Output('price-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_price_chart(n):
    """Update BTC price chart with latest data."""
    price_data = fetch_historical_prices()
    df = prepare_price_data(price_data)
    
    # Use last 90 days for clearer visualization
    df = df.tail(90).copy()
    
    fig = px.line(
        df, 
        x='date', 
        y='price', 
        labels={'price': 'Price (USD)', 'date': 'Date'}
    )
    
    fig.update_layout(
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(230,230,230,0.8)'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified'
    )
    
    fig.update_traces(line=dict(width=3, color=colors['accent']))
    
    return fig

@callback(
    Output('portfolio-chart', 'figure'),
    Input('backtest-store', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_portfolio_chart(backtest_data, n):
    """Update portfolio value chart based on backtest results."""
    if not backtest_data:
        # Use default backtest results if none provided
        results = run_backtest()
    else:
        results = pd.DataFrame(backtest_data)
    
    # Create figure
    fig = px.line(
        results, 
        x='date', 
        y='portfolio_value',
        labels={'portfolio_value': 'Value (USD)', 'date': 'Date'}
    )
    
    # Add markers for trades
    for action, color in [('BUY', colors['success']), ('SELL', colors['danger']), ('RESET', colors['neutral'])]:
        action_df = results[results['action'] == action]
        if not action_df.empty:
            fig.add_scatter(
                x=action_df['date'],
                y=action_df['portfolio_value'],
                mode='markers',
                marker=dict(size=10, color=color, symbol='circle'),
                name=action,
                hovertemplate=
                '<b>%{text}</b><br>' +
                'Date: %{x}<br>' +
                'Value: $%{y:.2f}<extra></extra>',
                text=[action] * len(action_df)
            )
    
    fig.update_layout(
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(230,230,230,0.8)'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified'
    )
    
    fig.update_traces(selector=dict(type='scatter', mode='lines'), line=dict(width=3, color=colors['accent']))
    
    return fig

@callback(
    Output('trade-log-table', 'children'),
    Input('backtest-store', 'data')
)
def update_trade_log(backtest_data):
    """Update trade log table with backtest results."""
    if not backtest_data:
        # Use default backtest results if none provided
        results = run_backtest()
    else:
        results = pd.DataFrame(backtest_data)
    
    # Filter for trades only (exclude HOLDs)
    results = results[results['action'] != 'HOLD']
    
    # Sort by date descending
    results = results.sort_values('date', ascending=False)
    
    # Create table
    table_header = [
        html.Thead(html.Tr([
            html.Th("Date"),
            html.Th("Action"),
            html.Th("Price"),
            html.Th("F&G"),
            html.Th("USDC After"),
            html.Th("BTC After"),
            html.Th("Portfolio Value")
        ]))
    ]
    
    rows = []
    for i, row in results.iterrows():
        # Style based on action
        style = {}
        if row['action'] == 'BUY':
            style = {'backgroundColor': 'rgba(46, 204, 113, 0.1)'}
        elif row['action'] == 'SELL':
            style = {'backgroundColor': 'rgba(231, 76, 60, 0.1)'}
        elif row['action'] == 'RESET':
            style = {'backgroundColor': 'rgba(52, 152, 219, 0.1)'}
        
        date_str = row['date'].split('T')[0] if isinstance(row['date'], str) else row['date'].strftime('%Y-%m-%d')
        
        rows.append(html.Tr([
            html.Td(date_str),
            html.Td(row['action'], style={'fontWeight': 'bold'}),
            html.Td(f"${row['price']:.2f}"),
            html.Td(f"{row['fg_value']} ({row['fg_class']})"),
            html.Td(f"${row['usdc_after']:.2f}"),
            html.Td(f"{row['btc_after']:.6f}"),
            html.Td(f"${row['portfolio_value']:.2f}")
        ], style=style))
    
    table_body = [html.Tbody(rows)]
    
    return html.Table(table_header + table_body)

@callback(
    Output('live-market-data', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_market_data(n):
    """Update live market data display."""
    ticker = fetch_tradeogre_ticker()
    fg_data = fetch_fear_greed(limit=1)
    
    if not ticker.get('success', True):
        return html.Div("Error fetching market data", style={'color': colors['danger']})
    
    current_price = float(ticker.get('price', 0))
    volume = ticker.get('volume', 'N/A')
    high = ticker.get('high', 'N/A')
    low = ticker.get('low', 'N/A')
    
    fg_value = fg_data['data'][0]['value']
    fg_class = fg_data['data'][0]['value_classification']
    
    return html.Div(className="market-data", children=[
        html.Div(className="market-data-item", children=[
            html.H4("BTC/USDC"),
            html.P(f"${current_price:.2f}", style={'fontSize': '1.5rem', 'fontWeight': 'bold'})
        ]),
        html.Div(className="market-data-item", children=[
            html.H4("24h Volume"),
            html.P(volume)
        ]),
        html.Div(className="market-data-item", children=[
            html.H4("24h High"),
            html.P(high)
        ]),
        html.Div(className="market-data-item", children=[
            html.H4("24h Low"),
            html.P(low)
        ]),
        html.Div(className="market-data-item", children=[
            html.H4("Fear & Greed"),
            html.P(f"{fg_value} ({fg_class})")
        ])
    ])

@callback(
    Output('trade-signal-output', 'children'),
    Output('btn-execute', 'disabled'),
    Input('btn-check-signal', 'n_clicks'),
    State('live-usdc', 'value'),
    State('live-btc', 'value'),
    State('input-fear', 'value'),
    State('input-greed', 'value'),
    prevent_initial_call=True
)
def check_trade_signal(n_clicks, usdc, btc, fear, greed):
    """Check for a trade signal based on current market conditions."""
    if n_clicks == 0:
        raise PreventUpdate
    
    # Get latest Fear & Greed value
    fg_data = fetch_fear_greed(limit=1)
    fg_value = int(fg_data['data'][0]['value'])
    
    # Get signal
    action, amount = get_live_trade_signal(fg_value, usdc, btc, fear, greed)
    
    background_color = {
        'BUY': 'rgba(46, 204, 113, 0.2)',
        'SELL': 'rgba(231, 76, 60, 0.2)',
        'RESET': 'rgba(52, 152, 219, 0.2)',
        'HOLD': 'rgba(189, 195, 199, 0.2)'
    }.get(action, 'rgba(189, 195, 199, 0.2)')
    
    if action == "HOLD":
        return html.Div([
            html.H4("Current Signal: HOLD", style={'textAlign': 'center', 'color': colors['text']}),
            html.P(f"Fear & Greed Index: {fg_value}", style={'textAlign': 'center'}),
            html.P("No action needed at this time", style={'textAlign': 'center'})
        ], style={'backgroundColor': background_color, 'padding': '15px', 'borderRadius': '5px'}), True
    elif action == "BUY":
        ticker = fetch_tradeogre_ticker()
        current_price = float(ticker.get('price', 0))
        estimated_btc = amount / current_price if current_price > 0 else 0
        
        return html.Div([
            html.H4("Current Signal: BUY", style={'textAlign': 'center', 'color': colors['success']}),
            html.P(f"Fear & Greed Index: {fg_value}", style={'textAlign': 'center'}),
            html.P(f"Action: Buy ${amount:.2f} worth of BTC", style={'textAlign': 'center', 'fontWeight': 'bold'}),
            html.P(f"Est. BTC: {estimated_btc:.6f} @ ${current_price:.2f}", style={'textAlign': 'center'})
        ], style={'backgroundColor': background_color, 'padding': '15px', 'borderRadius': '5px'}), False
    elif action == "SELL":
        ticker = fetch_tradeogre_ticker()
        current_price = float(ticker.get('price', 0))
        estimated_usdc = amount * current_price
        
        return html.Div([
            html.H4("Current Signal: SELL", style={'textAlign': 'center', 'color': colors['danger']}),
            html.P(f"Fear & Greed Index: {fg_value}", style={'textAlign': 'center'}),
            html.P(f"Action: Sell {amount:.6f} BTC", style={'textAlign': 'center', 'fontWeight': 'bold'}),
            html.P(f"Est. USDC: ${estimated_usdc:.2f} @ ${current_price:.2f}", style={'textAlign': 'center'})
        ], style={'backgroundColor': background_color, 'padding': '15px', 'borderRadius': '5px'}), False
    elif action == "RESET":
        return html.Div([
            html.H4("Current Signal: RESET", style={'textAlign': 'center', 'color': colors['neutral']}),
            html.P(f"Fear & Greed Index: {fg_value}", style={'textAlign': 'center'}),
            html.P("Reset portfolio to baseline values", style={'textAlign': 'center', 'fontWeight': 'bold'}),
            html.P("USDC: $200, BTC: 0.0022", style={'textAlign': 'center'})
        ], style={'backgroundColor': background_color, 'padding': '15px', 'borderRadius': '5px'}), False

@callback(
    Output('trade-execution-output', 'children'),
    Input('btn-execute', 'n_clicks'),
    State('trade-signal-output', 'children'),
    State('live-usdc', 'value'),
    State('live-btc', 'value'),
    prevent_initial_call=True
)
def execute_trade(n_clicks, signal_output, usdc, btc):
    """Execute a trade based on the current signal."""
    if n_clicks == 0:
        raise PreventUpdate
    
    # Get latest Fear & Greed value
    fg_data = fetch_fear_greed(limit=1)
    fg_value = int(fg_data['data'][0]['value'])
    
    # Get signal
    action, amount = get_live_trade_signal(fg_value, usdc, btc)
    
    # Execute trade (simulated for now)
    result = execute_live_trade(action, amount)
    
    if result['success']:
        if result.get('simulated', False):
            background_color = {
                'BUY': 'rgba(46, 204, 113, 0.2)',
                'SELL': 'rgba(231, 76, 60, 0.2)',
                'RESET': 'rgba(52, 152, 219, 0.2)',
            }.get(action, 'rgba(189, 195, 199, 0.2)')
            
            return html.Div([
                html.H4("SIMULATION MODE", style={'textAlign': 'center', 'color': colors['warning']}),
                html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-between'}, children=[
                    html.Div(className="market-data-item", style={'flexGrow': 1}, children=[
                        html.H4("Action"),
                        html.P(result['action'], style={'fontWeight': 'bold'})
                    ]),
                    html.Div(className="market-data-item", style={'flexGrow': 1}, children=[
                        html.H4("Quantity"),
                        html.P(f"{result['quantity']:.6f}")
                    ]),
                    html.Div(className="market-data-item", style={'flexGrow': 1}, children=[
                        html.H4("Price"),
                        html.P(f"${result['price']:.2f}")
                    ]),
                    html.Div(className="market-data-item", style={'flexGrow': 1}, children=[
                        html.H4("Total"),
                        html.P(f"${result['quantity'] * result['price']:.2f}")
                    ])
                ])
            ], style={'backgroundColor': background_color, 'padding': '15px', 'borderRadius': '5px'})
        else:
            return html.Div([
                html.H4("Trade Executed Successfully!", style={'textAlign': 'center', 'color': colors['success']}),
                html.P(f"Details: {result.get('message', '')}", style={'textAlign': 'center'})
            ], style={'backgroundColor': 'rgba(46, 204, 113, 0.2)', 'padding': '15px', 'borderRadius': '5px'})
    else:
        return html.Div([
            html.H4("Trade Execution Failed", style={'textAlign': 'center', 'color': colors['danger']}),
            html.P(f"Error: {result.get('error', 'Unknown error')}", style={'textAlign': 'center'})
        ], style={'backgroundColor': 'rgba(231, 76, 60, 0.2)', 'padding': '15px', 'borderRadius': '5px'})

# Run the app
if __name__ == '__main__':
    app.run(debug=True)