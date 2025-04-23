import pandas as pd
import numpy as np
from datetime import datetime
import traceback
import logging
from dash import Output, Input, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

# Strategy and vault imports
from strategies.fear_greed import run_backtest, get_live_trade_signal
from strategies.dual_trade import DualTradeStrategy
from strategies.virtual_vault import VirtualVault

# API helpers
from scripts.utils import (
    fetch_tradeogre_orderbook,
    fetch_tradeogre_ticker,
    fetch_tradeogre_account,
    execute_live_trade
)

logger = logging.getLogger(__name__)

def register_callbacks(app):
    """Register all callbacks for the application"""

    @app.callback(
        Output("last-updated", "children"),
        Input("interval-component", "n_intervals")
    )
    def update_time(n):
        return html.Span(f"Last Updated: {datetime.now().strftime('%H:%M:%S')} ")

    @app.callback(
        Output("mode-badge", "className"),
        Output("mode-badge", "children"),
        Input("mode-toggle", "value")
    )
    def update_mode_badge(mode):
        if mode == "live":
            return "live-badge", [
                html.I(className="fas fa-satellite-dish"),
                html.Span("Live Trading")
            ]
        return "test-badge", [
            html.I(className="fas fa-flask"),
            html.Span("Test Mode")
        ]

    @app.callback(
        Output("strategy-notes", "children"),
        Input("strategy-type", "value")
    )
    def update_strategy_notes(strategy):
        if strategy == "fear_greed":
            return [
                html.H4(
                    "Fear & Greed Strategy",
                    style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
                    children=[html.I(className="fas fa-lightbulb", style={"color": "#F59E0B"}), "Fear & Greed Strategy"]
                ),
                html.Div(className="strategy-notes", children=[
                    html.P("• Buy when Fear & Greed < 40 with 50% of USDT"),
                    html.P("• Sell when Fear & Greed > 60 with 50% of BTC"),
                    html.P("• Reset when BTC ≥ 0.011 to [USDT: 200, BTC: 0.0022]")
                ])
            ]
        return [
            html.H4(
                "Dual-Trade Strategy",
                style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
                children=[html.I(className="fas fa-lightbulb", style={"color": "#F59E0B"}), "Dual-Trade Strategy"]
            ),
            html.Div(className="strategy-notes", children=[
                html.P("• Place simultaneous buy & sell orders daily"),
                html.P("• Buy at current price × (1 - buy discount)"),
                html.P("• Sell at current price × (1 + sell premium)"),
                html.P("• When one order fills, cancel the other"),
                html.P("• Reinvest profits based on reinvestment rate")
            ])
        ]

    @app.callback(
        Output("fear-greed-controls", "style"),
        Output("dual-trade-controls", "style"),
        Input("strategy-type", "value")
    )
    def toggle_strategy_controls(strategy):
        if strategy == "fear_greed":
            return {"display": "block"}, {"display": "none"}
        return {"display": "none"}, {"display": "block"}

    @app.callback(
        Output("connection-status", "children"),
        Input("interval-component", "n_intervals")
    )
    def update_connection_status(n):
        try:
            price = fetch_tradeogre_ticker("BTC-USDT")
            if price > 0:
                return [
                    html.I(className="fas fa-circle"),
                    html.Span("Connected")
                ]
            return [
                html.I(className="fas fa-circle", style={"color": "#F59E0B"}),
                html.Span("Degraded", style={"color": "#F59E0B"})
            ]
        except Exception:
            return [
                html.I(className="fas fa-circle", style={"color": "#EF4444"}),
                html.Span("Disconnected", style={"color": "#EF4444"})
            ]

    @app.callback(
        Output("market-data-grid", "children"),
        Input("interval-component", "n_intervals")
    )
    def update_market_data(n):
        try:
            price = fetch_tradeogre_ticker("BTC-USDT")
            # Placeholder demo values
            hour_change, day_change = 0.75, -1.2
            volume = 1234.56
            hour_class = "positive" if hour_change > 0 else "negative"
            hour_icon = "fa-caret-up" if hour_change > 0 else "fa-caret-down"
            day_class = "positive" if day_change > 0 else "negative"
            day_icon = "fa-caret-up" if day_change > 0 else "fa-caret-down"
            return [
                html.Div(className="data-item", children=[
                    html.Div(className="data-value", children=f"${price:,.2f}"),
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
            logger.error(f"Error in update_market_data: {e}")
            logger.error(traceback.format_exc())
            return html.Div("Error loading market data")

    @app.callback(
        Output("account-info", "children"),
        Input("interval-component", "n_intervals"),
        Input("mode-toggle", "value"),
        Input("virtual-vault-store", "data")
    )
    def update_account_info(n, mode, vault_data):
        try:
            if mode == "live":
                balances = fetch_tradeogre_account()
                usdt = float(balances.get("USDT", 0))
                btc = float(balances.get("BTC", 0))
            else:
                if vault_data:
                    vault = VirtualVault.from_dict(vault_data)
                    usdt, btc = vault.usdt_balance, vault.btc_balance
                else:
                    usdt, btc = 100, 0.001
            price = fetch_tradeogre_ticker("BTC-USDT")
            btc_value = btc * price
            logger.info(f"Account balances - BTC: {btc:.8f}, USDT: ${usdt:.2f}")
            return [
                html.Div(className="account-item", children=[
                    html.Div(className="account-value", children=f"{btc:.8f}"),
                    html.Div(className="account-label", children="BTC BALANCE"),
                    html.Div(className="btc-value", children=f"(${btc_value:.2f})")
                ]),
                html.Div(className="account-item", children=[
                    html.Div(className="account-value", children=f"${usdt:.2f}"),
                    html.Div(className="account-label", children="USDT BALANCE")
                ])
            ]
        except Exception as e:
            logger.error(f"Error in update_account_info: {e}")
            logger.error(traceback.format_exc())
            return html.Div("Error loading account info")

    @app.callback(
        Output("metric-daily-return", "children"),
        Output("metric-daily-return", "className"),
        Output("metric-unrealized-return", "children"),
        Output("metric-unrealized-return", "className"),
        Output("metric-avg-cost", "children"),
        Input("backtest-store", "data"),
        Input("virtual-vault-store", "data"),
        Input("interval-component", "n_intervals")
    )
    def update_performance_metrics(backtest_data, vault_data, n):
        try:
            price = fetch_tradeogre_ticker("BTC-USDT")
            daily_return, daily_cls = "0.00%", "metric-value"
            unreal_return, unreal_cls = "0.00%", "metric-value"
            avg_cost = f"${price:.2f}"

            # Backtest-based metrics
            if backtest_data:
                df = pd.DataFrame(backtest_data)
                if len(df) > 1:
                    latest, prev = df["portfolio_value"].iloc[-1], df["portfolio_value"].iloc[-2]
                    if prev > 0:
                        dpct = ((latest / prev) - 1) * 100
                        daily_return = f"{dpct:.2f}%"
                        daily_cls = f"metric-value {'positive' if dpct >= 0 else 'negative'}"
                    init = df["portfolio_value"].iloc[0]
                    if init > 0:
                        tpct = ((latest / init) - 1) * 100
                        unreal_return = f"{tpct:.2f}%"
                        unreal_cls = f"metric-value {'positive' if tpct >= 0 else 'negative'}"
                    buys = df[df["action"] == "BUY"]
                    if len(buys) > 0:
                        avg_cost = f"${buys['price'].mean():.2f}"

            # Virtual-vault–based metrics override
            if vault_data:
                vault = VirtualVault.from_dict(vault_data)
                hist = vault.get_portfolio_history_df(price)
                if len(hist) > 1:
                    dpct = hist["daily_return"].iloc[-1]
                    daily_return = f"{dpct:.2f}%"
                    daily_cls = f"metric-value {'positive' if dpct >= 0 else 'negative'}"
                    tpct = hist["total_return"].iloc[-1]
                    unreal_return = f"{tpct:.2f}%"
                    unreal_cls = f"metric-value {'positive' if tpct >= 0 else 'negative'}"
                trade_df = vault.get_trade_history_df()
                buys = trade_df[trade_df["action"] == "BUY"]
                if len(buys) > 0:
                    avg_price = (buys["price"] * buys["btc_amount"]).sum() / buys["btc_amount"].sum()
                    avg_cost = f"${avg_price:.2f}"

            return daily_return, daily_cls, unreal_return, unreal_cls, avg_cost

        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
            logger.error(traceback.format_exc())
            return "0.00%", "metric-value", "0.00%", "metric-value", "$0.00"

    def create_default_figure():
        """Create a default chart styled for dark theme."""
        fig = go.Figure()
        fig.update_layout(
            margin=dict(l=10, r=10, t=0, b=0),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(255,255,255,0.7)"),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.2)",
                color="rgba(255,255,255,0.7)"
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.1)",
                zeroline=False,
                tickprefix="$",
                color="rgba(255,255,255,0.7)"
            ),
            annotations=[dict(
                text="No portfolio data available yet",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(color="white", size=14)
            )]
        )
        return fig

    def create_portfolio_chart(df, additional_markers=None):
        """Create a portfolio‐value chart from backtest or vault history."""
        try:
            logger.info(f"Creating portfolio chart with {len(df)} data points")
            required = ["date", "portfolio_value", "action"]
            for col in required:
                if col not in df.columns:
                    logger.error(f"Missing required column: {col}")
                    return create_default_figure()

            if isinstance(df["date"].iloc[0], str):
                df["date"] = pd.to_datetime(df["date"])

            fig = go.Figure()
            # main line
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df["portfolio_value"],
                mode="lines",
                name="Portfolio Value",
                line=dict(color="#38BDF8", width=2),
                hovertemplate="Date: %{x}<br>Value: $%{y:.2f}<extra></extra>"
            ))
            # markers
            actions = {
                "BUY": {"color": "#10B981", "symbol": "triangle-up"},
                "SELL": {"color": "#EF4444", "symbol": "triangle-down"},
                "RESET": {"color": "#6366F1", "symbol": "circle"}
            }
            for act, style in actions.items():
                df_a = df[df["action"] == act]
                if not df_a.empty:
                    fig.add_trace(go.Scatter(
                        x=df_a["date"],
                        y=df_a["portfolio_value"],
                        mode="markers",
                        name=act,
                        marker=dict(color=style["color"], size=8, symbol=style["symbol"]),
                        hovertemplate="%{text}<br>Date: %{x}<br>Value: $%{y:.2f}<extra></extra>",
                        text=[act] * len(df_a)
                    ))
            if additional_markers:
                for m in additional_markers:
                    fig.add_trace(m)

            fig.update_layout(
                margin=dict(l=10, r=10, t=0, b=0),
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showline=True,
                    linecolor="rgba(255,255,255,0.2)",
                    tickformat="%b %d",
                    tickfont=dict(size=8),
                    color="rgba(255,255,255,0.7)"
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.1)",
                    zeroline=False,
                    tickprefix="$",
                    tickfont=dict(size=8),
                    color="rgba(255,255,255,0.7)"
                ),
                hovermode="x unified"
            )
            return fig

        except Exception as e:
            logger.error(f"Error creating portfolio chart: {e}")
            logger.error(traceback.format_exc())
            return create_default_figure()

    @app.callback(
        Output("backtest-store", "data"),
        Output("virtual-vault-store", "data"),
        Output("trade-log", "children"),
        Output("vault-value", "children"),
        Output("vault-value-btc", "children"),
        Output("portfolio-chart", "figure"),
        Input("btn-execute", "n_clicks"),
        State("mode-toggle", "value"),
        State("strategy-type", "value"),
        # Fear & Greed params
        State("input-usdt", "value"),
        State("input-btc", "value"),
        State("input-fear", "value"),
        State("input-greed", "value"),
        # Dual Trade params
        State("input-base-btc", "value"),
        State("input-usdc-reserve", "value"),
        State("input-buy-discount", "value"),
        State("input-sell-premium", "value"),
        State("input-reinvest-rate", "value"),
        # Virtual vault state
        State("virtual-vault-store", "data"),
        prevent_initial_call=True
    )
    def execute_strategy(
        n_clicks, mode, strategy_type,
        usdt, btc, fear, greed,
        base_btc, usdc_reserve, buy_discount, sell_premium, reinvest_rate,
        vault_data
    ):
        logger.debug(f"execute_strategy clicked: n_clicks={n_clicks}, mode={mode}, strategy={strategy_type}")
        if not n_clicks:
            raise PreventUpdate

        try:
            btc_price = fetch_tradeogre_ticker("BTC-USDT")
            if vault_data:
                vault = VirtualVault.from_dict(vault_data)
            else:
                vault = VirtualVault(
                    initial_btc=(btc if strategy_type == "fear_greed" else base_btc),
                    initial_usdt=(usdt if strategy_type == "fear_greed" else usdc_reserve)
                )

            # ─── Fear & Greed Strategy ─────────────────────────────────────────────
            if strategy_type == "fear_greed":
                if mode == "live":
                    logger.info(f"Live F&G: Fear={fear}, Greed={greed}")
                    action, amount = get_live_trade_signal(None, vault.usdt_balance, vault.btc_balance, fear, greed)
                    if action != "HOLD":
                        result = execute_live_trade(action, amount, price=btc_price)
                        ts = datetime.now().strftime("%H:%M:%S")
                        cls = action.lower()
                        if result.get("success"):
                            vault.execute_trade(action, amount, btc_price)
                            log_item = html.Div(className=f"log-item {cls}", children=[
                                html.Span(ts, className="log-timestamp"),
                                html.Span(action, className=f"log-action {cls}"),
                                html.Span(f" {result.get('quantity', amount):.6f} @ ${btc_price:.2f}")
                            ])
                        else:
                            log_item = html.Div(className="log-item error", children=[
                                html.Span(ts, className="log-timestamp"),
                                html.Span("ERROR", className="log-action"),
                                html.Span(f" {result.get('error','unknown')}")
                            ])
                        fig = create_portfolio_chart(vault.get_portfolio_history_df(btc_price))
                    else:
                        ts = datetime.now().strftime("%H:%M:%S")
                        log_item = html.Div(className="log-item", children=[
                            html.Span(ts, className="log-timestamp"),
                            html.Span("HOLD", className="log-action"),
                            html.Span(" - No trade signal generated")
                        ])
                        fig = no_update

                    vault_val = vault.get_total_value_usd(btc_price)
                    return (
                        no_update,
                        vault.to_dict(),
                        log_item,
                        f"${vault_val:.2f}",
                        f"{vault.btc_balance:.8f} BTC",
                        fig
                    )

                # ─── Backtest mode ────────────────────────────────────────────────────
                else:
                    logger.info(f"Backtest F&G: USDT={usdt}, BTC={btc}, Fear={fear}, Greed={greed}")
                    df = run_backtest(start_usdc=usdt, start_btc=btc, fg_fear=fear, fg_greed=greed)
                    fig = create_portfolio_chart(df)
                    trades = df[df["action"] != "HOLD"].sort_values("date", ascending=False)
                    logs = []
                    for _, r in trades.iterrows():
                        date_str = (r["date"].strftime("%Y-%m-%d")
                                    if isinstance(r["date"], pd.Timestamp) else r["date"])
                        cls = r["action"].lower()
                        logs.append(html.Div(className=f"log-item {cls}", children=[
                            html.Span(date_str, className="log-timestamp"),
                            html.Span(r["action"], className=f"log-action {cls}"),
                            html.Span(f" @ ${r['price']:.2f} | USDT: ${r['usdc_after']:.2f} | BTC: {r['btc_after']:.8f}")
                        ]))
                    latest = df.iloc[-1]
                    vault.reset(latest["btc_after"], latest["usdc_after"])
                    vault.update_market_price(btc_price)
                    return (
                        df.to_dict("records"),
                        vault.to_dict(),
                        html.Div(logs),
                        f"${latest['portfolio_value']:.2f}",
                        f"{latest['btc_after']:.8f} BTC",
                        fig
                    )

            # ─── Dual-Trade Strategy ───────────────────────────────────────────────
            strategy = DualTradeStrategy(
                base_btc=base_btc,
                usdt_reserve=usdc_reserve,
                buy_discount=buy_discount,
                sell_premium=sell_premium,
                reinvest_rate=reinvest_rate
            )

            if mode == "live":
                logger.info("Live Dual-Trade")
                buy_order, sell_order = strategy.generate_orders(btc_price)
                ts = datetime.now().strftime("%H:%M:%S")
                log_item = html.Div(className="log-item", children=[
                    html.Span(ts, className="log-timestamp"),
                    html.Span("DUAL TRADE", className="log-action"),
                    html.Span(f" BUY {buy_order['btc_amount']:.8f} @ ${buy_order['price']:.2f} | SELL {sell_order['btc_amount']:.8f} @ ${sell_order['price']:.2f}")
                ])
                vault_val = vault.get_total_value_usd(btc_price)
                return (
                    no_update,
                    vault.to_dict(),
                    log_item,
                    f"${vault_val:.2f}",
                    f"{vault.btc_balance:.8f} BTC",
                    no_update
                )

            # ─── Dual Trade Backtest ──────────────────────────────────────────────
            logger.info("Backtest Dual-Trade")
            results_df, final_btc, final_usdt = strategy.run_backtest(initial_price=btc_price)
            fig = create_portfolio_chart(results_df)
            trades = results_df[results_df["action"].isin(["BUY", "SELL"])].sort_values("date", ascending=False)
            logs = []
            for _, r in trades.iterrows():
                date_str = r["date"].strftime("%Y-%m-%d")
                cls = r["action"].lower()
                logs.append(html.Div(className=f"log-item {cls}", children=[
                    html.Span(date_str, className="log-timestamp"),
                    html.Span(r["action"], className=f"log-action {cls}"),
                    html.Span(f" @ ${r['price']:.2f} | Portfolio: ${r['portfolio_value']:.2f}")
                ]))
            final_val = results_df["portfolio_value"].iloc[-1]
            vault.reset(final_btc, final_usdt)
            vault.update_market_price(btc_price)
            return (
                results_df.to_dict("records"),
                vault.to_dict(),
                html.Div(logs),
                f"${final_val:.2f}",
                f"{final_btc:.8f} BTC",
                fig
            )

        except Exception as e:
            logger.error(f"Error executing strategy: {e}")
            logger.error(traceback.format_exc())
            error_log = html.Div(className="log-item error", children=[
                html.Span(datetime.now().strftime("%H:%M:%S"), className="log-timestamp"),
                html.Span("ERROR", className="log-action"),
                html.Span(f" {str(e)}")
            ])
            return no_update, no_update, error_log, no_update, no_update, no_update
