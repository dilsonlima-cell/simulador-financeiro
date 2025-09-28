# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# --- Cores personalizadas ---
BG_COLOR = "#F7F7F5"        # Branco Gelo
TEXT_COLOR = "#000000"       # Preto
MUTED_TEXT_COLOR = "#333333" # Cinza escuro
TABLE_BORDER_COLOR = "#E0E0E0" # Cinza muito claro

# Sidebar colors
SIDEBAR_BG = "#086788"      # Blue Sapphire
SIDEBAR_TEXT_COLOR = "#FFFFFF" # Branco
SIDEBAR_MUTED_TEXT_COLOR = "rgba(255,255,255,0.8)"

# Card colors
CARD_BG = "rgba(0,0,0,0.03)"

# Gradient & Highlight colors
GRADIENT_START = "#07A0C3"  # Blue Green
GRADIENT_END = "#F0C808"    # Jonquil
CUSTOM_GRADIENT = f"linear-gradient(90deg, {GRADIENT_START}, {GRADIENT_END})"

# Chart specific colors
CHART_CAIXA_COLOR = "#F0C808" # Jonquil
CHART_FUNDO_COLOR = "#07A0C3" # Blue Green
CHART_RETIRADAS_COLOR = "#DD1C1A" # Maximum Red
CHART_MODULOS_COLOR = "#086788" # Blue Sapphire

