import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime

from utils.helpers import maturity_level, score_color, clean_text, top_gaps
from services.sheets_db import load_company_history
from exports.pdf_generator import generate_pdf

def render_dashboard():
    results = st.session_state.audit_results
    comp    = st.session_state.audit_company
    overall = results.get("overall_score", 0)
    maturity = maturity_level(overall)
    cat_name = results.get("project_category", "MINT")

    total_docs  = sum(len(p.get("documents", [])) for p in results.get("phases", {}).values())
    passed_docs = sum(1 for p in results.get("phases", {}).values() for d in p.get("documents", []) if d.get("pass"))
    pass_rate   = round(passed_docs / total_docs * 100, 1) if total_docs > 0 else 0

    current_ts   = results.get("audit_timestamp", "")
    history      = load_company_history(comp)
    older_audits = [h for h in history if h.get("audit_timestamp", "") < current_ts]
    
    if older_audits:
        benchmark_score = older_audits[0].get("overall_score", 0)
        delta_val       = f"{round(overall - benchmark_score, 1):+.1f}% vs last audit"
    else:
        benchmark_score = None
        delta_val       = "First audit"

    # ── Page Header ──
    st.markdown(f"""
    <div style="
        padding: 32px 0 24px 0;
        border-bottom: 1px solid rgba(99,179,237,0.08);
        margin-bottom: 32px;
    ">
        <div style="font-size:0.72rem; font-weight:600; letter-spacing:0.15em; color:#3B82F6; text-transform:uppercase; margin-bottom:6px;">
            Adherence Intelligence Report ({cat_name})
        </div>
        <div style="
            font-size: 2rem;
            font-weight: 700;
            color: #F1F5F9;
            font-family: 'Sora', sans-serif;
            letter-spacing: -0.02em;
        ">
            {comp}
        </div>
        <div style="font-size:0.82rem; color:#475569; margin-top:4px;">
            Detected Phase: <span style="color:#94A3B8; font-weight:500;">{results.get('detected_phase', 'N/A')}</span>
            &nbsp;&nbsp;·&nbsp;&nbsp;
            Project Type: <span style="color:#94A3B8; font-weight:500;">{results.get('project_type', 'N/A')}</span>
            &nbsp;&nbsp;·&nbsp;&nbsp;
            Generated: <span style="color:#94A3B8; font-weight:500;">{datetime.datetime.now().strftime("%B %d, %Y  %H:%M")}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Row ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Adherence", f"{overall}%", delta=delta_val)
    with col2:
        st.metric("Document Pass Rate", f"{pass_rate}%", delta=f"{passed_docs}/{total_docs} documents")
    with col3:
        st.metric("Maturity Level", maturity)
    with col4:
        st.metric(
            "Risk Classification",
            results.get("risk_level", "Unknown"),
            delta="Needs attention" if overall < 70 else "Within tolerance",
            delta_color="inverse"
        )

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Phase Pipeline ──
    st.markdown('<div class="mint-section-label">Phase Progression</div>', unsafe_allow_html=True)
    st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Lifecycle Adherence Pipeline</div>', unsafe_allow_html=True)

    phase_list  = list(results.get("phases", {}).items())
    if phase_list:
        phase_cols  = st.columns(len(phase_list))
        detected_ph = results.get("detected_phase", "")

        for i, (phase, info) in enumerate(phase_list):
            score  = info.get("score", 0)
            clr    = score_color(score)
            active = "phase-active" if phase == detected_ph else ""
            with phase_cols[i]:
                st.markdown(f"""
                <div class="phase-node {active}">
                    <div class="phase-node-label">{phase}</div>
                    <div class="phase-node-score" style="color:{clr};">{score}%</div>
                    <div style="font-size:0.68rem; color:#475569; margin-top:4px;">
                        {sum(1 for d in info.get('documents', []) if d.get('pass'))}/{len(info.get('documents', []))} docs
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Charts Row ──
    chart_col, gap_col = st.columns([1, 1], gap="large")

    with chart_col:
        st.markdown('<div class="mint-section-label">Performance Analysis</div>', unsafe_allow_html=True)
        st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Phase Score Distribution</div>', unsafe_allow_html=True)

        phase_names  = list(results.get("phases", {}).keys())
        phase_scores = [results["phases"][p].get("score", 0) for p in phase_names]

        if phase_names:
            bar_colors = [score_color(s) for s in phase_scores]
            fig_bar = go.Figure(go.Bar(
                x=phase_names,
                y=phase_scores,
                marker=dict(
                    color=bar_colors,
                    opacity=0.85,
                    line=dict(width=0)
                ),
                text=[f"{s}%" for s in phase_scores],
                textposition="outside",
                textfont=dict(color="#94A3B8", size=11, family="Sora"),
            ))
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Sora", color="#64748B", size=11),
                margin=dict(l=0, r=0, t=10, b=0),
                height=260,
                yaxis=dict(
                    range=[0, 115],
                    showgrid=True,
                    gridcolor="rgba(99,179,237,0.06)",
                    zeroline=False,
                    tickfont=dict(color="#475569"),
                    ticksuffix="%",
                ),
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(color="#64748B"),
                ),
                showlegend=False,
            )
            st.plotly_chart(fig_bar, width="stretch", config={"displayModeBar": False})

    with gap_col:
        st.markdown('<div class="mint-section-label">Action Required</div>', unsafe_allow_html=True)
        st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Priority Gap Register</div>', unsafe_allow_html=True)

        gaps = top_gaps(results)
        if not gaps:
            st.markdown("""
            <div style="
                padding: 32px;
                text-align: center;
                background: rgba(34,197,94,0.04);
                border: 1px solid rgba(34,197,94,0.15);
                border-radius: 10px;
            ">
                <div style="font-size:1.4rem; margin-bottom:8px;">✓</div>
                <div style="font-size:0.88rem; color:#4ADE80; font-weight:600;">All documents verified</div>
                <div style="font-size:0.78rem; color:#475569; margin-top:4px;">No adherence gaps detected.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for phase, doc, score, wrong_folder, actual_folder in gaps:
                severity_class = "gap-warning" if wrong_folder else "gap-critical"
                badge_class    = "badge-warn"   if wrong_folder else "badge-fail"
                badge_text     = "MISPLACED"    if wrong_folder else "MISSING"
                ai_comment     = "No diagnostic available."
                
                for d in results["phases"][phase]["documents"]:
                    if d["document"] == doc:
                        ai_comment = d.get("comment", ai_comment)
                        break
                
                clean_phase = str(phase).strip()
                clean_comment = str(ai_comment).replace('\n', ' ').strip()
                truncated = (clean_comment[:90] + "…") if len(clean_comment) > 90 else clean_comment
                
                found_html = f'&nbsp;·&nbsp; Found in: <span style="color:#FACC15;">{actual_folder}</span>' if wrong_folder else ''
                
                html_str = f"""
                <div class="gap-item {severity_class}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                        <div style="font-size:0.82rem; font-weight:600; color:#E2E8F0; flex:1; padding-right:8px;">{doc}</div>
                        <span class="mint-badge {badge_class}">{badge_text}</span>
                    </div>
                    <div style="font-size:0.72rem; color:#475569; margin-bottom:4px;">{clean_phase}{found_html}&nbsp;·&nbsp; Score: <span style="color:#94A3B8;">{score}%</span></div>
                    <div style="font-size:0.75rem; color:#64748B; line-height:1.5;">{truncated}</div>
                </div>
                """
                st.markdown(html_str, unsafe_allow_html=True)

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Master Ledger ──
    st.markdown('<div class="mint-section-label">Document Register</div>', unsafe_allow_html=True)
    st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Adherence Master Ledger</div>', unsafe_allow_html=True)

    table_data = []
    for phase, info in results.get("phases", {}).items():
        for d in info.get("documents", []):
            if d.get("is_bypassed"):
                loc_status = "PASS (Optional)"
            elif not d.get("actual_folder") or d.get("actual_folder") == "N/A":
                loc_status = "Missing"
            elif d.get("wrong_folder"):
                loc_status = f"Wrong folder ({d.get('actual_folder')})"
            else:
                loc_status = "Correct"

            table_data.append({
                "Phase":        phase,
                "Document":     d.get("document", "Unknown"),
                "Score":        d.get("score", 0),
                "Status":       "Pass" if d.get("pass") or d.get("is_bypassed") else "Fail",
                "Location":     loc_status,
                "Diagnostics":  d.get("comment", ""),
            })

    df_ledger = pd.DataFrame(table_data)
    if not df_ledger.empty:
        st.dataframe(
            df_ledger,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Health Score", format="%d%%", min_value=0, max_value=100
                ),
                "Status": st.column_config.TextColumn("Status"),
            },
            width="stretch",
            hide_index=True,
            height=380,
        )

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Export Section ──
    st.markdown('<div class="mint-section-label">Report Exports</div>', unsafe_allow_html=True)
    st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Download Artifacts</div>', unsafe_allow_html=True)

    ex_col1, ex_col2 = st.columns(2, gap="large")

    with ex_col1:
        st.markdown("""
        <div class="export-card">
            <div class="export-card-title">Executive PDF Report</div>
            <div class="export-card-desc">Full adherence brief with phase scores, ledger, and AI diagnostics. Formatted for board-level review.</div>
        </div>
        """, unsafe_allow_html=True)
        pdf_path = generate_pdf(comp, results)
        
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name=f"{clean_text(comp)}_{clean_text(cat_name).replace(' ', '_')}_Adherence_Report.pdf",
            mime="application/pdf",
            width="stretch",
        )

    with ex_col2:
        st.markdown("""
        <div class="export-card">
            <div class="export-card-title">Ledger CSV Export</div>
            <div class="export-card-desc">Machine-readable adherence ledger for integration with your data warehouse or project tracking systems.</div>
        </div>
        """, unsafe_allow_html=True)
        if not df_ledger.empty:
            csv_bytes = df_ledger.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Ledger CSV",
                data=csv_bytes,
                file_name=f"{clean_text(comp)}_Adherence_Ledger.csv",
                mime="text/csv",
                width="stretch",
            )

    st.markdown('<div style="height:48px;"></div>', unsafe_allow_html=True)