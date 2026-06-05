# =============================================================================
# EV Brand Sentiment Intelligence Dashboard
# =============================================================================
# Developer   : Michael Chen
# Course      : MSBA - Applied Data Engineering
# Stack       : Python, Dash, Plotly, SQLAlchemy, Supabase (PostgreSQL)
# =============================================================================
# To run: python tesla_dashboard.py
# Then open: http://127.0.0.1:8050
# =============================================================================

import pandas as pd
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# =============================================================================
# CONFIG
# =============================================================================
DB_USERNAME = "postgres.ttntqvcomspvbkdumfvx"
DB_PASSWORD = "Tesla2026sentiment"
DB_HOST     = "aws-1-us-east-1.pooler.supabase.com"
DB_PORT     = 6543
DB_NAME     = "postgres"

BRANDS = {
    "Tesla":   {"color": "#CC0000", "logo": "tesla.com"},
    "Rivian":  {"color": "#00B274", "logo": "rivian.com"},
    "Ford EV": {"color": "#0066CC", "logo": "ford.com"},
    "Hyundai": {"color": "#FF6B00", "logo": "hyundai.com"},
    "BYD":     {"color": "#7B2D8B", "logo": "byd.com"},
}

BG       = "#F8F9FA"
CARD     = "#FFFFFF"
BORDER   = "#E5E7EB"
GRID     = "#F3F4F6"
PRI      = "#111827"
SEC      = "#6B7280"
POS      = "#16A34A"
NEG      = "#DC2626"
NEU      = "#9CA3AF"
ACCENT   = "#2563EB"
SENT_CLR = {"positive": POS, "neutral": NEU, "negative": NEG}
ALL_SENTS = ["positive", "neutral", "negative"]

# Keywords for relevance filtering
RELEVANT_KEYWORDS = [
    "tesla", "elon", "musk", "rivian", "hyundai", "ford", "byd",
    "electric", "ev", " car", "vehicle", "battery", "autopilot",
    "cybertruck", "model", "charging", "ioniq", "mach-e", "lightning"
]

# =============================================================================
# DATABASE
# =============================================================================
def get_engine():
    return create_engine(URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USERNAME, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT, database=DB_NAME
    ))

def load_data():
    engine = get_engine()
    with engine.connect() as conn:
        art = pd.read_sql("SELECT * FROM tesla_sentiment.articles", conn)
        ev  = pd.read_sql("SELECT * FROM tesla_sentiment.tesla_events", conn)
    art["published_at"] = pd.to_datetime(art["published_at"]).dt.tz_localize(None)
    ev["event_date"]    = pd.to_datetime(ev["event_date"]).dt.tz_localize(None)
    return art, ev

articles, tesla_events = load_data()
ALL_BRANDS    = sorted(articles["brand"].unique().tolist())
MIN_DATE      = articles["published_at"].min().date()
MAX_DATE      = articles["published_at"].max().date()
DEFAULT_END   = MAX_DATE
DEFAULT_START = max(MIN_DATE, MAX_DATE - timedelta(days=30))

# =============================================================================
# HELPERS
# =============================================================================
def logo(domain):
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"

def card(children, mb="16px"):
    return html.Div(
        style={"backgroundColor": CARD, "borderRadius": "8px",
               "border": f"1px solid {BORDER}", "padding": "20px",
               "marginBottom": mb},
        children=children
    )

def lbl(text):
    return html.P(text, style={
        "color": SEC, "fontSize": "11px", "fontWeight": "600",
        "letterSpacing": "0.08em", "textTransform": "uppercase",
        "margin": "0 0 12px 0"
    })

def base_fig(fig, height, b_margin=8):
    fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(family="Inter, Arial, sans-serif", color=PRI, size=12),
        height=height,
        margin=dict(l=48, r=24, t=8, b=b_margin),
        xaxis=dict(gridcolor=GRID, linecolor=BORDER, showline=True,
                   zeroline=False, tickfont=dict(color=SEC, size=11)),
        yaxis=dict(gridcolor=GRID, linecolor=BORDER, showline=False,
                   zeroline=False, tickfont=dict(color=SEC, size=11)),
        legend=dict(bgcolor=CARD, bordercolor=BORDER, borderwidth=1,
                    font=dict(color=PRI, size=11), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font_color=PRI),
        hovermode="closest",
    )
    return fig

