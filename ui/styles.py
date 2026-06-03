def get_custom_css():
    return """
    /* ── Reset & Base ── */
    *, *::before, *::after { box-sizing: border-box; }

    html, body, .stApp {
        background-color: #080C14 !important;
        color: #CBD5E1 !important;
        font-family: 'Sora', sans-serif !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0C1221 0%, #080C14 100%) !important;
        border-right: 1px solid rgba(99,179,237,0.08) !important;
    }
    [data-testid="stSidebar"] * { font-family: 'Sora', sans-serif !important; }
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] .stFileUploader > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(99,179,237,0.15) !important;
        border-radius: 6px !important;
        color: #E2E8F0 !important;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stRadio label {
        color: #94A3B8 !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebar"] .stRadio > div { gap: 6px !important; }
    [data-testid="stSidebar"] .stRadio > div > label {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(99,179,237,0.1) !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        font-size: 0.85rem !important;
        color: #CBD5E1 !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] .stRadio > div > label:hover {
        border-color: rgba(99,179,237,0.35) !important;
        background: rgba(99,179,237,0.06) !important;
    }

    /* ── Primary Button ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%) !important;
        border: none !important;
        border-radius: 6px !important;
        color: #fff !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 0 20px rgba(37,99,235,0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 0 30px rgba(37,99,235,0.45) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(99,179,237,0.2) !important;
        border-radius: 6px !important;
        color: #94A3B8 !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.82rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: rgba(99,179,237,0.45) !important;
        color: #E2E8F0 !important;
    }

    /* ── Download Button ── */
    [data-testid="stDownloadButton"] > button {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(99,179,237,0.2) !important;
        border-radius: 6px !important;
        color: #94A3B8 !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.82rem !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        border-color: rgba(99,179,237,0.45) !important;
        color: #E2E8F0 !important;
        background: rgba(99,179,237,0.06) !important;
    }

    /* ── Metrics ── */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.025) !important;
        border: 1px solid rgba(99,179,237,0.1) !important;
        border-radius: 10px !important;
        padding: 20px 24px !important;
    }
    [data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-size: 0.72rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
    }
    [data-testid="stMetricValue"] {
        color: #F1F5F9 !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        font-family: 'Sora', sans-serif !important;
    }
    [data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(99,179,237,0.1) !important;
        border-radius: 8px !important;
        margin-bottom: 6px !important;
    }
    [data-testid="stExpander"] summary {
        color: #CBD5E1 !important;
        font-size: 0.85rem !important;
    }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(99,179,237,0.1) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* ── Divider ── */
    hr { border-color: rgba(99,179,237,0.08) !important; }

    /* ── Progress bar ── */
    [data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, #1D4ED8, #38BDF8) !important;
    }

    /* ── Status box ── */
    [data-testid="stStatus"] {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(99,179,237,0.12) !important;
        border-radius: 10px !important;
    }

    /* ── Plotly chart background ── */
    .js-plotly-plot, .plotly { background: transparent !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(99,179,237,0.2); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,179,237,0.4); }

    /* ── Custom card classes ── */
    .mint-section-label {
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #3B82F6;
        margin-bottom: 8px;
    }
    .mint-section-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: #F1F5F9;
        margin-bottom: 0;
    }
    .mint-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .badge-pass   { background: rgba(34,197,94,0.12);  color: #4ADE80; border: 1px solid rgba(34,197,94,0.25); }
    .badge-fail   { background: rgba(239,68,68,0.12);  color: #F87171; border: 1px solid rgba(239,68,68,0.25); }
    .badge-warn   { background: rgba(234,179,8,0.12);  color: #FACC15; border: 1px solid rgba(234,179,8,0.25); }

    .phase-node {
        text-align: center;
        padding: 14px 10px;
        border-radius: 10px;
        border: 1px solid rgba(99,179,237,0.15);
        background: rgba(255,255,255,0.025);
        position: relative;
    }
    .phase-node-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #64748B;
        margin-bottom: 6px;
    }
    .phase-node-score {
        font-size: 1.4rem;
        font-weight: 700;
        font-family: 'Sora', sans-serif;
    }
    .phase-active { border-color: rgba(59,130,246,0.45) !important; background: rgba(59,130,246,0.06) !important; }

    .gap-item {
        padding: 14px 18px;
        border-radius: 8px;
        border-left: 3px solid;
        background: rgba(255,255,255,0.02);
        margin-bottom: 8px;
    }
    .gap-critical { border-left-color: #EF4444; }
    .gap-warning  { border-left-color: #F59E0B; }

    .sidebar-logo {
        font-size: 1.3rem;
        font-weight: 700;
        color: #F1F5F9;
        letter-spacing: -0.02em;
        font-family: 'Sora', sans-serif;
    }
    .export-card {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(99,179,237,0.1);
        border-radius: 10px;
        padding: 20px 24px;
    }
    .export-card-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: #F1F5F9;
        margin-bottom: 4px;
    }
    .export-card-desc {
        font-size: 0.75rem;
        color: #64748B;
        margin-bottom: 14px;
    }
    """