import dash
from dash import html, dcc

# Premium dark theme colors
colors = {
    'background': '#0B1120',  # Darker blue-black
    'card': '#1E293B',        # Card background
    'text': '#F1F5F9',        # Off-white
    'accent': '#38BDF8',      # Sky blue
    'success': '#10B981',     # Emerald green
    'warning': '#F59E0B',     # Amber
    'danger': '#EF4444',      # Red
    'neutral': '#6366F1',     # Indigo
    'card_border': '#334155'  # Slate border
}

def create_layout(update_interval):
    """Creates the main application layout"""
    return html.Div(className="container", children=[
        # Header
        html.Div(className="header", children=[
            html.Div(className="logo", children=[
                html.I(className="fas fa-robot"),
                html.Span("CryptoTrader")
            ]),
            html.Div(className="status", id="connection-status", children=[
                html.I(className="fas fa-circle"),
                html.Span("Connected")
            ])
        ]),
        
        # Main Grid - Top Row
        html.Div(className="grid", children=[
            # Left Side - Vault Value with Chart
            html.Div(className="col-8", children=[
                # Vault Value Card with Graph
                html.Div(className="card", children=[
                    html.Div(className="card-header", children=[
                        html.H2(className="card-title", children=[
                            html.I(className="fas fa-wallet"),
                            html.Span("Vault Value"),
                            html.Div(id="mode-badge", className="test-badge", children=[
                                html.I(className="fas fa-flask"),
                                html.Span("Test Mode")
                            ])
                        ]),
                        html.Div(id="last-updated", style={"fontSize": "0.875rem", "opacity": "0.7"})
                    ]),
                    html.Div(className="card-body", style={"padding": "0.75rem"}, children=[
                        # Value display with both USD and BTC
                        html.Div(id="vault-value", className="card-value"),
                        html.Div(id="vault-value-btc", className="btc-value"),
                        html.Div(className="card-label", children="Total Portfolio Value"),
                        
                        # Performance Metrics
                        html.Div(className="metrics-grid", id="performance-metrics", children=[
                            html.Div(className="metric-item", children=[
                                html.Div(className="metric-value", id="metric-daily-return"),
                                html.Div(className="metric-label", children="Daily Return")
                            ]),
                            html.Div(className="metric-item", children=[
                                html.Div(className="metric-value", id="metric-unrealized-return"),
                                html.Div(className="metric-label", children="Unrealized Return")
                            ]),
                            html.Div(className="metric-item", children=[
                                html.Div(className="metric-value", id="metric-avg-cost"),
                                html.Div(className="metric-label", children="Avg. Cost")
                            ])
                        ]),
                        
                        # Value History Chart
                        html.Div(style={"height": "200px", "marginTop": "0.75rem"}, children=[
                            dcc.Graph(
                                id="portfolio-chart",
                                config={"displayModeBar": False},
                                style={"height": "100%"}
                            )
                        ]),
                        
                        # Market Data Section
                        html.Div(className="market-section", children=[
                            html.Div(className="market-header", children=[
                                html.H3(className="market-title", children=[
                                    html.I(className="fas fa-chart-line"),
                                    html.Span("Market Data")
                                ])
                            ]),
                            html.Div(className="data-grid", id="market-data-grid")
                        ])
                    ])
                ])
            ]),
            
            # Right Side - Main container for Trading Controls and History (side by side)
            html.Div(className="col-4", children=[
                # Horizontal layout container for Trading Controls and Trading History
                html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "0.75rem"}, children=[
                    # Left Column - Trade Account and Trading Controls
                    html.Div(className="card", children=[
                        # Small Trade Account Section
                        html.Div(style={"borderBottom": "1px solid var(--card-border)", "padding": "0.75rem"}, children=[
                            html.H3(className="card-title", style={"fontSize": "1rem", "marginBottom": "0.5rem"}, children=[
                                html.I(className="fas fa-user-cog"),
                                html.Span("Trade Account")
                            ]),
                            html.Div(className="account-info", id="trade-account-info")
                        ]),
                        
                        # Trading Controls Header
                        html.Div(className="card-header", children=[
                            html.H2(className="card-title", children=[
                                html.I(className="fas fa-sliders"),
                                html.Span("Trading Controls")
                            ])
                        ]),
                        
                        # Trading Controls Content
                        html.Div(className="card-body", style={"padding": "0.75rem"}, children=[
                            # Account Information
                            html.Div(className="account-info", id="account-info"),
                            
                            # Test/Live Mode Toggle
                            html.Div(className="toggle-container", children=[
                                dcc.RadioItems(
                                    id="mode-toggle",
                                    options=[
                                        {'label': 'Test Mode', 'value': 'test'},
                                        {'label': 'Live Trading', 'value': 'live'}
                                    ],
                                    value='test',
                                    className="mode-toggle",
                                    labelStyle={'display': 'inline-block'}
                                )
                            ]),
                            
                            # Strategy Type Selection
                            html.Div(className="form-group", style={"marginTop": "1rem"}, children=[
                                html.Label("Strategy Type:"),
                                dcc.RadioItems(
                                    id="strategy-type",
                                    options=[
                                        {'label': 'Fear & Greed Index', 'value': 'fear_greed'},
                                        {'label': 'Dual-Trade Daily', 'value': 'dual_trade'}
                                    ],
                                    value='fear_greed',
                                    labelStyle={'marginRight': '1rem', 'marginBottom': '0.5rem', 'fontSize': '0.9rem'}
                                )
                            ]),
                            
                            # Fear & Greed Strategy Controls
                            html.Div(id="fear-greed-controls", children=[
                                html.Div(className="form-group", children=[
                                    html.Label("Initial USDT:"),
                                    dcc.Input(id="input-usdt", type="number", value=100, min=1, step=1)
                                ]),
                                html.Div(className="form-group", children=[
                                    html.Label("Initial BTC:"),
                                    dcc.Input(id="input-btc", type="number", value=0.0011, min=0.0001, step=0.0001)
                                ]),
                                
                                html.Div(style={"display": "flex", "gap": "0.75rem"}, children=[
                                    html.Div(className="form-group", style={"flex": 1}, children=[
                                        html.Label("Fear Threshold (<):"),
                                        dcc.Input(id="input-fear", type="number", value=40, min=0, max=100, step=1)
                                    ]),
                                    html.Div(className="form-group", style={"flex": 1}, children=[
                                        html.Label("Greed Threshold (>):"),
                                        dcc.Input(id="input-greed", type="number", value=60, min=0, max=100, step=1)
                                    ])
                                ])
                            ]),
                            
                            # Dual-Trade Strategy Controls
                            html.Div(id="dual-trade-controls", style={"display": "none"}, children=[
                                html.Div(className="form-group", children=[
                                    html.Label("Base BTC Holding:"),
                                    dcc.Input(id="input-base-btc", type="number", value=0.001, min=0.0001, step=0.0001)
                                ]),
                                html.Div(className="form-group", children=[
                                    html.Label("USDC Reserve:"),
                                    dcc.Input(id="input-usdc-reserve", type="number", value=100, min=1, step=1)
                                ]),
                                
                                html.Div(style={"display": "flex", "gap": "0.75rem"}, children=[
                                    html.Div(className="form-group", style={"flex": 1}, children=[
                                        html.Label("Buy Discount (%):"),
                                        dcc.Input(id="input-buy-discount", type="number", value=3, min=0.1, max=20, step=0.1)
                                    ]),
                                    html.Div(className="form-group", style={"flex": 1}, children=[
                                        html.Label("Sell Premium (%):"),
                                        dcc.Input(id="input-sell-premium", type="number", value=2, min=0.1, max=20, step=0.1)
                                    ])
                                ]),
                                
                                html.Div(className="form-group", children=[
                                    html.Label("Reinvestment Rate (%):"),
                                    dcc.Input(id="input-reinvest-rate", type="number", value=20, min=0, max=100, step=5)
                                ]),
                                
                                # New FG Thresholds for Dual-Trade
                                html.Div(style={"display": "flex", "gap": "0.75rem", "marginTop": "0.5rem"}, children=[
                                    html.Div(className="form-group", style={"flex": 1}, children=[
                                        html.Label("FG Fear Threshold (<):"),
                                        dcc.Input(id="dual-input-fear", type="number", value=40, min=0, max=100, step=1)
                                    ]),
                                    html.Div(className="form-group", style={"flex": 1}, children=[
                                        html.Label("FG Greed Threshold (>):"),
                                        dcc.Input(id="dual-input-greed", type="number", value=60, min=0, max=100, step=1)
                                    ])
                                ])
                            ]),
                            
                            # Strategy Notes
                            html.Div(id="strategy-notes", className="strategy-section"),
                            
                            # Action Button
                            html.Div(className="btn-group", children=[
                                html.Button(children=[
                                    html.I(className="fas fa-play"),
                                    html.Span("Execute Strategy")
                                ], id="btn-execute", n_clicks=0, className="btn btn-primary")
                            ])
                        ])
                    ]),
                    
                    # Right Column - Trading History
                    html.Div(className="card", children=[
                        html.Div(className="card-header", children=[
                            html.H2(className="card-title", children=[
                                html.I(className="fas fa-history"),
                                html.Span("Trading History")
                            ])
                        ]),
                        html.Div(className="card-body", style={"padding": "0.75rem", "height": "calc(100% - 48px)"}, children=[
                            html.Div(id="trade-log", className="log-container", style={"height": "100%", "overflowY": "auto"})
                        ])
                    ])
                ])
            ])
        ]),
        
        # Hidden storage
        dcc.Store(id="backtest-store"),
        dcc.Store(id="virtual-vault-store"),
        dcc.Store(id="initial-price-store"),
        dcc.Interval(id="interval-component", interval=update_interval*1000, n_intervals=0)
    ])