def is_relevant(title):
    t = str(title).lower()
    return any(kw in t for kw in RELEVANT_KEYWORDS)

def get_filtered(brands, sents, start, end):
    end_dt = pd.Timestamp(end) + pd.Timedelta(days=1)
    f = articles[
        (articles["brand"].isin(brands)) &
        (articles["sentiment_label"].isin(sents)) &
        (articles["published_at"] >= pd.Timestamp(start)) &
        (articles["published_at"] < end_dt)
    ]
    return f[f["title"].apply(is_relevant)]

# =============================================================================
# APP
# =============================================================================
app = dash.Dash(
    __name__,
    title="EV Sentiment Intelligence",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ]
)

app.layout = html.Div(
    style={"backgroundColor": BG, "minHeight": "100vh",
           "fontFamily": "Inter, Arial, sans-serif", "color": PRI},
    children=[

        # NAV
        html.Div(style={
            "backgroundColor": CARD, "borderBottom": f"1px solid {BORDER}",
            "padding": "0 32px", "display": "flex", "alignItems": "center",
            "justifyContent": "space-between", "height": "56px",
            "position": "sticky", "top": "0", "zIndex": "100",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"
        }, children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px"}, children=[
                html.Div(style={"width": "4px", "height": "24px",
                                "backgroundColor": NEG, "borderRadius": "2px"}),
                html.Span("EV Sentiment Intelligence",
                          style={"fontSize": "15px", "fontWeight": "700"}),
                html.Span("· Powered by NewsAPI + VADER",
                          style={"fontSize": "12px", "color": SEC, "marginLeft": "6px"})
            ]),
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "12px"}, children=[
                html.Span(id="last-updated", style={"fontSize": "12px", "color": SEC}),
                html.Button("↻ Refresh", id="refresh-btn", n_clicks=0,
                    style={"backgroundColor": ACCENT, "color": "white", "border": "none",
                           "padding": "6px 14px", "borderRadius": "6px",
                           "cursor": "pointer", "fontSize": "12px", "fontWeight": "600"})
            ])
        ]),

        html.Div(style={"padding": "24px 32px", "maxWidth": "1400px", "margin": "0 auto"},
        children=[

            # BRAND PILLS
            html.Div(style={"marginBottom": "20px"}, children=[
                lbl("Filter by Brand"),
                html.Div(style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
                    children=[
                        html.Div(
                            id="pill-" + b.replace(" ", "-"), n_clicks=0,
                            style={
                                "display": "flex", "alignItems": "center", "gap": "7px",
                                "padding": "7px 14px", "borderRadius": "999px",
                                "border": f"1.5px solid {BRANDS[b]['color']}",
                                "backgroundColor": BRANDS[b]["color"],
                                "cursor": "pointer", "userSelect": "none",
                                "transition": "all 0.15s"
                            },
                            children=[
                                html.Img(src=logo(BRANDS[b]["logo"]),
                                    style={"width": "16px", "height": "16px",
                                           "borderRadius": "3px", "backgroundColor": "white",
                                           "padding": "1px", "objectFit": "contain",
                                           "flexShrink": "0"}),
                                html.Span(b, style={"fontSize": "12px",
                                                    "fontWeight": "600", "color": "white"})
                            ]
                        ) for b in ALL_BRANDS
                    ]
                ),
                dcc.Store(id="brand-store", data=ALL_BRANDS),
                dcc.Dropdown(id="brand-filter",
                    options=[{"label": b, "value": b} for b in ALL_BRANDS],
                    value=ALL_BRANDS, multi=True, style={"display": "none"})
            ]),

            # CONTROLS
            html.Div(style={"display": "flex", "gap": "24px", "marginBottom": "20px",
                             "alignItems": "flex-start", "flexWrap": "wrap"}, children=[
                html.Div(style={"minWidth": "200px"}, children=[
                    lbl("Sentiment"),
                    dcc.Dropdown(id="sent-filter",
                        options=[{"label": s.capitalize(), "value": s} for s in ALL_SENTS],
                        value=ALL_SENTS, multi=True, clearable=False,
                        style={"fontSize": "13px"})
                ]),
                html.Div(style={"flex": "2", "minWidth": "300px"}, children=[
                    lbl("Date Range"),
                    html.Div(style={"display": "flex", "gap": "8px",
                                    "flexWrap": "wrap", "marginBottom": "8px"},
                        children=[
                            html.Button(label, id="preset-" + label.replace(" ", "-"),
                                n_clicks=0,
                                style={"padding": "5px 12px", "borderRadius": "6px",
                                       "border": f"1px solid {BORDER}",
                                       "backgroundColor": CARD, "color": SEC,
                                       "fontSize": "12px", "cursor": "pointer",
                                       "fontFamily": "Inter, Arial, sans-serif"})
                            for label in ["Last 7 days", "Last 14 days", "Last 30 days", "All time"]
                        ]
                    ),
                    dcc.DatePickerRange(id="date-filter",
                        start_date=DEFAULT_START, end_date=DEFAULT_END,
                        min_date_allowed=MIN_DATE, max_date_allowed=MAX_DATE,
                        display_format="MMM D, YYYY", minimum_nights=0)
                ]),
                html.Div(style={"paddingTop": "32px"}, children=[
                    dcc.Checklist(id="show-events",
                        options=[{"label": "  Show Tesla events", "value": "show"}],
                        value=["show"],
                        style={"color": SEC, "fontSize": "12px"})
                ])
            ]),

            # KPI STRIP
            html.Div(id="kpis",
                style={"display": "flex", "gap": "12px",
                       "marginBottom": "20px", "flexWrap": "wrap"}),

            # ROW 1: Trend full width
            card([
                lbl("Daily Sentiment Trend"),
                dcc.Graph(id="trend-chart", config={"displayModeBar": False})
            ]),

            # ROW 2: Brand avg + Mix + Volume
            html.Div(style={
                "display": "grid", "gridTemplateColumns": "1fr 1fr 1fr",
                "gap": "16px", "marginBottom": "16px", "alignItems": "start"
            }, children=[
                card([lbl("Brand Avg Sentiment"),
                      dcc.Graph(id="brand-chart", config={"displayModeBar": False})], mb="0"),
                card([lbl("Sentiment Mix by Brand"),
                      dcc.Graph(id="mix-chart", config={"displayModeBar": False})], mb="0"),
                card([lbl("Article Volume"),
                      dcc.Graph(id="vol-chart", config={"displayModeBar": False})], mb="0"),
            ]),

            # ROW 3: Topic full width
            card([
                lbl("Sentiment by Topic"),
                dcc.Graph(id="topic-chart", config={"displayModeBar": False})
            ]),

            # ROW 4: Articles table
            card([
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "alignItems": "center", "marginBottom": "12px"}, children=[
                    lbl("Recent Articles"),
                    dcc.Dropdown(id="table-brand",
                        options=[{"label": "All Brands", "value": "all"}] +
                                [{"label": b, "value": b} for b in ALL_BRANDS],
                        value="all", clearable=False,
                        style={"width": "180px", "fontSize": "12px"})
                ]),
                dash_table.DataTable(
                    id="art-table",
                    columns=[
                        {"name": "Date",      "id": "published_at"},
                        {"name": "Brand",     "id": "brand"},
                        {"name": "Source",    "id": "source"},
                        {"name": "Headline",  "id": "title"},
                        {"name": "Sentiment", "id": "sentiment_label"},
                        {"name": "Score",     "id": "compound"},
                    ],
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": BG, "color": SEC, "fontWeight": "600",
                        "fontSize": "11px", "letterSpacing": "0.05em",
                        "textTransform": "uppercase", "border": "none",
                        "borderBottom": f"1px solid {BORDER}", "padding": "8px 12px"
                    },
                    style_cell={
                        "backgroundColor": CARD, "color": PRI, "fontSize": "13px",
                        "padding": "10px 12px", "border": "none",
                        "borderBottom": f"1px solid {GRID}", "maxWidth": "320px",
                        "overflow": "hidden", "textOverflow": "ellipsis",
                        "fontFamily": "Inter, Arial, sans-serif"
                    },
                    style_data_conditional=[
                        {"if": {"row_index": "odd"}, "backgroundColor": BG},
                        {"if": {"filter_query": '{sentiment_label} = "positive"',
                                "column_id": "sentiment_label"},
                         "color": POS, "fontWeight": "600"},
                        {"if": {"filter_query": '{sentiment_label} = "negative"',
                                "column_id": "sentiment_label"},
                         "color": NEG, "fontWeight": "600"},
                        {"if": {"filter_query": '{sentiment_label} = "neutral"',
                                "column_id": "sentiment_label"},
                         "color": NEU},
                    ],
                    sort_action="native",
                )
            ], mb="0")
        ])
    ]
)

