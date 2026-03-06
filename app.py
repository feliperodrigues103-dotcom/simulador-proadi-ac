import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import date
from PIL import Image
import plotly.express as px
import io

# 1. Configurações de Identidade Visual e CSS para Botões Vibrantes
st.set_page_config(page_title="Simulador PROADI - A.C.Camargo", layout="wide")

MEDIUM_SPRING_GREEN = "#00FA9A"

st.markdown(f"""
    <style>
    .main {{ background-color: #0e1117; }}
    :root {{ --primary-color: {MEDIUM_SPRING_GREEN} !important; }}
    .block-container {{ padding: 2rem 3rem; }}
    
    /* ESTILIZAÇÃO DOS BOTÕES PARA FICAREM VIBRANTES */
    .stButton>button, .stDownloadButton>button {{
        background-color: {MEDIUM_SPRING_GREEN} !important;
        color: #0e1117 !important; /* Texto escuro para contraste */
        font-weight: bold !important;
        opacity: 1 !important; /* Remove o efeito de 'apagado' */
        border: none !important;
        transition: 0.3s;
    }}
    
    .stButton>button:hover, .stDownloadButton>button:hover {{
        background-color: #00D181 !important; /* Tom um pouco mais escuro no hover */
        transform: scale(1.02);
    }}

    div[data-testid="stDataEditor"] div:focus-within {{
        border-color: {MEDIUM_SPRING_GREEN} !important;
        box-shadow: 0 0 0 1px {MEDIUM_SPRING_GREEN} !important;
    }}

    [data-testid="stMetric"] {{
        background-color: transparent !important;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
    }}
    
    [data-testid="stMetricValue"] {{
        color: {MEDIUM_SPRING_GREEN} !important;
        font-weight: bold !important;
    }}
    
    [data-testid="stMetricLabel"] {{ color: #ffffff !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE FORMATAÇÃO ---
def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_numero_br(valor):
    return f"{valor:,.0f}".replace(",", ".")

# 2. Base de Custos
base_custos_hora = {
    "ANALISTA PROJETOS II": 42.28,
    "PESQUISADOR III": 115.53,
    "ANALISTA PROJETOS III": 44.28,
    "COORDENADOR PROJETOS": 94.60,
    "GERENTE PROJETOS ASSISTENCIAIS": 183.46
}

# 3. Função PDF com Gráfico
def gerar_pdf(df, total_val, total_h, fig=None):
    pdf = FPDF()
    pdf.add_page()
    
    if os.path.exists("ac-camargo.png"):
        try:
            img = Image.open("ac-camargo.png")
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save("logo_pdf.jpg", "JPEG")
            pdf.image("logo_pdf.jpg", x=85, y=10, w=40)
            pdf.ln(30)
        except: pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Simulacao de Custos - PROADI", ln=True, align='C')
    pdf.ln(10)
    
    # Tabela
    pdf.set_fill_color(0, 125, 64)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 10, "Cargo", 1, 0, 'C', True)
    pdf.cell(20, 10, "Qtde", 1, 0, 'C', True)
    pdf.cell(35, 10, "Hrs/Mes", 1, 0, 'C', True)
    pdf.cell(30, 10, "Meses", 1, 0, 'C', True)
    pdf.cell(45, 10, "Total", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        if row["Cargo"] != "Selecione...":
            pdf.cell(60, 10, str(row["Cargo"]), 1)
            pdf.cell(20, 10, str(row["Qtd"]), 1, 0, 'C')
            pdf.cell(35, 10, str(row["Horas Mensais"]), 1, 0, 'C')
            pdf.cell(30, 10, str(row["Meses"]), 1, 0, 'C')
            pdf.cell(45, 10, formatar_moeda_br(row['Custo Total']), 1, 1, 'C')
    
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_x(55)
    pdf.cell(100, 8, f"Volume Total de Horas: {formatar_numero_br(total_h)} h", 0, 1, 'L')
    pdf.set_x(55)
    pdf.cell(100, 8, f"Investimento Total Estimado: {formatar_moeda_br(total_val)}", 0, 1, 'L')
    
    if fig:
        try:
            img_bytes = fig.to_image(format="png", width=800, height=400)
            with open("temp_chart.png", "wb") as f:
                f.write(img_bytes)
            pdf.ln(10)
            pdf.image("temp_chart.png", x=15, y=pdf.get_y(), w=180)
        except: pass

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, "Nota de Auditoria: Os calculos acima baseiam-se em uma jornada padrao de 220h mensais. Valores sujeitos a alteracao conforme politicas do A.C.Camargo Cancer Center.", align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. CABEÇALHO ---
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists("ac-camargo.png"):
        st.image("ac-camargo.png", width=150)

with col_titulo:
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Simulador de Alocação - PROADI")
    st.caption("A.C.Camargo Cancer Center | Controle de Custos")

st.divider()

if 'cenario_salvo' not in st.session_state:
    st.session_state.cenario_salvo = None

if st.button("💾 Salvar Cenário Atual para Comparação"):
    st.session_state.cenario_salvo = {'valor': 0.0}
    st.success("Cenário salvo!")

# 5. Tabela
if 'proadi_data' not in st.session_state:
    st.session_state.proadi_data = pd.DataFrame([{"Cargo": "Selecione...", "Qtd": 1, "Horas Mensais": 220, "Meses": 1}])

df_editavel = st.data_editor(
    st.session_state.proadi_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Cargo": st.column_config.SelectboxColumn("Cargo", options=list(base_custos_hora.keys()), required=True),
        "Qtd": st.column_config.NumberColumn("Qtde", min_value=1),
        "Horas Mensais": st.column_config.NumberColumn("Hrs/Mes", min_value=1, max_value=220),
        "Meses": st.column_config.NumberColumn("Meses", min_value=1)
    }
)

# Cálculos
def calc_c(row):
    if row["Cargo"] in ["Selecione...", None]: return 0.0
    v_hora = base_custos_hora.get(row["Cargo"], 0)
    return (v_hora * (row["Horas Mensais"] or 0)) * (row["Meses"] or 0) * (row["Qtd"] or 0)

df_editavel["Custo Total"] = df_editavel.apply(calc_c, axis=1)
t_val = df_editavel["Custo Total"].sum()
t_hrs = (df_editavel["Horas Mensais"].fillna(0) * df_editavel["Qtd"].fillna(0) * df_editavel["Meses"].fillna(0)).sum()
t_ps = df_editavel["Qtd"].fillna(0).sum()

if st.session_state.cenario_salvo is not None and st.session_state.cenario_salvo['valor'] == 0:
    st.session_state.cenario_salvo['valor'] = t_val

# 6. Métricas
st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    delta = None
    if st.session_state.cenario_salvo:
        diff = t_val - st.session_state.cenario_salvo['valor']
        delta = formatar_moeda_br(diff)
    st.metric("Investimento Total", formatar_moeda_br(t_val), delta=delta, delta_color="inverse")
with c2: st.metric("Total de Profissionais", f"{int(t_ps)} pessoas")
with c3: st.metric("Volume de Horas Totais", f"{formatar_numero_br(t_hrs)} h")

# 7. Gráfico
st.divider()
st.subheader("📊 Distribuição de Custos por Cargo")
st.write("Este gráfico ajuda a visualizar quais categorias profissionais possuem maior peso no orçamento do projeto PROADI.")

df_chart = df_editavel[df_editavel["Cargo"] != "Selecione..."].groupby("Cargo")["Custo Total"].sum().reset_index()
fig_global = None

if not df_chart.empty:
    fig_global = px.bar(df_chart, x="Cargo", y="Custo Total", text="Custo Total", color_discrete_sequence=[MEDIUM_SPRING_GREEN], template="plotly_dark")
    fig_global.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
    fig_global.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showticklabels=False, showgrid=False))
    st.plotly_chart(fig_global, use_container_width=True)
    if st.session_state.cenario_salvo:
        st.info(f"**Cenário Comparativo:** O valor salvo anteriormente era de {formatar_moeda_br(st.session_state.cenario_salvo['valor'])}.")
else:
    st.info("Preencha a tabela para gerar o gráfico.")

# --- 8. BOTÕES DE EXPORTAÇÃO (VIBRANTES E FIXOS) ---
st.divider()
col_pdf, col_xlsx = st.columns(2)

with col_pdf:
    pdf_bytes = gerar_pdf(df_editavel, t_val, t_hrs, fig_global)
    st.download_button(
        label="📄 Baixar Relatório em PDF",
        data=pdf_bytes,
        file_name=f"Relatorio_PROADI_{date.today()}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

with col_xlsx:
    csv_br = df_editavel.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
    st.download_button(
        label="📊 Exportar para Excel (CSV)",
        data=csv_br,
        file_name=f"Simulacao_PROADI_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )