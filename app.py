# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# --- Cores personalizadas ---
# Cor principal (Diamante Lapidado, da imagem)
BG_COLOR = "#EAE8E1" 
# Cor para elementos de texto principal (preto)
TEXT_COLOR = "#000000" 
# Cor para detalhes/muted text (cinza escuro)
MUTED_TEXT_COLOR = "#333333"
# Cor para linhas de tabela
TABLE_BORDER_COLOR = "#DCDCDC" # Um cinza mais claro para combinar com o fundo
# Cor para o fundo da sidebar (um cinza escuro para contraste)
SIDEBAR_BG = "#4A4A4A" 
# Cor dos cards internos (sombra sutil em vez de branco)
CARD_BG = f"rgba(0,0,0,0.03)" 

# ---------------------------
# CSS - Estilos da Página
# ---------------------------
st.set_page_config(page_title="Simulador Financeiro Modular", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    f"""
    <style>
    :root{{
        --g1: linear-gradient(90deg,#ff7a45,#ffc75f,#9acd32); /* Mantém gradiente existente */
        --card-bg: {CARD_BG}; /* Fundo dos cards principais */
        --sidebar-bg: {SIDEBAR_BG}; /* Fundo da sidebar */
        --text-color: {TEXT_COLOR};
        --muted-text-color: {MUTED_TEXT_COLOR};
        --table-border-color: {TABLE_BORDER_COLOR};
    }}
    
    /* --- Estilos Globais --- */
    .stApp {{ 
        background-color: {BG_COLOR}; 
        color: var(--text-color);
    }}
    
    /* --- Títulos e Subtítulos --- */
    .header-title, h1, h2, h3, h4, h5, h6 {{
        color: var(--text-color);
    }}
    .subhead {{ 
        color: var(--muted-text-color);
    }}

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg);
        color: white; /* Texto na sidebar geralmente mais claro */
    }}
    [data-testid="stSidebar"] .stMarkdown > div > div > strong {{
        color: white; /* Título principal da sidebar */
    }}
    [data-testid="stSidebar"] .stMarkdown > div > div > div {{
        color: rgba(255,255,255,0.8); /* Subtítulo da sidebar */
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5, [data-testid="stSidebar"] h6 {{
        color: white; /* Headers na sidebar */
    }}
    [data-testid="stSidebar"] label {{
        color: white; /* Labels dos inputs na sidebar */
    }}
    /* Ajustes para inputs na sidebar */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] .stSelectbox {{
        background-color: rgba(255,255,255,0.1);
        color: white;
    }}
    [data-testid="stSidebar"] input[type="number"], 
    [data-testid="stSidebar"] .stSelectbox > div > div > div {{
        color: white; /* Garante que o texto de números e selects na sidebar seja branco */
    }}
    /* Setas dos number_input */
    [data-testid="stSidebar"] button[kind="secondary"] {{
        background-color: rgba(255,255,255,0.1);
        color: white;
    }}
    /* Botões "Adicionar" e "Remover" na sidebar */
    [data-testid="stSidebar"] .stButton > button {{
        background-color: #666; /* Botões escuros na sidebar */
        color: white;
        border: none;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: #777;
        color: white;
    }}


    /* --- Cartões KPI --- */
    .kpi-card {{
        background: var(--card-bg);
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        border-left: 6px solid rgba(0,0,0,0.04);
        color: var(--text-color); /* Garante texto preto */
    }}
    .kpi-card .small-muted {{
        color: var(--muted-text-color); /* Garante texto cinza */
    }}
    .kpi-gradient {{
        padding: 12px; border-radius: 12px;
        background: var(--g1);
        color: white; /* Texto dentro do gradiente continua branco para contraste */
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    }}
    .kpi-gradient .small-muted {{
        color: rgba(255,255,255,0.8); /* Texto menor no gradiente mais claro */
    }}

    /* --- Pills (tags) --- */
    .pill {{ 
        display:inline-block; 
        padding:6px 10px; 
        border-radius:999px; 
        font-size:12px; 
        background:rgba(0,0,0,0.1); /* Fundo do 'pill' mais sutil e escuro */
        color:#b94a00; /* Cor do texto da pill */
        border:1px solid rgba(0,0,0,0.03); 
    }}

    /* --- Tabelas (st.table e st.dataframe) --- */
    table, th, td {{ 
        color: var(--text-color) !important; /* Força o texto da tabela a ser preto */
        border-bottom: 1px solid var(--table-border-color); /* Linhas da tabela em cinza */
    }}
    thead th {{
        border-bottom: 2px solid var(--table-border-color); /* Cabeçalho da tabela com linha mais grossa */
    }}
    /* Para o st.dataframe especificamente */
    .stDataFrame > div > div > div > div > div > div {{
        background-color: transparent !important; /* Remove fundo branco do dataframe */
        color: var(--text-color) !important;
    }}
    .stDataFrame thead th {{
        background-color: rgba(0,0,0,0.05) !important; /* Leve sombreamento no cabeçalho do dataframe */
        color: var(--text-color) !important;
    }}
    .stDataFrame tbody tr {{
        background-color: transparent !important;
    }}
    .stDataFrame tbody tr:nth-child(even) {{
        background-color: rgba(0,0,0,0.02) !important; /* Linhas zebradas sutis */
    }}
    .stDataFrame .css-x1y8h7 {{ /* Ícone de ordenação */
        color: var(--text-color) !important;
    }}

    /* --- Elementos de formulário (inputs, selects, sliders) --- */
    label {{
        color: var(--text-color); /* Labels dos inputs */
    }}
    /* Estilo para inputs e selects no corpo principal */
    .stNumberInput, .stSelectbox {{
        background-color: var(--card-bg); /* Usa o card-bg para inputs */
        border-radius: 8px;
        padding: 5px;
    }}
    .stNumberInput input, .stSelectbox > div > div > div {{
        color: var(--text-color);
    }}
    /* Cor dos botões de incremento/decremento dos number_input */
    .stNumberInput button[kind="secondary"] {{
        background-color: rgba(0,0,0,0.1);
        color: var(--text-color);
    }}
    </style>
    """, unsafe_allow_html=True
)