# =============================================================================
# CALLBACKS
# =============================================================================

# Date presets
@app.callback(
    [Output("date-filter", "start_date"), Output("date-filter", "end_date")],
    [Input("preset-Last-7-days",  "n_clicks"),
     Input("preset-Last-14-days", "n_clicks"),
     Input("preset-Last-30-days", "n_clicks"),
     Input("preset-All-time",     "n_clicks")],
    prevent_initial_call=True
)
def set_preset(n7, n14, n30, nall):
    ctx = dash.callback_context
    if not ctx.triggered:
        return DEFAULT_START, DEFAULT_END
    btn = ctx.triggered[0]["prop_id"].split(".")[0]
    if btn == "preset-Last-7-days":
        return (MAX_DATE - timedelta(days=7)),  MAX_DATE
    elif btn == "preset-Last-14-days":
        return (MAX_DATE - timedelta(days=14)), MAX_DATE
    elif btn == "preset-Last-30-days":
        return (MAX_DATE - timedelta(days=30)), MAX_DATE
    else:
        return MIN_DATE, MAX_DATE


# Brand pill toggle
@app.callback(
    [Output("brand-filter", "value"), Output("brand-store", "data")] +
    [Output("pill-" + b.replace(" ", "-"), "style") for b in ALL_BRANDS],
    [Input("pill-" + b.replace(" ", "-"), "n_clicks") for b in ALL_BRANDS],
    [State("brand-store", "data")]
)
def toggle_pills(*args):
    current = list(args[len(ALL_BRANDS)])
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["value"]:
        tid = ctx.triggered[0]["prop_id"].split(".")[0]
        for b in ALL_BRANDS:
            if "pill-" + b.replace(" ", "-") == tid:
                if b in current and len(current) > 1:
                    current.remove(b)
                elif b not in current:
                    current.append(b)
                break
    styles = []
    for b in ALL_BRANDS:
        active = b in current
        styles.append({
            "display": "flex", "alignItems": "center", "gap": "7px",
            "padding": "7px 14px", "borderRadius": "999px",
            "border": f"1.5px solid {BRANDS[b]['color'] if active else BORDER}",
            "backgroundColor": BRANDS[b]["color"] if active else "#F9FAFB",
            "cursor": "pointer", "userSelect": "none", "transition": "all 0.15s"
        })
    return [current, current] + styles


