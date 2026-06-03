import streamlit as st

def render_landing():
    st.markdown("""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 100px 40px;
        text-align: center;
    ">
        <div style="
            font-size: 3.8rem;
            font-weight: 700;
            color: #F1F5F9;
            font-family: 'Sora', sans-serif;
            letter-spacing: -0.03em;
            line-height: 1.1;
            margin-bottom: 16px;
        ">
            Adherence Intelligence<br>
            <span style="color: #3B82F6;">Dashboard</span>
        </div>
        <div style="
            font-size: 1rem;
            color: #475569;
            max-width: 500px;
            line-height: 1.7;
            margin-bottom: 40px;
        ">
            Configure your engagement in the sidebar, select a data source,
            and initiate the audit to generate a full adherence report.
        </div>
        <div style="
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            justify-content: center;
        ">
            <div style="
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(99,179,237,0.1);
                border-radius: 10px;
                padding: 20px 28px;
                width: 180px;
            ">
                <div style="font-size:1.6rem; margin-bottom:8px;">◈</div>
                <div style="font-size:0.8rem; font-weight:600; color:#94A3B8;">Phase Detection</div>
            </div>
            <div style="
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(99,179,237,0.1);
                border-radius: 10px;
                padding: 20px 28px;
                width: 180px;
            ">
                <div style="font-size:1.6rem; margin-bottom:8px;">⬡</div>
                <div style="font-size:0.8rem; font-weight:600; color:#94A3B8;">AI Document Audit</div>
            </div>
            <div style="
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(99,179,237,0.1);
                border-radius: 10px;
                padding: 20px 28px;
                width: 180px;
            ">
                <div style="font-size:1.6rem; margin-bottom:8px;">▦</div>
                <div style="font-size:0.8rem; font-weight:600; color:#94A3B8;">Risk Classification</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)