# ---------------------------
# Funções Utilitárias
# ---------------------------
def fmt_brl(v):
    return f"R$ {v:,.2f}"

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Simulacao')
    return output.getvalue()

# ---------------------------
# Lógica da Simulação
# ---------------------------
def simulate(
    years: int,
    modules_init: int,
    cost_per_module: float,
    cost_correction_rate: float,
    revenue_per_module: float,
    maintenance_per_module: float,
    rent_value: float,
    rent_start_month: int,
    aportes: list,
    retiradas: list,
    fundos: list,
):
    months = years * 12
    rows = []
    
    modules = modules_init
    caixa = 0.0
    investimento_total = modules * cost_per_module
    fundo_ac = 0.0
    retiradas_ac = 0.0
    custo_modulo_atual = cost_per_module
    aportes_map = {a["mes"]: a.get("valor", 0.0) for a in aportes}

    for m in range(1, months + 1):
        receita = modules * revenue_per_module
        manut = modules * maintenance_per_module
        aluguel = rent_value if m >= rent_start_month else 0.0
        novos_modulos_comprados = 0

        aporte_mes = aportes_map.get(m, 0.0)
        caixa += aporte_mes
        investimento_total += aporte_mes

        caixa += receita - manut - aluguel

        fundo_mes_total = 0.0
        if caixa > 0:
            for f in fundos:
                if m >= f["mes"]:
                    valor_fundo = caixa * (f["percentual"] / 100.0)
                    caixa -= valor_fundo
                    fundo_mes_total += valor_fundo
        fundo_ac += fundo_mes_total
        
        retirada_mes_total = 0.0
        if caixa > 0:
            for r in retiradas:
                if m >= r["mes"]:
                    valor_retirada = caixa * (r["percentual"] / 100.0)
                    caixa -= valor_retirada
                    retirada_mes_total += valor_retirada
        retiradas_ac += retirada_mes_total

        if m % 12 == 0:
            if caixa >= custo_modulo_atual:
                novos_modulos_comprados = int(caixa // custo_modulo_atual)
                custo_da_compra = novos_modulos_comprados * custo_modulo_atual
                caixa -= custo_da_compra
                modules += novos_modulos_comprados
                investimento_total += custo_da_compra
            custo_modulo_atual *= (1 + cost_correction_rate / 100.0)

        rows.append({
            "Mês": m, "Ano": (m - 1) // 12 + 1, "Módulos Ativos": modules,
            "Receita": receita, "Manutenção": manut, "Aluguel": aluguel,
            "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total,
            "Retirada (Mês)": retirada_mes_total, "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Custo Módulo (Próx. Ano)": custo_modulo_atual if m % 12 == 0 else np.nan,
        })

    df = pd.DataFrame(rows)
    df["Custo Módulo (Próx. Ano)"] = df["Custo Módulo (Próx. Ano)"].ffill()
    return df

# ---------------------------
# Sidebar - Entradas do Usuário
# ---------------------------
with st.sidebar:
    st.markdown("<div style='display:flex; gap:10px; align-items:center'><div style='width:48px;height:48px;border-radius:10px;background:var(--g1)'></div><div><strong>Simulador Modular</strong><div style='font-size:12px;'>Projeção com reinvestimento</div></div></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.header("1. Configuração Geral")
    years = st.slider("Horizonte de investimento (anos)", 1, 30, 10)
    
    col1, col2 = st.columns(2)
    with col1:
        modules_init = st.number_input("Módulos iniciais", min_value=1, value=5, step=1)
        cost_per_module = st.number_input("Custo inicial por módulo (R$)", min_value=0.0, value=100_000.0, step=1000.0, format="%.2f")
    with col2:
        revenue_per_module = st.number_input("Receita mensal/módulo (R$)", min_value=0.0, value=4_500.0, step=100.0, format="%.2f")
        maintenance_per_module = st.number_input("Manutenção mensal/módulo (R$)", min_value=0.0, value=1_500.0, step=50.0, format="%.2f")
    
    cost_correction_rate = st.number_input("Correção anual do custo do módulo (%)", min_value=0.0, value=5.0, step=0.5, format="%.1f", help="Percentual de aumento do custo para compra de novos módulos a cada ano.")

    st.markdown("---")
    st.header("2. Custos Fixos")
    rent_value = st.number_input("Aluguel mensal do terreno (R$)", min_value=0.0, value=3_000.0, step=50.0, format="%.2f")
    rent_start_month = st.number_input("Mês de início do aluguel", min_value=1, max_value=years*12, value=6, step=1)

    st.markdown("---")
    st.header("3. Eventos Financeiros")
    
    if "aportes" not in st.session_state:
        st.session_state.aportes = [{"mes": 3, "valor": 50_000.0}]
    if "retiradas" not in st.session_state:
        st.session_state.retiradas = [{"mes": 25, "percentual": 30.0}]
    if "fundos" not in st.session_state:
        st.session_state.fundos = [{"mes": 25, "percentual": 10.0}]

    with st.expander("Aportes (investimentos pontuais)"):
        for i, a in enumerate(st.session_state.aportes):
            c1, c2, c3 = st.columns([1,2,1])
            a["mes"] = c1.number_input(f"Mês (aporte #{i+1})", 1, years*12, a["mes"], key=f"ap_mes_{i}")
            a["valor"] = c2.number_input(f"Valor (R$) (aporte #{i+1})", 0.0, value=a["valor"], step=1000.0, key=f"ap_val_{i}", format="%.2f")
            if c3.button("🗑️", key=f"ap_rem_{i}"):
                st.session_state.aportes.pop(i); st.rerun()
        if st.button("Adicionar Aporte"):
            st.session_state.aportes.append({"mes": 1, "valor": 10000.0}); st.rerun()

    with st.expander("Retiradas (% sobre o caixa mensal)"):
        for i, r in enumerate(st.session_state.retiradas):
            c1, c2, c3 = st.columns([1,2,1])
            r["mes"] = c1.number_input(f"Mês início (retirada #{i+1})", 1, years*12, r["mes"], key=f"re_mes_{i}")
            r["percentual"] = c2.number_input(f"% (retirada #{i+1})", 0.0, 100.0, r["percentual"], step=1.0, key=f"re_pct_{i}", format="%.1f")
            if c3.button("🗑️", key=f"re_rem_{i}"):
                st.session_state.retiradas.pop(i); st.rerun()
        if st.button("Adicionar Retirada"):
            st.session_state.retiradas.append({"mes": 1, "percentual": 10.0}); st.rerun()

    with st.expander("Fundos de Reserva (% sobre o caixa mensal)"):
        for i, f in enumerate(st.session_state.fundos):
            c1, c2, c3 = st.columns([1,2,1])
            f["mes"] = c1.number_input(f"Mês início (fundo #{i+1})", 1, years*12, f["mes"], key=f"fu_mes_{i}")
            f["percentual"] = c2.number_input(f"% do caixa (fundo #{i+1})", 0.0, 100.0, f["percentual"], step=1.0, key=f"fu_pct_{i}", format="%.1f")
            if c3.button("🗑️", key=f"fu_rem_{i}"):
                st.session_state.fundos.pop(i); st.rerun()
        if st.button("Adicionar Fundo"):
            st.session_state.fundos.append({"mes": 1, "percentual": 5.0}); st.rerun()

# ---------------------------
# Conteúdo Principal
# ---------------------------
df = simulate(
    years=years, modules_init=modules_init, cost_per_module=cost_per_module,
    cost_correction_rate=cost_correction_rate, revenue_per_module=revenue_per_module,
    maintenance_per_module=maintenance_per_module, rent_value=rent_value,
    rent_start_month=rent_start_month, aportes=st.session_state.aportes,
    retiradas=st.session_state.retiradas, fundos=st.session_state.fundos,
)

st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center'><div><h1 class='header-title'>Simulador de Módulos — Projeção de {years} Anos</h1><div class='subhead'>Análise de fluxo de caixa com reinvestimento anual automático.</div></div><div><span class='pill'>✨ Fundo em %</span></div></div>", unsafe_allow_html=True)

final = df.iloc[-1]
kpi_cols = st.columns(4)
kpi_cols[0].markdown(f"<div class='kpi-card'><div class='small-muted'>Investimento Inicial</div><div style='font-size:20px;font-weight:700'>{fmt_brl(modules_init * cost_per_module)}</div></div>", unsafe_allow_html=True)
kpi_cols[1].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Módulos Finais</div><div style='font-size:20px;font-weight:700'>{int(final['Módulos Ativos'])}</div></div>", unsafe_allow_html=True)
kpi_cols[2].markdown(f"<div class='kpi-card'><div class='small-muted'>Retiradas Acumuladas</div><div style='font-size:20px;font-weight:700'>{fmt_brl(final['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
kpi_cols[3].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Caixa Final</div><div style='font-size:20px;font-weight:700'>{fmt_brl(final['Caixa (Final Mês)'])}</div></div>", unsafe_allow_html=True)

st.markdown("---")

colA, colB = st.columns([2, 1])
with colA:
    st.subheader("Evolução Financeira ao Longo do Tempo")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Caixa (Final Mês)"], mode="lines", name="Caixa", line=dict(color="#ff7a45", width=2.5)))
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Fundo Acumulado"], mode="lines", name="Fundo Acumulado", line=dict(color="#9acd32", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Retiradas Acumuladas"], mode="lines", name="Retiradas Acumuladas", line=dict(color="#ffc75f", width=1.5)))
    
    # Atualiza layout do gráfico para corresponder ao tema
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10), 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)', # Fundo do gráfico transparente
        paper_bgcolor='rgba(0,0,0,0)', # Fundo da área do gráfico transparente
        font=dict(color=TEXT_COLOR) # Cor do texto do gráfico
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)

    st.plotly_chart(fig, use_container_width=True)

