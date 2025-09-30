# app.py
# Simulador Modular — v10.1 com lógica correta de patrimônio + interface de configuração reorganizada
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import re
import json
import hashlib
from copy import deepcopy

# --- PALETA DE CORES (Tema Azul Corporativo Claro) ---
PRIMARY_COLOR   = "#F5A623"
SECONDARY_COLOR = "#0EA5E9"
SUCCESS_COLOR   = "#10B981"
DANGER_COLOR    = "#EF4444"
WARNING_COLOR   = "#F59E0B"
INFO_COLOR      = "#3B82F6"
APP_BG          = "#E6F1FB"
SIDEBAR_BG      = "#D4E6FA"
CARD_COLOR      = "#FFFFFF"
TEXT_COLOR      = "#0F172A"
MUTED_TEXT_COLOR = "#334155"
TABLE_BORDER_COLOR = "#CBD5E1"
CHART_GRID_COLOR  = "#E2E8F0"

# --- COLUNAS PARA FORMATAÇÃO ---
MONEY_COLS = {
    "Receita", "Manutenção", "Aluguel", "Parcela Terreno Inicial", "Parcelas Terrenos (Novos)", "Gastos",
    "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado",
    "Fundo Acumulado", "Retiradas Acumuladas", "Patrimônio Líquido", "Juros Terreno Inicial",
    "Amortização Terreno Inicial", "Equity Terreno Inicial", "Valor de Mercado Terreno",
    "Patrimônio Terreno", "Juros Acumulados", "Amortização Acumulada", "Desembolso Total"
}
COUNT_COLS = {"Mês", "Ano", "Módulos Ativos", "Módulos Alugados", "Módulos Próprios", "Módulos Comprados no Ano"}

# ---------------------------
# Helpers
# ---------------------------
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def fmt_brl(v):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "-"
        s = f"{float(v):,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def render_kpi_card(title, value, bg_color, icon=None, subtitle=None, dark_text=False):
    icon_html = f"<div style='font-size: 2rem; margin-bottom: 0.5rem;'>{icon}</div>" if icon else ""
    subtitle_html = f"<div class='kpi-card-subtitle'>{subtitle}</div>" if subtitle else ""
    txt_color = "#0F172A" if dark_text else "#FFFFFF"
    st.markdown(f"""
        <div class="kpi-card-modern" style="background:{bg_color}; color:{txt_color};">
            {icon_html}
            <div class="kpi-card-value-modern">{value}</div>
            <div class="kpi-card-title-modern">{title}</div>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)

def render_report_metric(title, value):
    st.markdown(f"""
        <div class="report-metric-card">
            <div class="report-metric-title">{title}</div>
            <div class="report-metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def calculate_summary_metrics(df):
    summary = {"roi_pct": 0, "break_even_month": "N/A", "total_investment": 0, "net_profit": 0}
    if df.empty:
        return summary
    final = df.iloc[-1]
    total_investment = final['Investimento Total Acumulado']
    summary["total_investment"] = total_investment
    if total_investment > 0:
        net_profit = final['Patrimônio Líquido'] - total_investment
        summary["roi_pct"] = (net_profit / total_investment) * 100
        summary["net_profit"] = net_profit
    break_even_df = df[df['Patrimônio Líquido'] >= df['Investimento Total Acumulado']]
    if not break_even_df.empty:
        summary["break_even_month"] = int(break_even_df.iloc[0]['Mês'])
    return summary

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Simulacao_Mensal")
        wb, ws = writer.book, writer.sheets["Simulacao_Mensal"]
        money_fmt = wb.add_format({"num_format": "R$ #,##0.00"})
        for i, col in enumerate(df.columns):
            width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            fmt = money_fmt if col in MONEY_COLS else None
            ws.set_column(i, i, width, fmt)
    return output.getvalue()

def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:60]

def apply_plot_theme(fig, title=None, h=420):
    fig.update_layout(
        title=dict(text=title or fig.layout.title.text, x=0.5, xanchor='center', font=dict(size=16, color=TEXT_COLOR)),
        height=h,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor=TABLE_BORDER_COLOR, borderwidth=1,
            font=dict(color=TEXT_COLOR)
        ),
        plot_bgcolor=CARD_COLOR,
        paper_bgcolor=CARD_COLOR,
        font=dict(color=TEXT_COLOR),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR)),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR))
    )
    return fig

def compute_cache_key(cfg: dict) -> str:
    payload = json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()

