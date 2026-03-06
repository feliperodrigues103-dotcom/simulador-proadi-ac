import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import date
from PIL import Image # Nova biblioteca para tratar a logo
import io

# 1. Configurações de Identidade Visual e CSS
st.set_page_config(page_title="Simulador PROADI - A.C.Camargo", layout="wide")

MEDIUM_SPRING_GREEN = "#00FA9A"

st.markdown(f"""
    <style>
    .main {{ background-color: #0e1117; }}
    :root {{ --primary-color: {MEDIUM_SPRING_GREEN} !important; }}
    
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

# 3. Função PDF Corrigida (Tratamento de Imagem)
def gerar_pdf(df, total_val, total_h):
    pdf = FPDF()
    pdf.add_page()
    
    # Tenta inserir a logo de forma robusta
    if os.path.exists("ac-camargo.png"):
        try:
            # Abrimos com Pillow para garantir que o formato seja aceito
            img = Image.open("ac-camargo.png")
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # Salvamos uma versão temporária compatível
            img.save("logo_pdf.jpg", "JPEG")
            pdf.image("logo_pdf.jpg", x=85, y=10, w=40)
        except Exception as e:
            st.error(f"Erro ao processar logo no PDF: {e}")
    
    pdf.ln(30)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Simulacao de Custos - PROADI", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 10, f"Data da Emissao: {date.today().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    # Cabeçalho da Tabela
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
    pdf.set_font("Arial", 'B', 12)
    pdf.set_x(55)
    pdf.cell(100, 8, f"Volume Total de Horas: {formatar_numero_br(total_h)} h", 0, 1, 'L')
    pdf.set_x(55)
    pdf.cell(100, 8, f"Investimento Total Estimado: {formatar_moeda_br(total_val)}", 0, 1, 'L')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. CABEÇALHO DO APP ---
col_logo, col_titulo = st.columns([0.8, 4])

with col_logo:
    if os.path.exists("ac-camargo.png"):
        st.image("ac-camargo.png", width=120)

with col_titulo:
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Simulador de Alocação - PROADI")
    st.caption("A.C.Camargo Cancer Center | Controle de Custos")

st.divider()

# 5. Restante da Interface e Tabela
if 'proadi_data' not in st.session_state:
    st.session_state.proadi_data = pd.DataFrame([{"Cargo": "Selecione...", "Qtd": 1, "Horas Mensais": 220, "Meses": 1}])

df_editavel = st.data_editor(
    st.session_state.proadi_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Cargo": st.column_config.SelectboxColumn("Cargo", options=list(base_custos_hora.keys()), required=True),
        "Qtd": st.column_config.NumberColumn("Qtde", min_value=1, default=1),
        "Horas Mensais": st.column_config.NumberColumn("Hrs/Mes", min_value=1, max_value=220, default=220),
        "Meses": st.column_config.NumberColumn("Meses", min_value=1, default=1)
    }
)

def calc_c(row):
    if row["Cargo"] in ["Selecione...", None]: return 0.0
    return (base_custos_hora.get(row["Cargo"], 0) * (row["Horas Mensais"] or 0)) * (row["Meses"] or 0) * (row["Qtd"] or 0)

def calc_h(row):
    if row["Cargo"] in ["Selecione...", None]: return 0
    return (row["Horas Mensais"] or 0) * (row["Qtd"] or 0) * (row["Meses"] or 0)

df_editavel["Custo Total"] = df_editavel.apply(calc_c, axis=1)
df_editavel["Total Horas"] = df_editavel.apply(calc_h, axis=1)

t_val = df_editavel["Custo Total"].sum()
t_hrs = df_editavel["Total Horas"].sum()
t_ps = df_editavel["Qtd"].sum()

st.divider()
c1, c2, c3 = st.columns(3)
with c1: st.metric("Investimento Total", formatar_moeda_br(t_val))
with c2: st.metric("Total de Profissionais", f"{int(t_ps)} pessoas")
with c3: st.metric("Volume de Horas Totais", f"{formatar_numero_br(t_hrs)} h")

st.divider()
col_pdf, col_xlsx = st.columns(2)
with col_pdf:
    if t_val > 0:
        pdf_bytes = gerar_pdf(df_editavel, t_val, t_hrs)
        st.download_button("📄 Baixar Relatorio em PDF", data=pdf_bytes, file_name=f"Relatorio_PROADI_{date.today()}.pdf", mime="application/pdf", use_container_width=True)
with col_xlsx:
    csv_br = df_editavel.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
    st.download_button("📊 Exportar para Excel", data=csv_br, file_name=f"Simulacao_PROADI_{date.today()}.csv", mime="text/csv", use_container_width=True)