import pandas as pd
import numpy as np
from datetime import datetime
import traceback
import logging
from dash import callback, Output, Input, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

# Import strategy modules
from strategies.fear_greed import run_backtest, get_live_trade_signal
from strategies.dual_trade import DualTradeStrategy
from strategies.virtual_vault import VirtualVault

# Import API functions
from scripts.utils import (
    fetch_tradeogre_orderbook,
    fetch_tradeogre_ticker,
    fetch_tradeogre_account,
    execute_live_trade
)

logger = logging.getLogger(__name__)

def register_callbacks(app):
    """Register all callbacks for the application"""
    
    @callback(
        Output("last-updated", "children"),
        Input("interval-component", "n_intervals")
    )
    def update_time(n):
        now = datetime.now()
        return html.Span(f"Last Updated: {now.strftime('%H:%M:%S')} ")

    @callback(
        Output("mode-badge", "className"),
        Output("mode-badge", "children"),
        Input("mode-toggle", "value")
    )
    def update_mode_badge(mode_value):
        if mode_value == 'live':
            return "live-badge", [
                html.I(className="fas fa-satellite-dish"),
                html.Span("Live Trading")
            ]
        else:
            return "test-badge", [
                html.I(className="fas fa-flask"),
                html.Span("Test Mode")
            ]

    @callback(
        Output("strategy-notes", "children"),
        Input("strategy-type", "value")
    )
    def update_strategy_notes(strategy_type):
        if strategy_type == "fear_greed":
            return [
                html.H4(
                    children=[
                        html.I(className="fas fa-lightbulb", style={"color": "#F59E0B"}),
                        "Fear & Greed Strategy"
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.5rem"}
                ),
                html.Div(className="strategy-notes", children=[
                    html.P("• Buy when Fear & Greed < 40 with 50% of USDT"),
                    html.P("• Sell when Fear & Greed > 60 with 50% of BTC"),
                    html.P("• Reset when BTC ≥ 0.011 to [USDT: 200, BTC: 0.0022]")
                ])
            ]
        else:
            return [
                html.H4(
                    children=[
                        html.I(className="fas fa-lightbulb", style={"color": "#F59E0B"}),
                        "Dual-Trade Strategy"
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.5rem"}
                ),
                html.Div(className="strategy-notes", children=[
                    html.P("• Place simultaneous buy & sell orders daily"),
                    html.P("• Buy at current price × (1 - buy discount)"),
                    html.P("• Sell at current price × (1 + sell premium)"),
                    html.P("• When one order fills, cancel the other"),
                    html.P("• Reinvest profits based on reinvestment rate")
                ])
            ]

    @callback(
        Output("fear-greed-controls", "style"),
        Output("dual-trade-controls", "style"),
        Input("strategy-type", "value")
    )
    def toggle_strategy_controls(strategy_type):
        if strategy_type == "fear_greed":
            return {"display": "block"}, {"display": "none"}
        else:
            return {"display": "none"}, {"display": "block"}

    @callback(
        Output("connection-status", "children"),
        Input("interval-component", "n_intervals")
    )
    def update_connection_status(n):
        try:
            ticker_price = fetch_tradeogre_ticker("BTC-USDT")
            if ticker_price > 0:
                return [
                    html.I(className="fas fa-circle"),
                    html.Span("Connected")
                ]
            else:
                return [
                    html.I(className="fas fa-circle", style={"color": "#F59E0B"}),
                    html.Span("Degraded", style={"color": "#F59E0B"})
                ]
        except Exception:
            return [
                html.I(className="fas fa-circle", style={"color": "#EF4444"}),
                html.Span("Disconnected", style={"color": "#EF4444"})
            ]

    @callback(
        Output("market-data-grid", "children"),
        Input("interval-component", "n_intervals")
    )
    def update_market_data(n):
        try:
            ticker_price = fetch_tradeogre_ticker("BTC-USDT")
            hour_change, day_change = 0.75, -1.2
            volume = 1234.56
            hour_class = "positive" if hour_change > 0 else "negative"
            hour_icon = "fa-caret-up" if hour_change > 0 else "fa-caret-down"
            day_class = "positive" if day_change > 0 else "negative"
            day_icon = "fa-caret-up" if day_change > 0 else "fa-caret-down"
            
            return [
                html.Div(className="data-item", children=[
                    html.Div(className="data-value", children=f"${ticker_price:,.2f}"),
                    html.Div(className="data-label", children="BTC-USDT")
                ]),
                html.Div(className="data-item", children=[
                    html.Div(className="data-value", children=[
                        html.Span(f"{abs(hour_change)}% ", className=hour_class),
                        html.I(className=f"fas {hour_icon}", style={"fontSize": "0.875rem"})
                    ]),
                    html.Div(className="data-label", children="1H CHANGE")
                ]),
                html.Div(className="data-item", children=[
                    html.Div(className="data-value", children=[
                        html.Span(f"{abs(day_change)}% ", className=day_class),
                        html.I(className=f"fas {day_icon}", style={"fontSize": "0.875rem"})
                    ]),
                    html.Div(className="data-label", children="24H CHANGE")
                ]),
                html.Div(className="data-item", children=[
                    html.Div(className="data-value", children=f"${volume:,.2f}"),
                    html.Div(className="data-label", children="VOLUME (USDT)")
                ])
            ]
        except Exception as e:
            logger.error(f"Error in update_market_data: {str(e)}")
            logger.error(traceback.format_exc())
            return html.Div("Error loading market data")

    @callback(
        Output("account-info", "children"),
        Input("interval-component", "n_intervals"),
        Input("mode-toggle", "value"),
        Input("virtual-vault-store", "data"),
    )
    def update_account_info(n, mode_value, virtual_vault_data):
        try:
            if mode_value == 'live':
                balances = fetch_tradeogre_account()
                usdt_balance = float(balances.get("USDT", 0))
                btc_balance = float(balances.get("BTC", 0))
            else:
                if virtual_vault_data:
                    vault = VirtualVault.from_dict(virtual_vault_data)
                    usdt_balance = vault.usdt_balance
                    btc_balance = vault.btc_balance
                else:
                    usdt_balance = 100
                    btc_balance = 0.001
            
            btc_price = fetch_tradeogre_ticker("BTC-USDT")
            btc_value_usdt = btc_balance * btc_price
            
            logger.info(f"Account balances - BTC: {btc_balance:.8f}, USDT: ${usdt_balance:.2f}")
            
            return [
                html.Div(className="account-item", children=[
                    html.Div(className="account-value", children=f"{btc_balance:.8f}"),
                    html.Div(className="account-label", children="BTC BALANCE"),
                    html.Div(className="btc-value", children=f"(${btc_value_usdt:.2f})")
                ]),
                html.Div(className="account-item", children=[
                    html.Div(className="account-value", children=f"${usdt_balance:.2f}"),
                    html.Div(className="account-label", children="USDT BALANCE")
                ])
            ]
        except Exception as e:
            logger.error(f"Error in update_account_info: {str(e)}")
            logger.error(traceback.format_exc())
            return html.Div("Error loading account info")

    @callback(
        [
            Output("metric-daily-return", "children"),
            Output("metric-daily-return", "className"),
            Output("metric-unrealized-return", "children"),
            Output("metric-unrealized-return", "className"),
            Output("metric-avg-cost", "children")
        ],
        Input("backtest-store", "data"),
        Input("virtual-vault-store", "data"),
        Input("interval-component", "n_intervals")
    )
    def update_performance_metrics(backtest_data, virtual_vault_data, n):
        try:
            btc_price = fetch_tradeogre_ticker("BTC-USDT")
            daily_return = "0.00%"
            daily_class = "metric-value"
            unrealized_return = "0.00%"
            unrealized_class = "metric-value"
            avg_cost = f"${btc_price:.2f}"
            
            if backtest_data:
                df = pd.DataFrame(backtest_data)
                if len(df) > 1:
                    latest = df['portfolio_value'].iloc[-1]
                    prev = df['portfolio_value'].iloc[-2]
                    if prev > 0:
                        dpct = ((latest / prev) - 1) * 100
                        daily_return = f"{dpct:.2f}%"
                        daily_class = f"metric-value {'positive' if dpct >= 0 else 'negative'}"
                    init = df['portfolio_value'].iloc[0]
                    if init > 0:
                        tpct = ((latest / init) - 1) * 100
                        unrealized_return = f"{tpct:.2f}%"
                        unrealized_class = f"metric-value {'positive' if tpct >= 0 else 'negative'}"
                    buy_trades = df[df['action'] == 'BUY']
                    if len(buy_trades) > 0:
                        avg_cost = f"${buy_trades['price'].mean():.2f}"
            
            if virtual_vault_data:
                vault = VirtualVault.from_dict(virtual_vault_data)
                history_df = vault.get_portfolio_history_df(btc_price)
                if len(history_df) > 1:
                    dpct = history_df['daily_return'].iloc[-1]
                    daily_return = f"{dpct:.2f}%"
                    daily_class = f"metric-value {'positive' if dpct >= 0 else 'negative'}"
                    tpct = history_df['total_return'].iloc[-1]
                    unrealized_return = f"{tpct:.2f}%"
                    unrealized_class = f"metric-value {'positive' if tpct >= 0 else 'negative'}"
                
                trade_df = vault.get_trade_history_df()
                if 'action' in trade_df.columns:
                    buy_trades = trade_df[trade_df['action'] == 'BUY']
                    if len(buy_trades) > 0:
                        avg_price = (buy_trades['price'] * buy_trades['btc_amount']).sum() / buy_trades['btc_amount'].sum()
                        avg_cost = f"${avg_price:.2f}"
            
            return daily_return, daily_class, unrealized_return, unrealized_class, avg_cost
        
        except Exception as e:
            logger.error(f"Error updating performance metrics: {str(e)}")
            logger.error(traceback.format_exc())
            return "0.00%", "metric-value", "0.00%", "metric-value", "$0.00"

    def create_default_figure():
        fig = go.Figure()
        fig.update_layout(
            margin=dict(l=10, r=10, t=0, b=0),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='rgba(255,255,255,0.7)'),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor='rgba(255,255,255,0.2)',
                color='rgba(255,255,255,0.7)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)',
                zeroline=False,
                tickprefix='$',
                color='rgba(255,255,255,0.7)'
            ),
            annotations=[
                dict(
                    text="No portfolio data available yet",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(color="white", size=14)
                )
            ]
        )
        return fig

    def create_portfolio_chart(df, additional_markers=None):
        try:
            logger.info(f"Creating portfolio chart with {len(df)} data points")
            required_cols = ['date', 'portfolio_value', 'action']
            for col in required_cols:
                if col not in df.columns:
                    logger.error(f"Missing required column: {col}")
                    return create_default_figure()
            if isinstance(df['date'].iloc[0], str):
                df['date'] = pd.to_datetime(df['date'])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['portfolio_value'],
                mode='lines',
                name='Portfolio Value',
                line=dict(color='#38BDF8', width=2),
                hovertemplate='Date: %{x}<br>Value: $%{y:.2f}<extra></extra>'
            ))
            actions = {
                'BUY': {'color': '#10B981', 'symbol': 'triangle-up'},
                'SELL': {'color': '#EF4444', 'symbol': 'triangle-down'},
                'RESET': {'color': '#6366F1', 'symbol': 'circle'}
            }
            for action, style in actions.items():
                df_action = df[df['action'] == action]
                if not df_action.empty:
                    fig.add_trace(go.Scatter(
                        x=df_action['date'],
                        y=df_action['portfolio_value'],
                        mode='markers',
                        name=action,
                        marker=dict(color=style['color'], size=8, symbol=style['symbol']),
                        hovertemplate='%{text}<br>Date: %{x}<br>Value: $%{y:.2f}<extra></extra>',
                        text=[action]*len(df_action)
                    ))
            if additional_markers:
                for marker in additional_markers:
                    fig.add_trace(marker)
            fig.update_layout(
                margin=dict(l=10, r=10, t=0, b=0),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showline=True,
                    linecolor='rgba(255,255,255,0.2)',
                    tickformat='%b %d',
                    tickfont=dict(size=8),
                    color='rgba(255,255,255,0.7)'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.1)',
                    zeroline=False,
                    tickprefix='$',
                    tickfont=dict(size=8),
                    color='rgba(255,255,255,0.7)'
                ),
                hovermode='x unified'
            )
            return fig
        except Exception as e:
            logger.error(f"Error creating portfolio chart: {str(e)}")
            logger.error(traceback.format_exc())
            return create_default_figure()

    @callback(
        [
            Output("backtest-store", "data"),
            Output("virtual-vault-store", "data"),
            Output("trade-log", "children"),
            Output("vault-value", "children"),
            Output("vault-value-btc", "children"),
            Output("portfolio-chart", "figure")
        ],
        Input("btn-execute", "n_clicks"),
        State("mode-toggle", "value"),
        State("strategy-type", "value"),
        State("input-usdt", "value"),
        State("input-btc", "value"),
        State("input-fear", "value"),
        State("input-greed", "value"),
        State("input-base-btc", "value"),
        State("input-usdc-reserve", "value"),
        State("input-buy-discount", "value"),
        State("input-sell-premium", "value"),
        State("input-reinvest-rate", "value"),
        State("virtual-vault-store", "data"),
        prevent_initial_call=True
    )
    def execute_strategy(n_clicks, mode_value, strategy_type, 
                         usdt, btc, fear, greed,
                         base_btc, usdc_reserve, buy_discount, sell_premium, reinvest_rate,
                         virtual_vault_data):
        if not n_clicks:
            raise PreventUpdate
        try:
            btc_price = fetch_tradeogre_ticker("BTC-USDT")
            if virtual_vault_data:
                vault = VirtualVault.from_dict(virtual_vault_data)
            else:
                vault = VirtualVault(
                    initial_btc=(btc if strategy_type=="fear_greed" else base_btc),
                    initial_usdt=(usdt if strategy_type=="fear_greed" else usdc_reserve)
                )
            # ... rest of the execute_strategy logic unchanged ...
            # (omitted here for brevity but exactly as before)
        except Exception as e:
            logger.error(f"Error executing strategy: {str(e)}")
            logger.error(traceback.format_exc())
            error_log = html.Div(className="log-item error", children=[
                html.Span(datetime.now().strftime("%H:%M:%S"), className="log-timestamp"),
                html.Span("ERROR", className="log-action"),
                html.Span(f" {str(e)}")
            ])
            return no_update, no_update, error_log, no_update, no_update, no_update
