"""
Angel One & TradingView Authentic Style Chart Plotter.
Renders high-fidelity TradingView candlesticks, fused volume, right-axis price badge,
S/R zones, CPR, PDH/PDL, and the authentic TradingView Long/Short Position Tool.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any, List, Optional


class ChartPlotter:
    # Official TradingView & Angel One Dark Theme Palette
    TV_BG = "#131722"
    TV_GRID = "#1E222D"
    TV_GREEN = "#089981"
    TV_RED = "#F23645"
    TV_TEXT = "#D1D4DC"
    TV_MUTED = "#787B86"

    @classmethod
    def create_trade_chart(
        cls,
        df: pd.DataFrame,
        trade_plan: Dict[str, Any],
        timeframe: str = "5m",
        show_sr: bool = True,
        show_cpr: bool = True,
        show_pdh_pdl: bool = True,
        show_fvg: bool = True,
        show_trade_overlay: bool = True,
        height: int = 580,
        is_grid_compact: bool = False
    ) -> go.Figure:
        """
        Creates an authentic Angel One / TradingView styled chart.
        Volume is fused on the secondary y-axis at the lower 18% of the canvas.
        """
        if df.empty or len(df) < 2:
            fig = go.Figure()
            fig.add_annotation(
                text="No candle data available for this timeframe",
                showarrow=False,
                font=dict(size=14, color=cls.TV_MUTED)
            )
            fig.update_layout(paper_bgcolor=cls.TV_BG, plot_bgcolor=cls.TV_BG, height=height)
            return fig

        # Fused single canvas with secondary y-axis for volume (Angel One TradingView Style)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        x_vals = df["datetime"] if "datetime" in df.columns else df.index

        # 1. Fused Volume Bars (Bottom 18% of Canvas)
        max_vol = float(df["volume"].max()) if not df["volume"].empty else 1.0
        vol_colors = [
            "rgba(8, 153, 129, 0.28)" if c >= o else "rgba(242, 54, 69, 0.28)"
            for c, o in zip(df["close"], df["open"])
        ]
        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=df["volume"],
                name="Volume",
                marker_color=vol_colors,
                hoverinfo="y",
                showlegend=False
            ),
            secondary_y=True
        )

        # Scale volume axis so it remains in lower 18% of chart
        fig.update_yaxes(
            range=[0, max_vol * 5.5],
            showgrid=False,
            showticklabels=False,
            secondary_y=True
        )

        # 2. TradingView Candlestick Trace
        fig.add_trace(
            go.Candlestick(
                x=x_vals,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Candles",
                increasing_line_color=cls.TV_GREEN,
                decreasing_line_color=cls.TV_RED,
                increasing_fillcolor=cls.TV_GREEN,
                decreasing_fillcolor=cls.TV_RED,
                line=dict(width=1)
            ),
            secondary_y=False
        )

        # 3. Dynamic Moving Averages & VWAP (TradingView Colors)
        if "vwap" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x_vals, y=df["vwap"],
                    mode="lines", name="VWAP",
                    line=dict(color="#FFEB3B", width=1.8),
                    hoverinfo="name+y"
                ),
                secondary_y=False
            )
        if "ema_9" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x_vals, y=df["ema_9"],
                    mode="lines", name="9 EMA",
                    line=dict(color="#2962FF", width=1.3),
                    hoverinfo="name+y"
                ),
                secondary_y=False
            )
        if "ema_21" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x_vals, y=df["ema_21"],
                    mode="lines", name="21 EMA",
                    line=dict(color="#FF9800", width=1.3),
                    hoverinfo="name+y"
                ),
                secondary_y=False
            )
        if "ema_50" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x_vals, y=df["ema_50"],
                    mode="lines", name="50 EMA",
                    line=dict(color="#00E5FF", width=1.2),
                    hoverinfo="name+y"
                ),
                secondary_y=False
            )
        if "ema_200" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x_vals, y=df["ema_200"],
                    mode="lines", name="200 EMA",
                    line=dict(color="#FFFFFF", width=1.5, dash="dot"),
                    hoverinfo="name+y"
                ),
                secondary_y=False
            )

        # 4. Support & Resistance Zones
        sr_zones = trade_plan.get("sr_zones", {})
        if show_sr and sr_zones and not is_grid_compact:
            for i, r in enumerate(sr_zones.get("resistances", [])[:3]):
                r_lvl = r["level"]
                fig.add_hrect(
                    y0=r.get("min_price", r_lvl * 0.998),
                    y1=r.get("max_price", r_lvl * 1.002),
                    fillcolor="rgba(242, 54, 69, 0.12)",
                    line_color="rgba(242, 54, 69, 0.45)",
                    line_width=1,
                    annotation_text=f"Resistance {i+1} (₹{r_lvl:,.1f})",
                    annotation_position="top right",
                    annotation_font=dict(size=9, color="#FF8A80"),
                    secondary_y=False
                )
            for i, s in enumerate(sr_zones.get("supports", [])[:3]):
                s_lvl = s["level"]
                fig.add_hrect(
                    y0=s.get("min_price", s_lvl * 0.998),
                    y1=s.get("max_price", s_lvl * 1.002),
                    fillcolor="rgba(8, 153, 129, 0.12)",
                    line_color="rgba(8, 153, 129, 0.45)",
                    line_width=1,
                    annotation_text=f"Support {i+1} (₹{s_lvl:,.1f})",
                    annotation_position="bottom right",
                    annotation_font=dict(size=9, color="#A7F3D0"),
                    secondary_y=False
                )

        # 5. Central Pivot Range (CPR)
        cpr = trade_plan.get("cpr", {})
        if show_cpr and cpr and "pivot" in cpr and not is_grid_compact:
            fig.add_hline(
                y=cpr["pivot"],
                line=dict(color="#FFD600", width=1.2, dash="dash"),
                annotation_text=f"P (₹{cpr['pivot']:,.1f})",
                annotation_position="bottom left",
                annotation_font=dict(size=9, color="#FFD600"),
                secondary_y=False
            )
            fig.add_hline(
                y=cpr["tc"],
                line=dict(color="#FFAB00", width=1.0, dash="dot"),
                annotation_text="TC",
                annotation_position="top left",
                annotation_font=dict(size=8, color="#FFAB00"),
                secondary_y=False
            )
            fig.add_hline(
                y=cpr["bc"],
                line=dict(color="#FFAB00", width=1.0, dash="dot"),
                annotation_text="BC",
                annotation_position="bottom left",
                annotation_font=dict(size=8, color="#FFAB00"),
                secondary_y=False
            )

        # 6. Previous Day High (PDH) & Low (PDL)
        pdh_pdl = trade_plan.get("pdh_pdl", {})
        if show_pdh_pdl and pdh_pdl and not is_grid_compact:
            if "pdh" in pdh_pdl:
                fig.add_hline(
                    y=pdh_pdl["pdh"],
                    line=dict(color="#E040FB", width=1.2, dash="dashdot"),
                    annotation_text=f"PDH (₹{pdh_pdl['pdh']:,.1f})",
                    annotation_position="top right",
                    annotation_font=dict(size=9, color="#E040FB"),
                    secondary_y=False
                )
            if "pdl" in pdh_pdl:
                fig.add_hline(
                    y=pdh_pdl["pdl"],
                    line=dict(color="#00E5FF", width=1.2, dash="dashdot"),
                    annotation_text=f"PDL (₹{pdh_pdl['pdl']:,.1f})",
                    annotation_position="bottom right",
                    annotation_font=dict(size=9, color="#00E5FF"),
                    secondary_y=False
                )

        # 7. Fair Value Gaps (FVG)
        fvgs = trade_plan.get("fvgs", [])
        if show_fvg and fvgs and not is_grid_compact:
            for fvg in fvgs[-3:]:
                color = "rgba(8, 153, 129, 0.14)" if fvg["type"] == "BULLISH_FVG" else "rgba(242, 54, 69, 0.14)"
                border = "rgba(8, 153, 129, 0.4)" if fvg["type"] == "BULLISH_FVG" else "rgba(242, 54, 69, 0.4)"
                fig.add_hrect(
                    y0=fvg["bottom"],
                    y1=fvg["top"],
                    fillcolor=color,
                    line_color=border,
                    line_width=1,
                    annotation_text="FVG",
                    annotation_position="inside left",
                    annotation_font=dict(size=8, color=cls.TV_MUTED),
                    secondary_y=False
                )

        # 8. TradingView Long / Short Position Tool (Authentic Risk/Reward Box)
        if show_trade_overlay and trade_plan.get("direction") in ("BUY", "SELL"):
            direction = trade_plan["direction"]
            entry = trade_plan.get("entry_price")
            sl = trade_plan.get("stop_loss")
            t1 = trade_plan.get("target_1")
            t2 = trade_plan.get("target_2")
            rrr = trade_plan.get("risk_reward_ratio", "1:2")

            # Entry Level (TradingView Blue Line)
            fig.add_hline(
                y=entry,
                line=dict(color="#2962FF", width=2.0, dash="solid"),
                annotation_text=f"ENTRY: ₹{entry:,.2f}",
                annotation_position="top left",
                annotation_font=dict(size=11, color="#2962FF", family="Trebuchet MS, sans-serif"),
                secondary_y=False
            )

            # Stop Loss Level (TradingView Red Line)
            fig.add_hline(
                y=sl,
                line=dict(color=cls.TV_RED, width=2.0, dash="dash"),
                annotation_text=f"SL: ₹{sl:,.2f}",
                annotation_position="bottom left",
                annotation_font=dict(size=11, color=cls.TV_RED, family="Trebuchet MS, sans-serif"),
                secondary_y=False
            )

            # Target 1 (Partial Booking)
            fig.add_hline(
                y=t1,
                line=dict(color=cls.TV_GREEN, width=1.5, dash="dash"),
                annotation_text=f"T1: ₹{t1:,.2f}",
                annotation_position="top left",
                annotation_font=dict(size=10, color=cls.TV_GREEN),
                secondary_y=False
            )

            # Target 2 (Full Target)
            fig.add_hline(
                y=t2,
                line=dict(color=cls.TV_GREEN, width=2.0, dash="solid"),
                annotation_text=f"T2: ₹{t2:,.2f} (R:R {rrr})",
                annotation_position="top left",
                annotation_font=dict(size=11, color=cls.TV_GREEN, family="Trebuchet MS, sans-serif"),
                secondary_y=False
            )

            # TradingView Shaded Long/Short Position Box
            if direction == "BUY":
                fig.add_hrect(
                    y0=sl, y1=entry,
                    fillcolor="rgba(242, 54, 69, 0.16)",
                    line_color="rgba(242, 54, 69, 0.5)",
                    line_width=1,
                    secondary_y=False
                )
                fig.add_hrect(
                    y0=entry, y1=t2,
                    fillcolor="rgba(8, 153, 129, 0.16)",
                    line_color="rgba(8, 153, 129, 0.5)",
                    line_width=1,
                    secondary_y=False
                )
            else:
                fig.add_hrect(
                    y0=entry, y1=sl,
                    fillcolor="rgba(242, 54, 69, 0.16)",
                    line_color="rgba(242, 54, 69, 0.5)",
                    line_width=1,
                    secondary_y=False
                )
                fig.add_hrect(
                    y0=t2, y1=entry,
                    fillcolor="rgba(8, 153, 129, 0.16)",
                    line_color="rgba(8, 153, 129, 0.5)",
                    line_width=1,
                    secondary_y=False
                )

        # 9. Current LTP Marker Pill on Right Axis
        curr_p = float(df["close"].iloc[-1])
        fig.add_hline(
            y=curr_p,
            line=dict(color="#2962FF", width=1.0, dash="dot"),
            annotation_text=f"₹{curr_p:,.2f}",
            annotation_position="right",
            annotation_font=dict(size=10, color="#FFFFFF"),
            annotation_bgcolor="#2962FF",
            secondary_y=False
        )

        # Layout Styling (TradingView & Angel One Specification)
        symbol = trade_plan.get("symbol", "CHART")
        fig.update_layout(
            title=dict(
                text=f"<b>{symbol}</b> • {timeframe.upper()}",
                x=0.015,
                y=0.98,
                font=dict(size=14, color=cls.TV_TEXT, family="Trebuchet MS, sans-serif")
            ),
            template="plotly_dark",
            paper_bgcolor=cls.TV_BG,
            plot_bgcolor=cls.TV_BG,
            xaxis_rangeslider_visible=False,
            dragmode="pan",
            height=height,
            margin=dict(l=15, r=65, t=35, b=20),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="right",
                x=1,
                font=dict(size=9, color=cls.TV_MUTED)
            )
        )

        # Crisp fine dotted gridlines like TradingView
        fig.update_xaxes(
            showgrid=True,
            gridcolor=cls.TV_GRID,
            gridwidth=1,
            griddash="dot",
            showline=True,
            linecolor=cls.TV_GRID,
            tickfont=dict(size=10, color=cls.TV_MUTED)
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor=cls.TV_GRID,
            gridwidth=1,
            griddash="dot",
            showline=True,
            linecolor=cls.TV_GRID,
            side="right",
            tickfont=dict(size=10, color=cls.TV_MUTED),
            secondary_y=False
        )

        return fig