# ---------------------------
# CSS - Estilos da Página
# ---------------------------
st.set_page_config(page_title="Simulador Financeiro Modular", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    f"""
    <style>
    :root{{
        --g1: {CUSTOM_GRADIENT};
        --card-bg: {CARD_BG};
        --sidebar-bg: {SIDEBAR_BG};
        --text-color: {TEXT_COLOR};
        --muted-text-color: {MUTED_TEXT_COLOR};
        --table-border-color: {TABLE_BORDER_COLOR};
        --sidebar-text-color: {SIDEBAR_TEXT_COLOR};
        --sidebar-muted-text-color: {SIDEBAR_MUTED_TEXT_COLOR};
    }}
    .stApp {{ background-color: {BG_COLOR}; color: var(--text-color); }}
    .header-title, h1, h2, h3, h4, h5, h6 {{ color: var(--text-color); }}
    .subhead {{ color: var(--muted-text-color); }}
    [data-testid="stSidebar"] {{ background-color: var(--sidebar-bg); color: var(--sidebar-text-color); }}
    [data-testid="stSidebar"] strong, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label {{ color: var(--sidebar-text-color); }}
    [data-testid="stSidebar"] .stMarkdown > div > div > div {{ color: var(--sidebar-muted-text-color); }}
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] .stSelectbox {{ background-color: rgba(255,255,255,0.15); color: var(--sidebar-text-color); border: 1px solid rgba(255,255,255,0.2); }}
    [data-testid="stSidebar"] input[type="number"], [data-testid="stSidebar"] .stSelectbox > div > div > div {{ color: var(--sidebar-text-color); }}
    [data-testid="stSidebar"] button[kind="secondary"] {{ background-color: rgba(255,255,255,0.1); color: var(--sidebar-text-color); border: none; }}
    .st-emotion-cache-19n205z {{ background-color: {GRADIENT_START}; color: white; border: none; transition: background-color 0.2s; }}
    .st-emotion-cache-19n205z:hover {{ background-color: {GRADIENT_END}; color: white; }}
    .st-emotion-cache-1x8cf5l {{ background-color: {CHART_RETIRADAS_COLOR}; }}
    .st-emotion-cache-1x8cf5l:hover {{ background-color: #A00000; }}
    [data-testid="stSidebar"] [data-testid="stExpander"] {{ background-color: transparent; border: none; }}
    [data-testid="stSidebar"] [data-testid="stExpander"] > div:first-child {{ border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 0.5rem; }}
    [data-testid="stSidebar"] [data-testid="stExpander"] div[role="button"] p {{ color: var(--sidebar-text-color); font-weight: bold; }}
    .kpi-card {{ background: var(--card-bg); border-radius: 12px; padding: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); border-left: 6px solid rgba(0,0,0,0.02); color: var(--text-color); }}
    .kpi-card .small-muted {{ color: var(--muted-text-color); }}
    .kpi-gradient {{ padding: 12px; border-radius: 12px; background: var(--g1); color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}
    .kpi-gradient .small-muted {{ color: rgba(255,255,255,0.8); }}
    .pill {{ display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; background:rgba(0,0,0,0.08); color:{GRADIENT_START}; border:1px solid rgba(0,0,0,0.03); }}
    table, th, td {{ color: var(--text-color) !important; border-bottom: 1px solid var(--table-border-color); }}
    thead th {{ border-bottom: 2px solid var(--table-border-color); }}
    .stDataFrame > div > div > div > div > div > div, .stDataFrame tbody tr {{ background-color: transparent !important; color: var(--text-color) !important; }}
    .stDataFrame thead th {{ background-color: rgba(0,0,0,0.02) !important; color: var(--text-color) !important; }}
    .stDataFrame tbody tr:nth-child(even) {{ background-color: rgba(0,0,0,0.01) !important; }}
    .stDataFrame .css-x1y8h7 {{ color: var(--text-color) !important; }}
    .stNumberInput, .stSelectbox {{ background-color: var(--card-bg); border-radius: 8px; padding: 5px; border: 1px solid var(--table-border-color); }}
    .stNumberInput input, .stSelectbox > div > div > div {{ color: var(--text-color); }}
    .stNumberInput button[kind="secondary"] {{ background-color: rgba(0,0,0,0.05); color: var(--text-color); }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Funções Utilitárias
# ---------------------------
def fmt_brl(v):
    return f"R$ {v:,.2f}"

def df_to_excel_bytes(df: pd.DataFrame, annual_df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Simulacao_Mensal')
        annual_df.to_excel(writer, index=False, sheet_name='Resumo_Anual')
    return output.getvalue()

# NOVA FUNÇÃO para criar o resumo anual
def create_annual_summary(df: pd.DataFrame):
    agg_funcs = {
        'Receita': 'sum',
        'Manutenção': 'sum',
        'Aluguel': 'sum',
        'Aporte': 'sum',
        'Fundo (Mês)': 'sum',
        'Retirada (Mês)': 'sum',
        'Módulos Comprados no Ano': 'sum',
        'Módulos Ativos': 'last',
        'Caixa (Final Mês)': 'last'
    }
    annual_df = df.groupby('Ano').agg(agg_funcs).reset_index()
    annual_df.rename(columns={
        'Fundo (Mês)': 'Fundo (Ano)',
        'Retirada (Mês)': 'Retirada (Ano)',
        'Caixa (Final Mês)': 'Caixa (Final Ano)',
        'Módulos Ativos': 'Módulos (Final Ano)'
    }, inplace=True)
    annual_df = annual_df[[
        'Ano', 'Módulos (Final Ano)', 'Receita', 'Manutenção', 'Aluguel',
        'Aporte', 'Retirada (Ano)', 'Fundo (Ano)', 'Módulos Comprados no Ano', 'Caixa (Final Ano)'
    ]]
    return annual_df

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
    max_withdraw_value: float,
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
        retirada_mes_total_potencial = 0.0
        
        if caixa > 0:
            caixa_disponivel_para_distribuicao = caixa
            for r in retiradas:
                if m >= r["mes"]:
                    valor_retirada = caixa_disponivel_para_distribuicao * (r["percentual"] / 100.0)
                    retirada_mes_total_potencial += valor_retirada
            for f in fundos:
                if m >= f["mes"]:
                    valor_fundo = caixa_disponivel_para_distribuicao * (f["percentual"] / 100.0)
                    fundo_mes_total += valor_fundo
        
        excesso_para_fundo = 0.0
        retirada_mes_efetiva = retirada_mes_total_potencial
        
        if max_withdraw_value > 0 and retirada_mes_total_potencial > max_withdraw_value:
            excesso_para_fundo = retirada_mes_total_potencial - max_withdraw_value
            retirada_mes_efetiva = max_withdraw_value

        fundo_mes_total += excesso_para_fundo
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total

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
            "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa,
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
    st.markdown("<div style='display:flex; gap:10px; align-items:center'><div style='width:48px;height:48px;border-radius:10px;background:var(--g1)'></div><div><strong>Simulador Modular</strong><div style='font-size:12px;color:var(--sidebar-muted-text-color);'>Projeção com reinvestimento</div></div></div>", unsafe_allow_html=True)
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
    st.header("3. Regras de Distribuição")
    max_withdraw_value = st.number_input("Valor máximo de retirada mensal (R$)", min_value=0.0, value=10000.0, step=1000.0, format="%.2f", help="Quando a retirada baseada em % atingir este valor, o restante irá para o fundo de reserva. Deixe em 0 para desativar.")
    
    st.markdown("---")
    st.header("4. Eventos Financeiros")
    
    if "aportes" not in st.session_state: st.session_state.aportes = [{"mes": 3, "valor": 50_000.0}]
    if "retiradas" not in st.session_state: st.session_state.retiradas = [{"mes": 25, "percentual": 30.0}]
    if "fundos" not in st.session_state: st.session_state.fundos = [{"mes": 25, "percentual": 10.0}]

    with st.expander("Aportes (investimentos pontuais)"):
        for i, a in enumerate(st.session_state.aportes):
            col_a1, col_a2, col_a3 = st.columns([1,2,0.5])
            with col_a1: a["mes"] = st.number_input(f"Mês Aporte #{i+1}", 1, years*12, a["mes"], key=f"ap_mes_{i}", label_visibility="collapsed")
            with col_a2: a["valor"] = st.number_input(f"Valor Aporte #{i+1}", 0.0, value=a["valor"], step=1000.0, key=f"ap_val_{i}", format="%.2f", label_visibility="collapsed")
            with col_a3:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"ap_rem_{i}", help="Remover Aporte"): st.session_state.aportes.pop(i); st.rerun()
        if st.button("Adicionar Aporte", key="add_aporte_btn"): st.session_state.aportes.append({"mes": 1, "valor": 10000.0}); st.rerun()

    with st.expander("Retiradas (% sobre o caixa mensal)"):
        for i, r in enumerate(st.session_state.retiradas):
            col_r1, col_r2, col_r3 = st.columns([1,2,0.5])
            with col_r1: r["mes"] = st.number_input(f"Mês Início Retirada #{i+1}", 1, years*12, r["mes"], key=f"re_mes_{i}", label_visibility="collapsed")
            with col_r2: r["percentual"] = st.number_input(f"% Caixa Retirada #{i+1}", 0.0, 100.0, r["percentual"], step=1.0, key=f"re_pct_{i}", format="%.1f", label_visibility="collapsed")
            with col_r3:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"re_rem_{i}", help="Remover Retirada"): st.session_state.retiradas.pop(i); st.rerun()
        if st.button("Adicionar Retirada", key="add_retirada_btn"): st.session_state.retiradas.append({"mes": 1, "percentual": 10.0}); st.rerun()

    with st.expander("Fundos de Reserva (% sobre o caixa mensal)"):
        for i, f in enumerate(st.session_state.fundos):
            col_f1, col_f2, col_f3 = st.columns([1,2,0.5])
            with col_f1: f["mes"] = st.number_input(f"Mês Início Fundo #{i+1}", 1, years*12, f["mes"], key=f"fu_mes_{i}", label_visibility="collapsed")
            with col_f2: f["percentual"] = st.number_input(f"% Caixa Fundo #{i+1}", 0.0, 100.0, f["percentual"], step=1.0, key=f"fu_pct_{i}", format="%.1f", label_visibility="collapsed")
            with col_f3:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"fu_rem_{i}", help="Remover Fundo"): st.session_state.fundos.pop(i); st.rerun()
        if st.button("Adicionar Fundo", key="add_fundo_btn"): st.session_state.fundos.append({"mes": 1, "percentual": 5.0}); st.rerun()
            
# ---------------------------
# Conteúdo Principal
# ---------------------------
df = simulate(
    years=years, modules_init=modules_init, cost_per_module=cost_per_module,
    cost_correction_rate=cost_correction_rate, revenue_per_module=revenue_per_module,
    maintenance_per_module=maintenance_per_module, rent_value=rent_value,
    rent_start_month=rent_start_month, max_withdraw_value=max_withdraw_value,
    aportes=st.session_state.aportes, retiradas=st.session_state.retiradas, 
    fundos=st.session_state.fundos,
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
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Caixa (Final Mês)"], mode="lines", name="Caixa", line=dict(color=CHART_CAIXA_COLOR, width=2.5)))
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Fundo Acumulado"], mode="lines", name="Fundo Acumulado", line=dict(color=CHART_FUNDO_COLOR, width=1.5)))
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Retiradas Acumuladas"], mode="lines", name="Retiradas Acumuladas", line=dict(color=CHART_RETIRADAS_COLOR, width=1.5)))
    
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR))
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)
    st.plotly_chart(fig, use_container_width=True)

with colB:
    st.subheader("Evolução dos Módulos")
    fig_mod = go.Figure()
    fig_mod.add_trace(go.Scatter(x=df["Mês"], y=df["Módulos Ativos"], mode="lines", name="Módulos", line=dict(color=CHART_MODULOS_COLOR, width=2.5), fill='tozeroy'))
    fig_mod.update_layout(margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR))
    fig_mod.update_xaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)
    fig_mod.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TABLE_BORDER_COLOR, zeroline=True, zerolinewidth=2, zerolinecolor=TABLE_BORDER_COLOR)
    st.plotly_chart(fig_mod, use_container_width=True)

st.markdown("---")

# --- NOVA SEÇÃO: RESUMO ANUAL ---
st.subheader("Resumo Anual")
annual_summary_df = create_annual_summary(df)
annual_display_df = annual_summary_df.copy()
format_cols_annual = ["Receita", "Manutenção", "Aluguel", "Aporte", "Retirada (Ano)", "Fundo (Ano)", "Caixa (Final Ano)"]
for col in format_cols_annual:
    annual_display_df[col] = annual_display_df[col].apply(fmt_brl)
st.dataframe(annual_display_df.set_index("Ano"), use_container_width=True)
# --- FIM DA NOVA SEÇÃO ---

st.markdown("---")

st.subheader("Resumo Consolidado por Ponto no Tempo")
col_res1, col_res2, col_res3 = st.columns([1, 1, 2])
with col_res1: summary_year = st.number_input("Selecione o ano", 1, years, min(5, years), 1)
with col_res2: summary_month = st.selectbox("E o mês", list(range(1, 13)), index=11)

def get_summary_for_point_in_time(df, year, month):
    target_month = (year - 1) * 12 + month
    if target_month > len(df): target_month = len(df)
    data = df[df["Mês"] == target_month].iloc[0]
    actual_year = (data['Mês'] - 1) // 12 + 1
    actual_month = (data['Mês'] - 1) % 12 + 1
    return {"Marco": f"Ano {actual_year}, Mês {actual_month}", "Módulos": f"{int(data['Módulos Ativos'])}", "Caixa": fmt_brl(data['Caixa (Final Mês)']), "Fundo": fmt_brl(data['Fundo Acumulado']), "Retiradas": fmt_brl(data['Retiradas Acumuladas']), "Invest. Total": fmt_brl(data['Investimento Total Acumulado'])}

with col_res3:
    summary_data = []
    summary_data.append(get_summary_for_point_in_time(df, summary_year, summary_month))
    final_month_in_sim = years * 12
    selected_month_in_sim = (summary_year - 1) * 12 + summary_month
    if selected_month_in_sim != final_month_in_sim:
        summary_data.append(get_summary_for_point_in_time(df, years, 12))
    st.table(pd.DataFrame(summary_data).set_index("Marco"))

st.markdown("---")

st.subheader("Tabela Completa da Simulação")
with st.expander("Clique para expandir e ver todos os dados mensais"):
    df_display = df.copy()
    format_cols = ["Receita", "Manutenção", "Aluguel", "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado", "Fundo Acumulado", "Retiradas Acumuladas", "Custo Módulo (Próx. Ano)"]
    for col in format_cols:
        df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
    st.dataframe(df_display, use_container_width=True)

excel_bytes = df_to_excel_bytes(df, annual_summary_df) # Passa o resumo anual para a função de download
st.download_button("📥 Baixar Relatório Completo (Excel)", data=excel_bytes, file_name=f"simulacao_modulos_{years}_anos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