# KPIs
@app.callback(
    [Output("kpis", "children"), Output("last-updated", "children")],
    [Input("brand-filter", "value"), Input("sent-filter", "value"),
     Input("date-filter", "start_date"), Input("date-filter", "end_date"),
     Input("refresh-btn", "n_clicks")]
)
def update_kpis(brands, sents, start, end, n):
    if n > 0:
        global articles, tesla_events
        articles, tesla_events = load_data()
    f     = get_filtered(brands, sents, start, end)
    total = len(f)
    pp    = round(len(f[f["sentiment_label"] == "positive"]) / total * 100, 1) if total else 0
    np_   = round(len(f[f["sentiment_label"] == "negative"]) / total * 100, 1) if total else 0
    avg   = round(f["compound"].mean(), 3) if total else 0
    top   = f.groupby("brand")["compound"].mean().idxmax() if total else "—"

    def kpi(lbl_text, val, color=PRI):
        return html.Div(style={
            "flex": "1", "minWidth": "140px", "backgroundColor": CARD,
            "border": f"1px solid {BORDER}", "borderRadius": "8px", "padding": "16px 20px"
        }, children=[
            html.P(lbl_text, style={"color": SEC, "fontSize": "11px", "fontWeight": "600",
                                    "letterSpacing": "0.06em", "textTransform": "uppercase",
                                    "margin": "0 0 6px"}),
            html.Span(val, style={"fontSize": "26px", "fontWeight": "700", "color": color})
        ])

    return [
        kpi("Articles",  f"{total:,}"),
        kpi("Positive",  f"{pp}%",  POS),
        kpi("Negative",  f"{np_}%", NEG),
        kpi("Avg Score", str(avg),  ACCENT),
        kpi("Top Brand", top,       BRANDS.get(top, {}).get("color", PRI)),
    ], f"Updated {pd.Timestamp.now().strftime('%b %d, %H:%M')}"