with colB:
    st.subheader("Evolução dos Módulos")
    fig_mod = go.Figure()
    fig_mod.add_trace(go.Scatter(x=df["Mês"], y=df["Módulos Ativos"], mode="lines", name="Módulos", line=dict(color="#2a9d8f", width=2.5), fill='tozeroy'))
    # Atualiza layout do gráfico para corresponder ao tema
    fig_mod.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=TEXT_COLOR)
    )
    fig_mod.update_xaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)
    fig_mod.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)

    st.plotly_chart(fig_mod, use_container_width=True)

st.markdown("---")

st.subheader("Resumo Consolidado por Ponto no Tempo")
col_res1, col_res2, col_res3 = st.columns([1, 1, 2])

with col_res1:
    summary_year = st.number_input("Selecione o ano", 1, years, min(5, years), 1)
with col_res2:
    summary_month = st.selectbox("E o mês", list(range(1, 13)), index=11)

def get_summary_for_point_in_time(df, year, month):
    target_month = (year - 1) * 12 + month
    if target_month > len(df):
        target_month = len(df)
        
    data = df[df["Mês"] == target_month].iloc[0]
    actual_year = (data['Mês'] - 1) // 12 + 1
    actual_month = (data['Mês'] - 1) % 12 + 1
    
    return {
        "Marco": f"Ano {actual_year}, Mês {actual_month}",
        "Módulos": f"{int(data['Módulos Ativos'])}",
        "Caixa": fmt_brl(data['Caixa (Final Mês)']),
        "Fundo": fmt_brl(data['Fundo Acumulado']),
        "Retiradas": fmt_brl(data['Retiradas Acumuladas']),
        "Invest. Total": fmt_brl(data['Investimento Total Acumulado'])
    }

with col_res3:
    summary_data = []
    summary_data.append(get_summary_for_point_in_time(df, summary_year, summary_month))
    
    final_month_in_sim = years * 12
    selected_month_in_sim = (summary_year - 1) * 12 + summary_month
    if selected_month_in_sim != final_month_in_sim:
        summary_data.append(get_summary_for_point_in_time(df, years, 12))
    
    summary_df = pd.DataFrame(summary_data).set_index("Marco")
    st.table(summary_df) # st.table usa o CSS global

st.markdown("---")

st.subheader("Tabela Completa da Simulação")
with st.expander("Clique para expandir e ver todos os dados mensais"):
    df_display = df.copy()
    format_cols = [
        "Receita", "Manutenção", "Aluguel", "Aporte", "Fundo (Mês)", 
        "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado", 
        "Fundo Acumulado", "Retiradas Acumuladas", "Custo Módulo (Próx. Ano)"
    ]
    for col in format_cols:
        df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
    st.dataframe(df_display, use_container_width=True) # st.dataframe usa o CSS global para suas células

excel_bytes = df_to_excel_bytes(df)
st.download_button(
    "📥 Baixar Relatório Completo (Excel)",
    data=excel_bytes,
    file_name=f"simulacao_modulos_{years}_anos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