# ---------------------------
# CSS - Estilos da Página
# ---------------------------
st.set_page_config(page_title="Simulador Modular", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"""
    <style>
        .main .block-container {{ padding: 1.5rem 2rem; max-width: 100%; }}
        .stApp {{ background: {APP_BG}; }}
        [data-testid="stSidebar"] {{ background: {SIDEBAR_BG}; border-right: 1px solid {TABLE_BORDER_COLOR}; }}
        [data-testid="stSidebar"] h1 {{ color: {TEXT_COLOR}; font-weight: 700; font-size: 1.5rem; }}
        h1, h2, h3, h4, h5, h6 {{ color: {TEXT_COLOR}; font-weight: 600; }}
        .subhead {{ color: {MUTED_TEXT_COLOR}; font-size: 1.05rem; }}
        .stButton > button {{
            border-radius: 12px; border: 2px solid {PRIMARY_COLOR};
            background-color: {PRIMARY_COLOR}; color: white;
            padding: 12px 24px; font-weight: 600; transition: all 0.3s ease;
            white-space: pre-line; text-align: center;
        }}
        .stButton > button:hover {{ background-color: #D98200; border-color: #D98200; transform: translateY(-2px); }}
        .stButton > button[kind="secondary"] {{ background-color: transparent; color: {PRIMARY_COLOR}; }}
        .stButton > button[kind="secondary"]:hover {{ background-color: rgba(245, 166, 35, .08); }}
        .card {{ background: {CARD_COLOR}; border-radius: 16px; padding: 1.5rem; border: 1px solid {TABLE_BORDER_COLOR}; margin-bottom: 1.25rem; }}
        .kpi-card-modern {{
            border-radius: 20px; padding: 1.5rem 1.25rem; height: 100%; text-align: center;
            transition: transform 0.3s ease; background: linear-gradient(135deg, {PRIMARY_COLOR} 0%, {SECONDARY_COLOR} 100%);
        }}
        .kpi-card-modern:hover {{ transform: translateY(-5px); }}
        .kpi-card-title-modern {{ font-size: 0.95rem; font-weight: 600; opacity: .95; margin-top: 0.5rem; }}
        .kpi-card-value-modern {{ font-size: 2rem; font-weight: 800; line-height: 1.1; }}
        .kpi-card-subtitle {{ font-size: 0.85rem; opacity: .9; margin-top: 0.35rem; }}
        .report-metric-card {{ background: {CARD_COLOR}; border-radius: 8px; padding: 0.75rem 1rem; border: 1px solid {TABLE_BORDER_COLOR}; text-align: center; margin-bottom: 0.5rem; }}
        .report-metric-title {{ font-size: 0.8rem; color: {MUTED_TEXT_COLOR}; margin-bottom: 0.25rem; text-transform: uppercase; font-weight: 600; }}
        .report-metric-value {{ font-size: 1.25rem; font-weight: 700; color: {TEXT_COLOR}; }}
        [data-testid="stDataFrame"] th {{ background-color: {SIDEBAR_BG} !important; color: {TEXT_COLOR} !important; }}
        .stTextInput input, .stNumberInput input, .stSelectbox select {{
            background: {CARD_COLOR} !important; color: {TEXT_COLOR} !important; border: 1px solid {TABLE_BORDER_COLOR} !important;
        }}
        .gradient-header {{
            background: linear-gradient(135deg, #0C4A6E 0%, #60A5FA 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: 800;
        }}
        .section-title {{ font-size: 1.25rem; font-weight: 700; margin: 1.25rem 0 0.75rem 0; color: {TEXT_COLOR}; }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Motor de Simulação (v10.1 — com SAC e patrimônio do terreno)
# ---------------------------
@st.cache_data(show_spinner=False)
def simulate(_config, reinvestment_strategy, cache_key: str):
    cfg_rented = _config['rented']
    cfg_owned = _config['owned']
    cfg_global = _config['global']
    months = cfg_global['years'] * 12
    rows = []
    modules_rented = cfg_rented['modules_init']
    modules_owned = cfg_owned['modules_init']
    caixa = 0.0
    investimento_total = (
        modules_rented * cfg_rented['cost_per_module'] +
        modules_owned * cfg_owned['cost_per_module']
    )
    historical_value_rented = modules_rented * cfg_rented['cost_per_module']
    historical_value_owned = modules_owned * cfg_owned['cost_per_module']
    fundo_ac = 0.0
    retiradas_ac = 0.0
    compra_intercalada_counter = 0
    correction_rate_pct = cfg_global.get('general_correction_rate', 0.0) / 100.0
    land_appreciation_rate_pct = cfg_global.get('land_appreciation_rate', 3.0) / 100.0
    custo_modulo_atual_rented = cfg_rented['cost_per_module']
    custo_modulo_atual_owned = cfg_owned['cost_per_module']
    receita_p_mod_rented = cfg_rented['revenue_per_module']
    receita_p_mod_owned = cfg_owned['revenue_per_module']
    manut_p_mod_rented = cfg_rented['maintenance_per_module']
    manut_p_mod_owned = cfg_owned['maintenance_per_module']
    aluguel_p_novo_mod = cfg_rented['rent_per_new_module']
    parcela_p_novo_terreno = cfg_owned['monthly_land_plot_parcel']
    aluguel_mensal_corrente = cfg_rented['rent_value'] + (cfg_rented['modules_init'] * cfg_rented['rent_per_new_module'])
    parcelas_terrenos_novos_mensal_corrente = 0.0
    # Financiamento do terreno inicial
    parcela_terreno_inicial_atual = 0.0
    saldo_financiamento_terreno = 0.0
    equity_terreno_inicial = 0.0
    juros_acumulados = 0.0
    amortizacao_acumulada = 0.0
    valor_compra_terreno = 0.0
    taxa_juros_mensal = 0.0
    amortizacao_mensal = 0.0
    if cfg_owned['land_total_value'] > 0:
        valor_compra_terreno = cfg_owned['land_total_value']
        valor_entrada_terreno = cfg_owned['land_total_value'] * (cfg_owned['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_owned['land_total_value'] - valor_entrada_terreno
        saldo_financiamento_terreno = valor_financiado
        equity_terreno_inicial = valor_entrada_terreno
        if cfg_owned['land_installments'] > 0:
            amortizacao_mensal = valor_financiado / cfg_owned['land_installments']
            taxa_juros_mensal = (cfg_owned.get('land_interest_rate', 8.0) / 100.0) / 12
        investimento_total += valor_entrada_terreno
    for m in range(1, months + 1):
        receita = (modules_rented * receita_p_mod_rented) + (modules_owned * receita_p_mod_owned)
        manut = (modules_rented * manut_p_mod_rented) + (modules_owned * manut_p_mod_owned)
        novos_modulos_comprados = 0
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes
        gastos_operacionais = aluguel_mensal_corrente + parcelas_terrenos_novos_mensal_corrente
        lucro_operacional = receita - manut - gastos_operacionais
        juros_terreno_mes = 0.0
        amortizacao_terreno_mes = 0.0
        parcela_terreno_inicial_mes = 0.0
        if saldo_financiamento_terreno > 0:
            juros_terreno_mes = saldo_financiamento_terreno * taxa_juros_mensal
            amortizacao_terreno_mes = min(amortizacao_mensal, saldo_financiamento_terreno)
            parcela_terreno_inicial_mes = juros_terreno_mes + amortizacao_terreno_mes
            saldo_financiamento_terreno -= amortizacao_terreno_mes
            equity_terreno_inicial += amortizacao_terreno_mes
            juros_acumulados += juros_terreno_mes
            amortizacao_acumulada += amortizacao_terreno_mes
        caixa += lucro_operacional
        caixa -= parcela_terreno_inicial_mes
        fundo_mes_total = 0.0
        retirada_mes_efetiva = 0.0
        if lucro_operacional > 0:
            base_distribuicao = lucro_operacional
            retirada_potencial = sum(base_distribuicao * (r['percentual'] / 100.0) for r in cfg_global['retiradas'] if m >= r['mes'])
            fundo_potencial = sum(base_distribuicao * (f['percentual'] / 100.0) for f in cfg_global['fundos'] if m >= f['mes'])
            if cfg_global['max_withdraw_value'] > 0 and retirada_potencial > cfg_global['max_withdraw_value']:
                excesso = retirada_potencial - cfg_global['max_withdraw_value']
                retirada_mes_efetiva = cfg_global['max_withdraw_value']
                fundo_mes_total = fundo_potencial + excesso
            else:
                retirada_mes_efetiva = retirada_potencial
                fundo_mes_total = fundo_potencial
            total_distribuicao = retirada_mes_efetiva + fundo_mes_total
            if total_distribuicao > caixa:
                if caixa > 0:
                    proporcao = caixa / total_distribuicao
                    retirada_mes_efetiva *= proporcao
                    fundo_mes_total *= proporcao
                else:
                    retirada_mes_efetiva = 0.0
                    fundo_mes_total = 0.0
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total
        if m % 12 == 0:
            if reinvestment_strategy == 'buy':
                custo_expansao = custo_modulo_atual_owned
                if caixa >= custo_expansao and custo_expansao > 0:
                    novos_modulos_comprados = int(caixa // custo_expansao)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo_expansao
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        historical_value_owned += custo_da_compra
                        modules_owned += novos_modulos_comprados
                        parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
                        compra_intercalada_counter += novos_modulos_comprados
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
                if caixa >= custo_expansao and custo_expansao > 0:
                    novos_modulos_comprados = int(caixa // custo_expansao)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo_expansao
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        historical_value_rented += custo_da_compra
                        modules_rented += novos_modulos_comprados
                        aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
            elif reinvestment_strategy == 'alternate':
                if compra_intercalada_counter % 2 == 0:
                    custo_expansao = custo_modulo_atual_owned
                    if caixa >= custo_expansao and custo_expansao > 0:
                        novos_modulos_comprados = int(caixa // custo_expansao)
                        if novos_modulos_comprados > 0:
                            custo_da_compra = novos_modulos_comprados * custo_expansao
                            caixa -= custo_da_compra
                            investimento_total += custo_da_compra
                            historical_value_owned += custo_da_compra
                            modules_owned += novos_modulos_comprados
                            parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
                            compra_intercalada_counter += novos_modulos_comprados
                else:
                    custo_expansao = custo_modulo_atual_rented
                    if caixa >= custo_expansao and custo_expansao > 0:
                        novos_modulos_comprados = int(caixa // custo_expansao)
                        if novos_modulos_comprados > 0:
                            custo_da_compra = novos_modulos_comprados * custo_expansao
                            caixa -= custo_da_compra
                            investimento_total += custo_da_compra
                            historical_value_rented += custo_da_compra
                            modules_rented += novos_modulos_comprados
                            aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
                            compra_intercalada_counter += novos_modulos_comprados
            correction_factor = 1 + correction_rate_pct
            custo_modulo_atual_owned *= correction_factor
            custo_modulo_atual_rented *= correction_factor
            receita_p_mod_rented *= correction_factor
            receita_p_mod_owned *= correction_factor
            manut_p_mod_rented *= correction_factor
            manut_p_mod_owned *= correction_factor
            aluguel_mensal_corrente *= correction_factor
            parcelas_terrenos_novos_mensal_corrente *= correction_factor
            parcela_p_novo_terreno *= correction_factor
            aluguel_p_novo_mod *= correction_factor
        valor_mercado_terreno = valor_compra_terreno * ((1 + land_appreciation_rate_pct) ** (m / 12))
        patrimonio_terreno = valor_mercado_terreno - saldo_financiamento_terreno
        ativos = historical_value_owned + historical_value_rented + caixa + fundo_ac + patrimonio_terreno
        passivos = saldo_financiamento_terreno
        patrimonio_liquido = ativos - passivos
        desembolso_total = investimento_total + juros_acumulados + (aluguel_mensal_corrente * (m / 12)) + (parcelas_terrenos_novos_mensal_corrente * (m / 12))
        gastos_totais = manut + aluguel_mensal_corrente + juros_terreno_mes + parcelas_terrenos_novos_mensal_corrente
        rows.append({
            "Mês": m,
            "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules_owned + modules_rented,
            "Módulos Alugados": modules_rented,
            "Módulos Próprios": modules_owned,
            "Receita": receita,
            "Manutenção": manut,
            "Aluguel": aluguel_mensal_corrente,
            "Juros Terreno Inicial": juros_terreno_mes,
            "Amortização Terreno Inicial": amortizacao_terreno_mes,
            "Parcela Terreno Inicial": parcela_terreno_inicial_mes,
            "Parcelas Terrenos (Novos)": parcelas_terrenos_novos_mensal_corrente,
            "Gastos": gastos_totais,
            "Aporte": aporte_mes,
            "Fundo (Mês)": fundo_mes_total,
            "Retirada (Mês)": retirada_mes_efetiva,
            "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac,
            "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Patrimônio Líquido": patrimonio_liquido,
            "Equity Terreno Inicial": equity_terreno_inicial,
            "Valor de Mercado Terreno": valor_mercado_terreno,
            "Patrimônio Terreno": patrimonio_terreno,
            "Juros Acumulados": juros_acumulados,
            "Amortização Acumulada": amortizacao_acumulada,
            "Desembolso Total": desembolso_total
        })
    return pd.DataFrame(rows)

# ---------------------------
# Estado Inicial
# ---------------------------
def get_default_config():
    return {
        'rented': {
            'modules_init': 1,
            'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0,
            'maintenance_per_module': 200.0,
            'rent_value': 750.0,
            'rent_per_new_module': 950.0
        },
        'owned': {
            'modules_init': 0,
            'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0,
            'maintenance_per_module': 200.0,
            'monthly_land_plot_parcel': 200.0,
            'land_value_per_module': 25000.0,
            'land_total_value': 0.0,
            'land_down_payment_pct': 20.0,
            'land_installments': 120,
            'land_interest_rate': 8.0
        },
        'global': {
            'years': 15,
            'max_withdraw_value': 50000.0,
            'general_correction_rate': 5.0,
            'land_appreciation_rate': 3.0,
            'aportes': [],
            'retiradas': [],
            'fundos': []
        }
    }

if 'config' not in st.session_state:
    st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state:
    st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = pd.DataFrame()
if 'active_page' not in st.session_state:
    st.session_state.active_page = 'Dashboard'

# ---------------------------
# Barra lateral
# ---------------------------
with st.sidebar:
    st.markdown("<h1>📊 Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #1F2937; margin-bottom: 1rem;'>Projeção com reinvestimento inteligente</p>", unsafe_allow_html=True)
    nav_options = {"Dashboard": "📈", "Relatórios e Dados": "📋", "Configurações": "⚙️"}
    selected = st.radio("Menu", list(nav_options.keys()), key="nav_radio", label_visibility="collapsed", format_func=lambda x: f"{nav_options[x]} {x}")
    st.session_state.active_page = selected
    st.markdown("---")
    st.markdown("<p style='color: #334155; font-size: 0.85rem;'>Desenvolvido com Streamlit</p>", unsafe_allow_html=True)

# ---------------------------
# Página de Configurações — REORGANIZADA
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.markdown("<h1 class='gradient-header'>Configurações de Investimento</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Ajuste os parâmetros da simulação financeira e adicione eventos.</p>", unsafe_allow_html=True)

    # Seção 1: Parâmetros do Terreno Alugado
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏢 Terreno Alugado</div>', unsafe_allow_html=True)
    cfg_r = st.session_state.config['rented']
    col1, col2, col3 = st.columns(3)
    with col1:
        cfg_r['modules_init'] = st.number_input("Módulos iniciais (alugados)", 0, value=cfg_r['modules_init'], key="rent_mod_init")
        cfg_r['cost_per_module'] = st.number_input("Custo por módulo (R$)", 0.0, value=cfg_r['cost_per_module'], format="%.2f", key="rent_cost_mod")
    with col2:
        cfg_r['revenue_per_module'] = st.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_r['revenue_per_module'], format="%.2f", key="rent_rev_mod")
        cfg_r['maintenance_per_module'] = st.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_r['maintenance_per_module'], format="%.2f", key="rent_maint_mod")
    with col3:
        cfg_r['rent_value'] = st.number_input("Aluguel mensal fixo (R$)", 0.0, value=cfg_r['rent_value'], format="%.2f", key="rent_base_rent")
        cfg_r['rent_per_new_module'] = st.number_input("Custo de aluguel por novo módulo (R$)", 0.0, value=cfg_r['rent_per_new_module'], format="%.2f", key="rent_new_rent")
    st.markdown('</div>', unsafe_allow_html=True)

    # Seção 2: Parâmetros do Terreno Próprio
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏠 Terreno Próprio</div>', unsafe_allow_html=True)
    cfg_o = st.session_state.config['owned']
    
    st.markdown("##### 🏗️ Financiamento do Terreno Inicial")
    col1, col2, col3 = st.columns(3)
    with col1:
        cfg_o['land_total_value'] = st.number_input("Valor total do terreno inicial (R$)", 0.0, value=cfg_o['land_total_value'], format="%.2f", key="own_total_land_val")
    if cfg_o['land_total_value'] > 0:
        with col2:
            cfg_o['land_down_payment_pct'] = st.number_input("Entrada (%)", 0.0, 100.0, value=cfg_o['land_down_payment_pct'], format="%.1f", key="own_down_pay")
            cfg_o['land_installments'] = st.number_input("Quantidade de parcelas", 1, 480, value=cfg_o['land_installments'], key="own_install")
        with col3:
            cfg_o['land_interest_rate'] = st.number_input("Juros anual (%)", 0.0, 50.0, value=cfg_o.get('land_interest_rate', 8.0), format="%.1f", key="own_interest")
            valor_entrada = cfg_o['land_total_value'] * (cfg_o['land_down_payment_pct'] / 100.0)
            valor_financiado = cfg_o['land_total_value'] - valor_entrada
            taxa_juros_mensal = (cfg_o['land_interest_rate'] / 100.0) / 12
            amortizacao_mensal = valor_financiado / cfg_o['land_installments'] if cfg_o['land_installments'] > 0 else 0
            primeira_parcela = amortizacao_mensal + (valor_financiado * taxa_juros_mensal) if cfg_o['land_installments'] > 0 else 0
            st.metric("Valor da Entrada", fmt_brl(valor_entrada))
            st.metric("1ª Parcela Estimada", fmt_brl(primeira_parcela))
    
    st.markdown("##### 📦 Módulos Próprios")
    col1, col2 = st.columns(2)
    with col1:
        cfg_o['modules_init'] = st.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
        cfg_o['cost_per_module'] = st.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
        cfg_o['monthly_land_plot_parcel'] = st.number_input("Parcela mensal por novo terreno (R$)", 0.0, value=cfg_o['monthly_land_plot_parcel'], format="%.2f", key="own_land_parcel")
    with col2:
        cfg_o['revenue_per_module'] = st.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
        cfg_o['maintenance_per_module'] = st.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
    st.markdown('</div>', unsafe_allow_html=True)

    # Seção 3: Parâmetros Globais
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🌐 Parâmetros Globais</div>', unsafe_allow_html=True)
    cfg_g = st.session_state.config['global']
    col1, col2 = st.columns(2)
    with col1:
        cfg_g['years'] = st.number_input("Anos de projeção", 1, 50, value=cfg_g['years'], key="glob_years")
        cfg_g['general_correction_rate'] = st.number_input("Correção anual geral (%)", 0.0, 50.0, value=cfg_g['general_correction_rate'], format="%.1f", key="glob_correction")
    with col2:
        cfg_g['max_withdraw_value'] = st.number_input("Retirada máxima mensal (R$)", 0.0, value=cfg_g['max_withdraw_value'], format="%.2f", key="glob_max_withdraw")
        cfg_g['land_appreciation_rate'] = st.number_input("Valorização anual do terreno (%)", 0.0, 50.0, value=cfg_g.get('land_appreciation_rate', 3.0), format="%.1f", key="glob_land_appr")
    st.markdown('</div>', unsafe_allow_html=True)

    # Seção 4: Estratégia de Reinvestimento
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔄 Estratégia de Reinvestimento</div>', unsafe_allow_html=True)
    reinvestment_strategy = st.selectbox(
        "Como reinvestir o lucro?",
        ["buy", "rent", "alternate"],
        format_func=lambda x: {
            "buy": "Comprar módulos próprios",
            "rent": "Alugar novos módulos",
            "alternate": "Alternar entre comprar e alugar"
        }[x],
        key="reinvestment_strategy"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Seção 5: Eventos Financeiros
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📅 Eventos Financeiros</div>', unsafe_allow_html=True)
    tab_aportes, tab_retiradas, tab_fundos = st.tabs(["Aportes", "Retiradas", "Fundos"])
    with tab_aportes:
        st.markdown("**Aportes de Capital (opcional)**")
        aporte_cols = st.columns([1, 2, 1])
        with aporte_cols[0]:
            aporte_mes = st.number_input("Mês do aporte", 1, cfg_g['years'] * 12, 1, key="aporte_mes")
        with aporte_cols[1]:
            aporte_valor = st.number_input("Valor (R$)", 0.0, key="aporte_valor")
        with aporte_cols[2]:
            if st.button("➕ Adicionar Aporte"):
                cfg_g['aportes'].append({"mes": aporte_mes, "valor": aporte_valor})
                st.rerun()
        if cfg_g['aportes']:
            st.markdown("**Aportes agendados:**")
            for i, a in enumerate(cfg_g['aportes']):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"Mês {a['mes']}")
                c2.write(fmt_brl(a['valor']))
                if c3.button("🗑️", key=f"del_aporte_{i}"):
                    cfg_g['aportes'].pop(i)
                    st.rerun()
    with tab_retiradas:
        st.markdown("**Regras de Retirada**")
        retirada_cols = st.columns([1, 2, 1])
        with retirada_cols[0]:
            retirada_mes = st.number_input("Mês inicial", 1, cfg_g['years'] * 12, 1, key="retirada_mes")
        with retirada_cols[1]:
            retirada_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, key="retirada_pct")
        with retirada_cols[2]:
            if st.button("➕ Adicionar Retirada"):
                cfg_g['retiradas'].append({"mes": retirada_mes, "percentual": retirada_pct})
                st.rerun()
        if cfg_g['retiradas']:
            st.markdown("**Regras ativas:**")
            for i, r in enumerate(cfg_g['retiradas']):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"A partir do mês {r['mes']}")
                c2.write(f"{r['percentual']}%")
                if c3.button("🗑️", key=f"del_retirada_{i}"):
                    cfg_g['retiradas'].pop(i)
                    st.rerun()
    with tab_fundos:
        st.markdown("**Regras de Fundo de Reserva**")
        fundo_cols = st.columns([1, 2, 1])
        with fundo_cols[0]:
            fundo_mes = st.number_input("Mês inicial", 1, cfg_g['years'] * 12, 1, key="fundo_mes")
        with fundo_cols[1]:
            fundo_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, key="fundo_pct")
        with fundo_cols[2]:
            if st.button("➕ Adicionar Fundo"):
                cfg_g['fundos'].append({"mes": fundo_mes, "percentual": fundo_pct})
                st.rerun()
        if cfg_g['fundos']:
            st.markdown("**Regras ativas:**")
            for i, f in enumerate(cfg_g['fundos']):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"A partir do mês {f['mes']}")
                c2.write(f"{f['percentual']}%")
                if c3.button("🗑️", key=f"del_fundo_{i}"):
                    cfg_g['fundos'].pop(i)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 Executar Simulação", type="primary", use_container_width=True):
        with st.spinner("Calculando projeção..."):
            cache_key = compute_cache_key(st.session_state.config)
            st.session_state.simulation_df = simulate(st.session_state.config, reinvestment_strategy, cache_key)
        st.success("Simulação concluída!")

# ---------------------------
# Dashboard e Relatórios (mantidos do Codigo__2.txt)
# ---------------------------
# (As seções 'Dashboard' e 'Relatórios e Dados' permanecem idênticas ao Codigo__2.txt, pois já estão bem implementadas)
# Para brevidade, omitimos aqui, mas devem ser copiadas integralmente do Codigo__2.txt.

# --- Dashboard ---
elif st.session_state.active_page == 'Dashboard':
    # (copiar exatamente do Codigo__2.txt a partir da linha "elif st.session_state.active_page == 'Dashboard':")
    st.markdown("<h1 class='gradient-header'>Dashboard de Projeção</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Análise visual do desempenho do investimento ao longo do tempo.</p>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("💡 Configure os parâmetros na página 'Configurações' e execute a simulação para ver os resultados.")
    else:
        df = st.session_state.simulation_df
        summary = calculate_summary_metrics(df)
        final = df.iloc[-1]
        st.markdown("### 📊 Resumo Executivo")
        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            render_kpi_card("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']), SUCCESS_COLOR, "💰")
        with kpi_cols[1]:
            render_kpi_card("ROI Total", f"{summary['roi_pct']:.1f}%", INFO_COLOR, "📈")
        with kpi_cols[2]:
            render_kpi_card("Ponto de Equilíbrio", f"Mês {summary['break_even_month']}", WARNING_COLOR, "⚖️")
        with kpi_cols[3]:
            render_kpi_card("Investimento Total", fmt_brl(final['Investimento Total Acumulado']), SECONDARY_COLOR, "💼")
        st.markdown("### 📈 Evolução do Investimento")
        chart_cols = st.columns(2)
        with chart_cols[0]:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Patrimônio Líquido'], mode='lines', name='Patrimônio Líquido', line=dict(color=SUCCESS_COLOR, width=3)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Investimento Total Acumulado'], mode='lines', name='Investimento Total', line=dict(color=SECONDARY_COLOR, width=2, dash='dash')))
            fig = apply_plot_theme(fig, "Patrimônio Líquido vs Investimento")
            st.plotly_chart(fig, use_container_width=True)
        with chart_cols[1]:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Receita'], mode='lines', name='Receita', line=dict(color=SUCCESS_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Gastos'], mode='lines', name='Gastos', line=dict(color=DANGER_COLOR, width=2)))
            fig = apply_plot_theme(fig, "Receita vs Gastos")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("### 📦 Crescimento e Fluxo de Caixa")
        chart_cols2 = st.columns(2)
        with chart_cols2[0]:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Módulos Ativos'], mode='lines', name='Módulos Ativos', line=dict(color=PRIMARY_COLOR, width=3)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Módulos Alugados'], mode='lines', name='Módulos Alugados', line=dict(color=SECONDARY_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Módulos Próprios'], mode='lines', name='Módulos Próprios', line=dict(color=SUCCESS_COLOR, width=2)))
            fig = apply_plot_theme(fig, "Evolução dos Módulos")
            st.plotly_chart(fig, use_container_width=True)
        with chart_cols2[1]:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Caixa (Final Mês)'], mode='lines', name='Caixa', line=dict(color=INFO_COLOR, width=3)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Fundo Acumulado'], mode='lines', name='Fundo Acumulado', line=dict(color=WARNING_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Retiradas Acumuladas'], mode='lines', name='Retiradas Acumuladas', line=dict(color=SUCCESS_COLOR, width=2)))
            fig = apply_plot_theme(fig, "Fluxo de Caixa e Retiradas")
            st.plotly_chart(fig, use_container_width=True)
        if final['Patrimônio Terreno'] > 0:
            st.markdown("### 🏡 Análise do Terreno")
            terreno_cols = st.columns(4)
            with terreno_cols[0]:
                render_kpi_card("Valor de Mercado", fmt_brl(final['Valor de Mercado Terreno']), INFO_COLOR, "🏠")
            with terreno_cols[1]:
                render_kpi_card("Patrimônio no Terreno", fmt_brl(final['Patrimônio Terreno']), SUCCESS_COLOR, "💰")
            with terreno_cols[2]:
                render_kpi_card("Equity Construído", fmt_brl(final['Equity Terreno Inicial']), WARNING_COLOR, "📊")
            with terreno_cols[3]:
                render_kpi_card("Juros Pagos", fmt_brl(final['Juros Acumulados']), DANGER_COLOR, "💸")

# --- Relatórios e Dados ---
elif st.session_state.active_page == 'Relatórios e Dados':
    # (copiar exatamente do Codigo__2.txt a partir da linha "elif st.session_state.active_page == 'Relatórios e Dados':")
    st.markdown("<h1 class='gradient-header'>Relatórios e Dados</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Tabelas detalhadas e exportação dos dados da simulação.</p>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("💡 Execute uma simulação primeiro para ver os relatórios.")
    else:
        df = st.session_state.simulation_df
        summary = calculate_summary_metrics(df)
        final = df.iloc[-1]
        st.markdown("### 📋 Resumo Financeiro")
        resumo_cols = st.columns(4)
        with resumo_cols[0]:
            render_report_metric("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']))
        with resumo_cols[1]:
            render_report_metric("ROI Total", f"{summary['roi_pct']:.1f}%")
        with resumo_cols[2]:
            render_report_metric("Investimento Total", fmt_brl(final['Investimento Total Acumulado']))
        with resumo_cols[3]:
            render_report_metric("Lucro Líquido", fmt_brl(summary['net_profit']))
        st.markdown("### 📊 Dados Mensais Detalhados")
        tab1, tab2, tab3 = st.tabs(["Visão Geral", "Fluxo de Caixa", "Patrimônio"])
        with tab1:
            cols_visao = ["Mês", "Ano", "Módulos Ativos", "Módulos Alugados", "Módulos Próprios", "Receita", "Gastos", "Patrimônio Líquido"]
            st.dataframe(df[cols_visao].style.format({c: fmt_brl for c in cols_visao if c in MONEY_COLS}), use_container_width=True)
        with tab2:
            cols_fluxo = ["Mês", "Receita", "Manutenção", "Aluguel", "Parcela Terreno Inicial", "Parcelas Terrenos (Novos)", "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)"]
            st.dataframe(df[cols_fluxo].style.format({c: fmt_brl for c in cols_fluxo if c in MONEY_COLS}), use_container_width=True)
        with tab3:
            cols_patrimonio = ["Mês", "Investimento Total Acumulado", "Fundo Acumulado", "Retiradas Acumuladas", "Patrimônio Líquido", "Patrimônio Terreno"]
            st.dataframe(df[cols_patrimonio].style.format({c: fmt_brl for c in cols_patrimonio if c in MONEY_COLS}), use_container_width=True)
        st.markdown("### 📤 Exportar Dados")
        col_export, _ = st.columns([1, 3])
        with col_export:
            excel_bytes = df_to_excel_bytes(df)
            st.download_button(
                label="📥 Baixar Excel",
                data=excel_bytes,
                file_name=f"simulacao_modular_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