# Trend chart
@app.callback(
    Output("trend-chart", "figure"),
    [Input("brand-filter", "value"), Input("date-filter", "start_date"),
     Input("date-filter", "end_date"), Input("show-events", "value")]
)
def trend_chart(brands, start, end, show_ev):
    raw = get_filtered(brands, ALL_SENTS, start, end).copy()
    raw["date"] = raw["published_at"].dt.normalize()
    f = raw.groupby(["brand", "date"])["compound"].mean().reset_index()
    f.columns = ["brand", "date", "avg_compound"]
    f["date"] = pd.to_datetime(f["date"]).dt.normalize()

    fig = go.Figure()
    for b in brands:
        d = f[f["brand"] == b].sort_values("date")
        if len(d) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=d["date"], y=d["avg_compound"],
            mode="lines", name=b,
            line=dict(color=BRANDS[b]["color"], width=2.5)
        ))

    if show_ev and "show" in show_ev:
        evs = tesla_events[
            (tesla_events["event_date"] >= pd.Timestamp(start)) &
            (tesla_events["event_date"] <= pd.Timestamp(end))
        ]
        for i, (_, ev) in enumerate(evs.iterrows()):
            ds = str(ev["event_date"])[:10]
            fig.add_shape(type="line", x0=ds, x1=ds, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color="#F59E0B", width=1, dash="dash"))
            xshift = -60 if i % 2 == 0 else 60
            fig.add_annotation(
                x=ds, y=-0.18, yref="paper",
                text=ev["title"][:28],
                showarrow=False,
                font=dict(color="#92400E", size=9),
                textangle=25, yanchor="top",
                xanchor="center", xshift=xshift,
                bgcolor="rgba(0,0,0,0)", borderwidth=0
            )

    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    fig = base_fig(fig, height=340, b_margin=100)
    fig.update_layout(
        hovermode="x unified",
        yaxis_title="Avg Compound Score",
        legend=dict(bgcolor=CARD, bordercolor=BORDER, borderwidth=1,
                    font=dict(color=PRI, size=11), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    return fig


# Brand avg sentiment
@app.callback(
    Output("brand-chart", "figure"),
    [Input("brand-filter", "value"), Input("date-filter", "start_date"),
     Input("date-filter", "end_date")]
)
def brand_chart(brands, start, end):
    f  = get_filtered(brands, ALL_SENTS, start, end)
    sm = f.groupby("brand")["compound"].mean().reset_index()
    sm.columns = ["brand", "avg"]
    sm = sm.sort_values("avg")
    fig = go.Figure(go.Bar(
        x=sm["avg"], y=sm["brand"], orientation="h",
        marker_color=[BRANDS[b]["color"] for b in sm["brand"]],
        marker_opacity=0.85,
        text=sm["avg"].round(3), textposition="outside",
        textfont=dict(size=11, color=SEC),
    ))
    fig.add_vline(x=0, line_color=BORDER, line_width=1)
    fig = base_fig(fig, height=max(180, len(sm) * 48))
    fig.update_layout(showlegend=False,
        xaxis=dict(range=[-0.6, 0.6], gridcolor=GRID,
                   tickfont=dict(color=SEC, size=11)))
    return fig


# Sentiment mix
@app.callback(
    Output("mix-chart", "figure"),
    [Input("brand-filter", "value"), Input("date-filter", "start_date"),
     Input("date-filter", "end_date")]
)
def mix_chart(brands, start, end):
    f  = get_filtered(brands, ALL_SENTS, start, end)
    bd = f.groupby(["brand", "sentiment_label"]).size().reset_index(name="count")
    bd["pct"] = (
        bd["count"] / bd.groupby("brand")["count"].transform("sum") * 100
    ).round(1)
    fig = go.Figure()
    for sent in ["positive", "neutral", "negative"]:
        d = bd[bd["sentiment_label"] == sent]
        fig.add_trace(go.Bar(
            name=sent.capitalize(), x=d["brand"], y=d["pct"],
            marker_color=SENT_CLR[sent], marker_opacity=0.85,
            text=d["pct"].astype(str) + "%", textposition="inside",
            textfont=dict(size=10, color="white")
        ))
    fig = base_fig(fig, height=max(220, len(brands) * 48))
    fig.update_layout(barmode="stack",
        yaxis=dict(ticksuffix="%", gridcolor=GRID),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig


# Article volume
@app.callback(
    Output("vol-chart", "figure"),
    [Input("brand-filter", "value"), Input("sent-filter", "value"),
     Input("date-filter", "start_date"), Input("date-filter", "end_date")]
)
def vol_chart(brands, sents, start, end):
    f   = get_filtered(brands, sents, start, end)
    vol = f.groupby("brand").size().reset_index(name="count")
    fig = go.Figure(go.Bar(
        x=vol["brand"], y=vol["count"],
        marker_color=[BRANDS[b]["color"] for b in vol["brand"]],
        marker_opacity=0.85,
        text=vol["count"], textposition="outside",
        textfont=dict(size=11, color=SEC),
    ))
    fig = base_fig(fig, height=max(220, len(vol) * 48))
    fig.update_layout(showlegend=False, yaxis=dict(gridcolor=GRID))
    return fig


# Topic sentiment
@app.callback(
    Output("topic-chart", "figure"),
    [Input("brand-filter", "value"), Input("date-filter", "start_date"),
     Input("date-filter", "end_date")]
)
def topic_chart(brands, start, end):
    f  = get_filtered(brands, ALL_SENTS, start, end)
    qt = f.groupby("query_type")["compound"].mean().reset_index()
    qt.columns = ["topic", "avg"]
    qt = qt.sort_values("avg")
    qt["color"] = qt["avg"].apply(
        lambda x: POS if x >= 0.05 else NEG if x <= -0.05 else NEU)
    fig = go.Figure(go.Bar(
        x=qt["avg"], y=qt["topic"], orientation="h",
        marker_color=qt["color"].tolist(), marker_opacity=0.85,
        text=qt["avg"].round(3), textposition="outside",
        textfont=dict(size=10, color=SEC),
    ))
    fig.add_vline(x=0, line_color=BORDER, line_width=1)
    fig = base_fig(fig, height=max(320, len(qt) * 36))
    fig.update_layout(showlegend=False,
        xaxis=dict(range=[-0.6, 0.6], gridcolor=GRID,
                   tickfont=dict(color=SEC, size=11)))
    return fig


# Articles table
@app.callback(
    Output("art-table", "data"),
    [Input("brand-filter", "value"), Input("sent-filter", "value"),
     Input("date-filter", "start_date"), Input("date-filter", "end_date"),
     Input("table-brand", "value")]
)
def art_table(brands, sents, start, end, tb):
    f = get_filtered(brands, sents, start, end).copy()
    if tb != "all":
        f = f[f["brand"] == tb]
    # Sort by actual timestamp BEFORE formatting so order is correct
    f = f.sort_values("published_at", ascending=False)
    f["published_at"] = f["published_at"].dt.strftime("%b %d, %Y")
    return f[["published_at", "brand", "source", "title",
              "sentiment_label", "compound"]].head(200).to_dict("records")


if __name__ == "__main__":
    app.run(debug=True)
