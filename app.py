# app.py
# Simulador Modular — v8 com Correções e Melhorias de UI

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import re
from copy import deepcopy # <-- IMPORTADO PARA CORRIGIR O CACHE

# --- PALETA DE CORES E CONFIGURAÇÕES (TEMA AZUL ESCURO) ---
PRIMARY_COLOR = "#2563EB"
SECONDARY_COLOR = "#0EA5E9"
SUCCESS_COLOR = "#10B981"
DANGER_COLOR  = "#EF4444"
WARNING_COLOR = "#F59E0B"
INFO_COLOR    = "#8B5CF6"
DARK_BACKGROUND  = "#0B1120"
LIGHT_BACKGROUND = "#0F172A"
TEXT_COLOR       = "#F1F5F9"
CARD_COLOR       = "#1E293B"
MUTED_TEXT_COLOR = "#94A3B8"
ACCENT_COLOR     = "#6366F1"
TABLE_BORDER_COLOR = "#334155"
CHART_GRID_COLOR = "#1E293B"

# --- DEFINIÇÃO DE COLUNAS PARA FORMATAÇÃO ---
MONEY_COLS = {
    "Receita", "Manutenção", "Aluguel", "Parcela Terreno Inicial", "Parcelas Terrenos (Novos)", "Gastos",
    "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado",
    "Fundo Acumulado", "Retiradas Acumuladas", "Patrimônio Líquido"
}
COUNT_COLS = {"Mês", "Ano", "Módulos Ativos", "Módulos Alugados", "Módulos Próprios", "Módulos Comprados no Ano"}


# --- FUNÇÕES HELPER ---

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def ideal_text_color(bg_hex: str) -> str:
    """Retorna cor de texto ideal baseada no fundo."""
    return TEXT_COLOR

def fmt_brl(v):
    """Formata um valor numérico como uma string de moeda brasileira de forma robusta."""
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "-"
        s = f"{float(v):,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return "R$ 0,00"

def render_kpi_card(title, value, bg_color, icon=None, subtitle=None):
    """Renderiza um cartão de KPI com design moderno."""
    text_color = ideal_text_color(bg_color)
    icon_html = f"<div style='font-size: 2rem; margin-bottom: 0.5rem;'>{icon}</div>" if icon else ""
    subtitle_html = f"<div class='kpi-card-subtitle'>{subtitle}</div>" if subtitle else ""
    
    st.markdown(f"""
        <div class="kpi-card-modern" style="background-color:{bg_color}; color:{text_color};">
            {icon_html}
            <div class="kpi-card-value-modern">{value}</div>
            <div class="kpi-card-title-modern">{title}</div>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)

def render_report_metric(title, value):
    """Renderiza uma métrica compacta para a página de relatórios."""
    st.markdown(f"""
        <div class="report-metric-card">
            <div class="report-metric-title">{title}</div>
            <div class="report-metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def df_to_excel_bytes(df: pd.DataFrame):
    """Converte um DataFrame para bytes de um arquivo Excel, formatando apenas colunas de moeda."""
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
    """Aplica um tema visual moderno aos gráficos Plotly."""
    fig.update_layout(
        title=dict(text=title or fig.layout.title.text, x=0.5, xanchor='center', font=dict(size=16, color=TEXT_COLOR, family="Arial, sans-serif")),
        height=h,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor='rgba(30, 41, 59, 0.8)', bordercolor=TABLE_BORDER_COLOR, borderwidth=1, font=dict(color=TEXT_COLOR)),
        plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR,
        font=dict(color=TEXT_COLOR, size=13, family="Arial, sans-serif"),
        xaxis=dict(gridcolor=TABLE_BORDER_COLOR, linecolor=TABLE_BORDER_COLOR, linewidth=1, tickfont=dict(color=MUTED_TEXT_COLOR)), 
        yaxis=dict(gridcolor=TABLE_BORDER_COLOR, linecolor=TABLE_BORDER_COLOR, linewidth=1, tickfont=dict(color=MUTED_TEXT_COLOR))
    )
    return fig

# ---------------------------
# CSS - Estilos da Página
# ---------------------------
st.set_page_config(page_title="Simulador Modular", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"""
    <style>
        .main .block-container {{ padding: 1.5rem 2rem; max-width: 100%; }}
        .stApp {{ background: {DARK_BACKGROUND}; }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{ background: {LIGHT_BACKGROUND}; border-right: 1px solid {TABLE_BORDER_COLOR}; }}
        [data-testid="stSidebar"] * {{ color: #E5E7EB; }}
        [data-testid="stSidebar"] h1 {{ color: #FFFFFF; font-weight: 700; font-size: 1.5rem; margin-bottom: 0.5rem; }}
        
        /* Text */
        h1, h2, h3, h4, h5, h6 {{ color: {TEXT_COLOR}; font-weight: 600; }}
        .subhead {{ color: {MUTED_TEXT_COLOR}; font-size: 1.1rem; }}
        p, label, span {{ color: {TEXT_COLOR} !important; }}
        
        /* Buttons */
        .stButton > button {{ border-radius: 12px; border: 2px solid {PRIMARY_COLOR}; background-color: {PRIMARY_COLOR}; color: white; padding: 12px 24px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.1); }}
        .stButton > button:hover {{ background-color: #1E40AF; border-color: #1E40AF; transform: translateY(-2px); box-shadow: 0 6px 12px rgba(37, 99, 235, 0.15); }}
        .stButton > button[kind="secondary"] {{ background-color: transparent; color: {PRIMARY_COLOR}; border: 2px solid {PRIMARY_COLOR}; }}
        .stButton > button[kind="secondary"]:hover {{ background-color: rgba(37, 99, 235, .08); transform: translateY(-2px); }}
        
        /* Cards */
        .card {{ background: {CARD_COLOR}; border-radius: 16px; padding: 1.5rem; border: 1px solid {TABLE_BORDER_COLOR}; box-shadow: 0 4px 20px rgba(0,0,0,.15); backdrop-filter: blur(10px); }}
        
        /* KPI Cards - Dashboard */
        .kpi-card-modern {{ border-radius: 20px; padding: 2rem 1.5rem; box-shadow: 0 8px 25px rgba(0,0,0,.2); height: 100%; text-align: center; transition: transform 0.3s ease; background: linear-gradient(135deg, {PRIMARY_COLOR} 0%, {SECONDARY_COLOR} 100%); border: 1px solid {TABLE_BORDER_COLOR}; }}
        .kpi-card-modern:hover {{ transform: translateY(-5px); box-shadow: 0 12px 30px rgba(0,0,0,.25); }}
        .kpi-card-title-modern {{ font-size: 1rem; font-weight: 600; opacity: .95; margin-top: 0.5rem; }}
        .kpi-card-value-modern {{ font-size: 2.5rem; font-weight: 800; line-height: 1.1; }}
        .kpi-card-subtitle {{ font-size: 0.85rem; opacity: .8; margin-top: 0.5rem; }}

        /* --- NOVOS ESTILOS PARA KPIs DE RELATÓRIO --- */
        .report-metric-card {{ background: {LIGHT_BACKGROUND}; border-radius: 8px; padding: 0.75rem 1rem; border: 1px solid {TABLE_BORDER_COLOR}; text-align: center; margin-bottom: 0.5rem; height: calc(100% - 0.5rem); }}
        .report-metric-title {{ font-size: 0.8rem; color: {MUTED_TEXT_COLOR}; margin-bottom: 0.25rem; text-transform: uppercase; font-weight: 600; }}
        .report-metric-value {{ font-size: 1.25rem; font-weight: 600; color: {TEXT_COLOR}; }}
        
        /* Dataframe */
        [data-testid="stDataFrame"] div[data-testid="StyledTable"] {{ border: 1px solid {TABLE_BORDER_COLOR}; border-radius: 12px; overflow: hidden; background: {CARD_COLOR}; }}
        [data-testid="stDataFrame"] th {{ background: linear-gradient(135deg, {LIGHT_BACKGROUND} 0%, {CARD_COLOR} 100%) !important; color: {TEXT_COLOR} !important; font-weight: 700 !important; border-bottom: 1px solid {TABLE_BORDER_COLOR} !important; padding: 12px 16px !important; }}
        [data-testid="stDataFrame"] td {{ padding: 10px 16px !important; border-bottom: 1px solid {TABLE_BORDER_COLOR} !important; color: {TEXT_COLOR} !important; background: {CARD_COLOR} !important; }}
        
        /* Inputs e Tabs */
        .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
        .stTabs [data-baseweb="tab"] {{ border-radius: 12px 12px 0 0; padding: 12px 24px; background-color: {LIGHT_BACKGROUND}; color: {TEXT_COLOR}; }}
        .stTabs [aria-selected="true"] {{ background-color: {PRIMARY_COLOR} !important; color: white !important; }}
        .stTextInput input, .stNumberInput input, .stSelectbox select {{ background: {CARD_COLOR} !important; color: {TEXT_COLOR} !important; border: 1px solid {TABLE_BORDER_COLOR} !important; }}
        
        /* Outros */
        .gradient-header {{ background: linear-gradient(135deg, {PRIMARY_COLOR} 0%, {SECONDARY_COLOR} 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: 700; }}
        .streamlit-expanderHeader {{ background: {CARD_COLOR}; border: 1px solid {TABLE_BORDER_COLOR}; border-radius: 8px; }}
    </style>
""", unsafe_allow_html=True)


# ---------------------------
# Motor de Simulação
# ---------------------------
@st.cache_data
def simulate(_config, reinvestment_strategy):
    # (O código desta função permanece inalterado)
    cfg_rented = _config['rented']
    cfg_owned = _config['owned']
    cfg_global = _config['global']
    months = cfg_global['years'] * 12
    rows = []
    modules_rented = cfg_rented['modules_init']
    modules_owned = cfg_owned['modules_init']
    caixa = 0.0
    investimento_total = (modules_rented * cfg_rented['cost_per_module']) + (modules_owned * cfg_owned['cost_per_module'])
    fundo_ac = 0.0
    retiradas_ac = 0.0
    valor_terrenos_adicionais = 0.0
    compra_intercalada_counter = 0
    correction_rate_pct = cfg_global.get('general_correction_rate', 0.0) / 100.0
    custo_modulo_atual_rented = cfg_rented['cost_per_module']
    custo_modulo_atual_owned = cfg_owned['cost_per_module']
    receita_p_mod_rented = cfg_rented['revenue_per_module']
    receita_p_mod_owned = cfg_owned['revenue_per_module']
    manut_p_mod_rented = cfg_rented['maintenance_per_module']
    manut_p_mod_owned = cfg_owned['maintenance_per_module']
    aluguel_p_novo_mod = cfg_rented['rent_per_new_module']
    parcela_p_novo_terreno = cfg_owned['monthly_land_plot_parcel']
    aluguel_mensal_corrente = cfg_rented['rent_value']
    parcelas_terrenos_novos_mensal_corrente = 0.0
    valor_entrada_terreno = 0.0
    parcela_terreno_inicial_atual = 0.0
    if cfg_owned['land_total_value'] > 0:
        valor_entrada_terreno = cfg_owned['land_total_value'] * (cfg_owned['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_owned['land_total_value'] - valor_entrada_terreno
        if cfg_owned['land_installments'] > 0:
            parcela_terreno_inicial_atual = valor_financiado / cfg_owned['land_installments']
        investimento_total += valor_entrada_terreno
    for m in range(1, months + 1):
        receita = (modules_rented * receita_p_mod_rented) + (modules_owned * receita_p_mod_owned)
        manut = (modules_rented * manut_p_mod_rented) + (modules_owned * manut_p_mod_owned)
        novos_modulos_comprados = 0
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes
        lucro_operacional_mes = receita - manut - aluguel_mensal_corrente - parcelas_terrenos_novos_mensal_corrente
        parcela_terreno_inicial_mes = 0.0
        if cfg_owned['land_total_value'] > 0 and m <= cfg_owned['land_installments']:
            parcela_terreno_inicial_mes = parcela_terreno_inicial_atual
            investimento_total += parcela_terreno_inicial_mes
        if m == 1:
            caixa -= valor_entrada_terreno
        caixa += lucro_operacional_mes
        caixa -= parcela_terreno_inicial_mes
        fundo_mes_total, retirada_mes_efetiva = 0.0, 0.0
        if lucro_operacional_mes > 0:
            base_distribuicao = lucro_operacional_mes
            retirada_potencial = sum(base_distribuicao * (r['percentual'] / 100.0) for r in cfg_global['retiradas'] if m >= r['mes'])
            fundo_mes_total = sum(base_distribuicao * (f['percentual'] / 100.0) for f in cfg_global['fundos'] if m >= f['mes'])
            excesso = 0.0
            if cfg_global['max_withdraw_value'] > 0 and retirada_potencial > cfg_global['max_withdraw_value']:
                excesso = retirada_potencial - cfg_global['max_withdraw_value']
                retirada_mes_efetiva = cfg_global['max_withdraw_value']
            else:
                retirada_mes_efetiva = retirada_potencial
            fundo_mes_total += excesso
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total
        if m > 0 and m % 12 == 0:
            custo_expansao = 0.0
            if reinvestment_strategy == 'buy':
                custo_expansao = custo_modulo_atual_owned
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
            elif reinvestment_strategy == 'alternate':
                custo_expansao = custo_modulo_atual_owned if compra_intercalada_counter % 2 == 0 else custo_modulo_atual_rented
            if custo_expansao > 0 and caixa >= custo_expansao:
                novos_modulos_comprados = int(caixa // custo_expansao)
                if novos_modulos_comprados > 0:
                    custo_da_compra = novos_modulos_comprados * custo_expansao
                    caixa -= custo_da_compra
                    investimento_total += custo_da_compra
                    if reinvestment_strategy == 'buy':
                        modules_owned += novos_modulos_comprados
                        parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
                        valor_terrenos_adicionais += novos_modulos_comprados * cfg_owned['land_value_per_module']
                    elif reinvestment_strategy == 'rent':
                        modules_rented += novos_modulos_comprados
                        aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
                    elif reinvestment_strategy == 'alternate':
                        for _ in range(novos_modulos_comprados):
                            if compra_intercalada_counter % 2 == 0:
                                modules_owned += 1
                                parcelas_terrenos_novos_mensal_corrente += parcela_p_novo_terreno
                                valor_terrenos_adicionais += cfg_owned['land_value_per_module']
                            else:
                                modules_rented += 1
                                aluguel_mensal_corrente += aluguel_p_novo_mod
                            compra_intercalada_counter += 1
            correction_factor = 1 + correction_rate_pct
            custo_modulo_atual_owned *= correction_factor
            custo_modulo_atual_rented *= correction_factor
            receita_p_mod_rented *= correction_factor
            receita_p_mod_owned *= correction_factor
            manut_p_mod_rented *= correction_factor
            manut_p_mod_owned *= correction_factor
            aluguel_mensal_corrente *= correction_factor
            parcelas_terrenos_novos_mensal_corrente *= correction_factor
            parcela_terreno_inicial_atual *= correction_factor
            aluguel_p_novo_mod *= correction_factor
            parcela_p_novo_terreno *= correction_factor
        patrimonio_liquido = (modules_owned * custo_modulo_atual_owned) + (modules_rented * custo_modulo_atual_rented) + caixa + fundo_ac + cfg_owned['land_total_value'] + valor_terrenos_adicionais
        rows.append({
            "Mês": m, "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules_owned + modules_rented,
            "Módulos Alugados": modules_rented, "Módulos Próprios": modules_owned,
            "Receita": receita, "Manutenção": manut, "Aluguel": aluguel_mensal_corrente,
            "Parcela Terreno Inicial": parcela_terreno_inicial_mes,
            "Parcelas Terrenos (Novos)": parcelas_terrenos_novos_mensal_corrente,
            "Gastos": manut + aluguel_mensal_corrente + parcela_terreno_inicial_mes + parcelas_terrenos_novos_mensal_corrente,
            "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total,
            "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Patrimônio Líquido": patrimonio_liquido
        })
    return pd.DataFrame(rows)

# ---------------------------
# Inicialização e Gerenciamento do Estado
# ---------------------------
def get_default_config():
    # (O código desta função permanece inalterado)
    return {
        'rented': { 'modules_init': 1, 'cost_per_module': 75000.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_per_new_module': 950.0 },
        'owned': { 'modules_init': 0, 'cost_per_module': 75000.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'monthly_land_plot_parcel': 0.0, 'land_value_per_module': 200.0, 'land_total_value': 0.0, 'land_down_payment_pct': 20.0, 'land_installments': 120 },
        'global': { 'years': 15, 'max_withdraw_value': 50000.0, 'general_correction_rate': 5.0, 'aportes': [], 'retiradas': [], 'fundos': [] }
    }

if 'config' not in st.session_state:
    st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state: st.session_state.comparison_df = pd.DataFrame()
if 'active_page' not in st.session_state: st.session_state.active_page = 'Dashboard'


# ---------------------------
# BARRA LATERAL E NAVEGAÇÃO
# ---------------------------
with st.sidebar:
    st.markdown("<h1>📊 Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8; margin-bottom: 2rem;'>Projeção com reinvestimento inteligente</p>", unsafe_allow_html=True)
    nav_options = { "Dashboard": "📈", "Relatórios e Dados": "📋", "Configurações": "⚙️" }
    selected = st.radio("Menu Principal", list(nav_options.keys()), key="navigation_radio", label_visibility="collapsed", format_func=lambda x: f"{nav_options[x]} {x}")
    st.session_state.active_page = selected
    st.markdown("---")
    st.markdown("<p style='color: #64748B; font-size: 0.85rem;'>Desenvolvido com Streamlit</p>", unsafe_allow_html=True)


# ---------------------------
# PÁGINA DE CONFIGURAÇÕES
# ---------------------------
if st.session_state.active_page == 'Configurações':
    # (O código desta página permanece inalterado)
    st.markdown("<h1 class='gradient-header'>Configurações de Investimento</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Ajuste os parâmetros da simulação financeira e adicione eventos.</p>", unsafe_allow_html=True)
    if st.button("🔄 Resetar Configurações", type="secondary"):
        st.session_state.config = get_default_config()
        st.rerun()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏢 Investimento com Terreno Alugado")
    c1, c2 = st.columns(2)
    cfg_r = st.session_state.config['rented']
    cfg_r['modules_init'] = c1.number_input("Módulos iniciais (alugados)", 0, value=cfg_r['modules_init'], key="rent_mod_init")
    cfg_r['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_r['cost_per_module'], format="%.2f", key="rent_cost_mod")
    cfg_r['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_r['revenue_per_module'], format="%.2f", key="rent_rev_mod")
    cfg_r['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_r['maintenance_per_module'], format="%.2f", key="rent_maint_mod")
    cfg_r['rent_value'] = c2.number_input("Aluguel mensal fixo (R$)", 0.0, value=cfg_r['rent_value'], format="%.2f", key="rent_base_rent")
    cfg_r['rent_per_new_module'] = cfg_r['maintenance_per_module'] + cfg_r['rent_value']
    c2.number_input("Custo de aluguel por novo módulo (R$)", 0.0, value=cfg_r['rent_per_new_module'], format="%.2f", key="rent_new_rent", disabled=True, help="Preenchido automaticamente (Manutenção + Aluguel Fixo).")
    st.markdown('</div><br>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏠 Investimento com Terreno Próprio")
    cfg_o = st.session_state.config['owned']
    st.markdown("###### Financiamento do Terreno Inicial (Opcional)")
    cfg_o['land_total_value'] = st.number_input("Valor total do terreno inicial (R$)", 0.0, value=cfg_o['land_total_value'], format="%.2f", key="own_total_land_val")
    if cfg_o['land_total_value'] > 0:
        c1_fin, c2_fin = st.columns(2)
        cfg_o['land_down_payment_pct'] = c1_fin.number_input("Entrada (%)", 0.0, 100.0, value=cfg_o['land_down_payment_pct'], format="%.1f", key="own_down_pay")
        cfg_o['land_installments'] = c1_fin.number_input("Quantidade de parcelas", 1, 480, value=cfg_o['land_installments'], key="own_install")
        valor_entrada = cfg_o['land_total_value'] * (cfg_o['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_o['land_total_value'] - valor_entrada
        valor_parcela = valor_financiado / cfg_o['land_installments'] if cfg_o['land_installments'] > 0 else 0
        c2_fin.metric("Valor da Entrada", fmt_brl(valor_entrada))
        c2_fin.metric("Valor da Parcela", fmt_brl(valor_parcela))
    st.markdown("---")
    st.markdown("###### Parâmetros do Módulo Próprio")
    c1, c2 = st.columns(2)
    cfg_o['modules_init'] = c1.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
    cfg_o['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
    cfg_o['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
    cfg_o['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
    cfg_o['monthly_land_plot_parcel'] = c2.number_input("Parcela mensal por novo terreno (R$)", 0.0, value=cfg_o.get('monthly_land_plot_parcel', 0.0), format="%.2f", key="own_land_parcel", help="Este valor será usado para cada novo módulo próprio adquirido.")
    cfg_o['land_value_per_module'] = cfg_o['monthly_land_plot_parcel'] + cfg_o['maintenance_per_module']
    st.markdown('</div><br>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🌐 Parâmetros Globais")
    cfg_g = st.session_state.config['global']
    c1, c2 = st.columns(2)
    cfg_g['years'] = c1.number_input("Horizonte de investimento (anos)", 1, 50, value=cfg_g['years'])
    cfg_g['general_correction_rate'] = c1.number_input("Correção Anual Geral (Inflação %)", 0.0, 100.0, value=cfg_g.get('general_correction_rate', 5.0), format="%.1f", key="global_corr_rate", help="Taxa anual que corrige receitas, manutenções, aluguéis e parcelas.")
    cfg_g['max_withdraw_value'] = c2.number_input("Valor máximo de retirada mensal (R$)", 0.0, value=cfg_g['max_withdraw_value'], format="%.2f", help="Teto para retiradas baseadas em % do lucro.")
    st.markdown('</div><br>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📅 Eventos Financeiros")
    st.markdown("<h6>Aportes (investimentos pontuais)</h6>", unsafe_allow_html=True)
    for i, aporte in enumerate(st.session_state.config['global']['aportes']):
        cols = st.columns([2, 3, 1])
        aporte['mes'] = cols[0].number_input("Mês", 1, None, aporte['mes'], key=f"aporte_mes_{i}")
        aporte['valor'] = cols[1].number_input("Valor (R$)", 0.0, None, aporte['valor'], format="%.2f", key=f"aporte_valor_{i}")
        if cols[2].button("Remover", key=f"aporte_remover_{i}", type="secondary"): st.session_state.config['global']['aportes'].pop(i); st.rerun()
    if st.button("Adicionar Aporte"): st.session_state.config['global']['aportes'].append({"mes": 1, "valor": 10000.0}); st.rerun()
    st.markdown("---")
    st.markdown("<h6>Retiradas (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, retirada in enumerate(st.session_state.config['global']['retiradas']):
        cols = st.columns([2, 3, 1])
        retirada['mes'] = cols[0].number_input("Mês início", 1, None, retirada['mes'], key=f"retirada_mes_{i}")
        retirada['percentual'] = cols[1].number_input("% do lucro", 0.0, 100.0, retirada['percentual'], format="%.1f", key=f"retirada_pct_{i}")
        if cols[2].button("Remover", key=f"retirada_remover_{i}", type="secondary"): st.session_state.config['global']['retiradas'].pop(i); st.rerun()
    if st.button("Adicionar Retirada"): st.session_state.config['global']['retiradas'].append({"mes": 1, "percentual": 30.0}); st.rerun()
    st.markdown("---")
    st.markdown("<h6>Fundos de Reserva (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, fundo in enumerate(st.session_state.config['global']['fundos']):
        cols = st.columns([2, 3, 1])
        fundo['mes'] = cols[0].number_input("Mês início", 1, None, fundo['mes'], key=f"fundo_mes_{i}")
        fundo['percentual'] = cols[1].number_input("% do lucro", 0.0, 100.0, fundo['percentual'], format="%.1f", key=f"fundo_pct_{i}")
        if cols[2].button("Remover", key=f"fundo_remover_{i}", type="secondary"): st.session_state.config['global']['fundos'].pop(i); st.rerun()
    if st.button("Adicionar Fundo"): st.session_state.config['global']['fundos'].append({"mes": 1, "percentual": 10.0}); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------
# PÁGINA DO DASHBOARD
# ---------------------------
if st.session_state.active_page == 'Dashboard':
    st.markdown("<h1 class='gradient-header'>Dashboard Estratégico</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Simule uma estratégia de reinvestimento ou compare todas as abordagens</p>", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🎯 Estratégias de Reinvestimento")
        strat_cols = st.columns(3)
        
        # --- CORREÇÃO DO CACHE: Usando deepcopy para garantir que a simulação seja reexecutada ---
        config_copy = deepcopy(st.session_state.config)

        if strat_cols[0].button("**🏠 Comprar Novos**\n\nAquisição de terrenos próprios", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação de compra..."):
                st.session_state.simulation_df = simulate(config_copy, 'buy')
                st.session_state.comparison_df = pd.DataFrame()
                
        if strat_cols[1].button("**🏢 Alugar Novos**\n\nExpansão com aluguel de terrenos", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação de aluguel..."):
                st.session_state.simulation_df = simulate(config_copy, 'rent')
                st.session_state.comparison_df = pd.DataFrame()
                
        if strat_cols[2].button("**🔄 Intercalar Novos**\n\nMix entre compra e aluguel", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação intercalada..."):
                st.session_state.simulation_df = simulate(config_copy, 'alternate')
                st.session_state.comparison_df = pd.DataFrame()
                
        st.markdown("<hr style='margin: 1.5rem 0; border-color: #334155;'>", unsafe_allow_html=True)
        
        if st.button("**📊 Comparar Todas as Estratégias**", use_container_width=True):
            with st.spinner("Calculando as três simulações..."):
                df_buy = simulate(config_copy, 'buy'); df_buy['Estratégia'] = 'Comprar'
                df_rent = simulate(config_copy, 'rent'); df_rent['Estratégia'] = 'Alugar'
                df_alt = simulate(config_copy, 'alternate'); df_alt['Estratégia'] = 'Intercalar'
                st.session_state.comparison_df = pd.concat([df_buy, df_rent, df_alt])
                st.session_state.simulation_df = pd.DataFrame()
                
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.comparison_df.empty:
        # (Seção de comparação permanece inalterada)
        st.markdown("<h2 class='gradient-header'>📈 Análise Comparativa de Estratégias</h2>", unsafe_allow_html=True)
        df_comp = st.session_state.comparison_df
        final_buy = df_comp[df_comp['Estratégia'] == 'Comprar'].iloc[-1]
        final_rent = df_comp[df_comp['Estratégia'] == 'Alugar'].iloc[-1]
        final_alt = df_comp[df_comp['Estratégia'] == 'Intercalar'].iloc[-1]
        k1, k2, k3, k4 = st.columns(4)
        with k1: render_kpi_card("Comprar", fmt_brl(final_buy['Patrimônio Líquido']), PRIMARY_COLOR, "🏠", "Patrimônio Final")
        with k2: render_kpi_card("Alugar", fmt_brl(final_rent['Patrimônio Líquido']), INFO_COLOR, "🏢", "Patrimônio Final")
        with k3: render_kpi_card("Intercalar", fmt_brl(final_alt['Patrimônio Líquido']), WARNING_COLOR, "🔄", "Patrimônio Final")
        with k4:
            best_strategy = pd.Series({'Comprar': final_buy['Patrimônio Líquido'], 'Alugar': final_rent['Patrimônio Líquido'], 'Intercalar': final_alt['Patrimônio Líquido']}).idxmax()
            render_kpi_card("Melhor Estratégia", best_strategy, SUCCESS_COLOR, "🏆", "Recomendação")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📊 Evolução Comparativa")
        metric_options = ["Patrimônio Líquido", "Módulos Ativos", "Retiradas Acumuladas", "Fundo Acumulado", "Caixa (Final Mês)"]
        selected_metric = st.selectbox("Selecione uma métrica para comparar:", options=metric_options)
        fig_comp = px.line(df_comp, x="Mês", y=selected_metric, color='Estratégia', color_discrete_map={'Comprar': PRIMARY_COLOR, 'Alugar': INFO_COLOR, 'Intercalar': WARNING_COLOR})
        apply_plot_theme(fig_comp, f'Comparativo de {selected_metric}', h=450)
        st.plotly_chart(fig_comp, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif not st.session_state.simulation_df.empty:
        # (Seção de resultados principais permanece com a correção anterior)
        df = st.session_state.simulation_df; final = df.iloc[-1]
        st.markdown("<h2 class='gradient-header'>📊 Resultados da Simulação</h2>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        with k1: render_kpi_card("Patrimônio Final", fmt_brl(final['Patrimônio Líquido']), PRIMARY_COLOR, "💰", "Acumulado total")
        with k2: render_kpi_card("Retiradas Totais", fmt_brl(final['Retiradas Acumuladas']), DANGER_COLOR, "💸", "Valor sacado")
        with k3: render_kpi_card("Fundo de Reserva", fmt_brl(final['Fundo Acumulado']), INFO_COLOR, "🛡️", "Proteção financeira")
        with k4: render_kpi_card("Módulos Ativos", f"{int(final['Módulos Ativos'])}", SUCCESS_COLOR, "📦", "Crescimento do negócio")
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("##### 📈 Evolução do Patrimônio")
            fig_pat = go.Figure()
            r, g, b = _hex_to_rgb(PRIMARY_COLOR)
            fig_pat.add_trace(go.Scatter(x=df["Mês"], y=df["Patrimônio Líquido"], name="Patrimônio", line=dict(color=PRIMARY_COLOR, width=4), fill='tozeroy', fillcolor=f'rgba({r}, {g}, {b}, 0.2)'))
            apply_plot_theme(fig_pat, "Crescimento do Patrimônio Líquido")
            st.plotly_chart(fig_pat, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("##### 🥧 Distribuição Final")
            dist_data = {"Valores": [final['Retiradas Acumuladas'], final['Fundo Acumulado'], final['Caixa (Final Mês)']], "Categorias": ["Retiradas", "Fundo Total", "Caixa Final"]}
            fig_pie = px.pie(dist_data, values="Valores", names="Categorias", color="Categorias", color_discrete_map={"Retiradas": DANGER_COLOR, "Fundo Total": INFO_COLOR, "Caixa Final": WARNING_COLOR}, hole=.5)
            apply_plot_theme(fig_pie, "Distribuição dos Recursos")
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("## 🚀 Comece sua Simulação\n\n**Selecione uma das estratégias acima para iniciar a análise.**")
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# PÁGINA DE RELATÓRIOS E DADOS
# ---------------------------
if st.session_state.active_page == 'Relatórios e Dados':
    st.markdown("<h1 class='gradient-header'>Relatórios e Dados</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Explore os dados detalhados da simulação mês a mês</p>", unsafe_allow_html=True)
    
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty: df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty: df_to_show = st.session_state.simulation_df

    if df_to_show.empty:
        st.info("👈 Vá para a página 'Dashboard' para executar uma simulação primeiro.")
    else:
        df_analysis_base = df_to_show
        selected_strategy = None
        if 'Estratégia' in df_analysis_base.columns:
            selected_strategy = st.selectbox("Selecione a estratégia para análise:", df_analysis_base['Estratégia'].unique(), key="relat_strategy_select")
            df_analysis = df_analysis_base[df_analysis_base['Estratégia'] == selected_strategy].copy()
        else:
            df_analysis = df_analysis_base.copy()

        main_cols = st.columns([6, 4])
        with main_cols[0], st.container(border=True):
            st.subheader("📅 Análise por Ponto no Tempo")
            c1, c2 = st.columns(2)
            anos_disponiveis = sorted(df_analysis['Ano'].unique())
            selected_year = c1.selectbox("Selecione o ano", options=anos_disponiveis)
            subset = df_analysis[df_analysis['Ano'] == selected_year].copy()
            if not subset.empty:
                months_in_year = sorted([((m - 1) % 12) + 1 for m in subset['Mês'].unique()])
                selected_month_label = c2.selectbox("Selecione o mês", options=months_in_year)
                filtered = subset[((subset["Mês"] - 1) % 12) + 1 == selected_month_label]
                if not filtered.empty:
                    data_point = filtered.iloc[0]
                    st.markdown("---")
                    # --- ATUALIZAÇÃO: Substituindo st.metric pelos novos KPIs ---
                    res_cols = st.columns(4)
                    with res_cols[0]:
                        render_report_metric("Total de Módulos", f"{int(data_point['Módulos Ativos'])}")
                        render_report_metric("Patrimônio Líquido", fmt_brl(data_point['Patrimônio Líquido']))
                    with res_cols[1]:
                        render_report_metric("Caixa no Mês", fmt_brl(data_point['Caixa (Final Mês)']))
                        render_report_metric("Investimento Total", fmt_brl(data_point['Investimento Total Acumulado']))
                    with res_cols[2]:
                        render_report_metric("Fundo (Mês)", fmt_brl(data_point['Fundo (Mês)']))
                        render_report_metric("Fundo Acumulado", fmt_brl(data_point['Fundo Acumulado']))
                    with res_cols[3]:
                        render_report_metric("Retirada (Mês)", fmt_brl(data_point['Retirada (Mês)']))
                        render_report_metric("Retiradas Acumuladas", fmt_brl(data_point['Retiradas Acumuladas']))
        with main_cols[1], st.container(border=True):
            st.subheader("📊 Resumo Gráfico do Mês")
            if 'data_point' in locals() and not filtered.empty:
                chart_data = pd.DataFrame({"Categoria": ["Receita", "Gastos", "Retirada", "Fundo"], "Valor": [ data_point['Receita'], data_point['Gastos'], data_point['Retirada (Mês)'], data_point['Fundo (Mês)']]})
                fig_monthly = px.bar(chart_data, x="Categoria", y="Valor", text_auto='.2s', color="Categoria", color_discrete_map={"Receita": SUCCESS_COLOR, "Gastos": WARNING_COLOR, "Retirada": DANGER_COLOR, "Fundo": INFO_COLOR})
                apply_plot_theme(fig_monthly, f"Fluxo Financeiro - Mês {int(data_point['Mês'])}")
                st.plotly_chart(fig_monthly, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("Selecione um ponto no tempo para ver o gráfico.")
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("📋 Tabela Completa da Simulação")
            # (O restante do código da página permanece inalterado)
            all_columns = df_analysis.columns.tolist()
            state_key = f"column_visibility_{slug(selected_strategy or 'default')}"
            if state_key not in st.session_state or set(st.session_state[state_key].keys()) != set(all_columns):
                default_cols = ['Mês', 'Ano', 'Módulos Ativos', 'Receita', 'Gastos', 'Caixa (Final Mês)', 'Patrimônio Líquido']
                st.session_state[state_key] = {c: (c in default_cols) for c in all_columns}
            with st.expander("Exibir/Ocultar Colunas da Tabela"):
                vis_map = st.session_state[state_key]
                grid_cols = st.columns(5)
                for i, col_name in enumerate(all_columns):
                    with grid_cols[i % 5]:
                        new_on = st.toggle(col_name, value=vis_map.get(col_name, False), key=f"tg_{slug(selected_strategy or 'default')}_{slug(col_name)}")
                        if new_on != vis_map.get(col_name): vis_map[col_name] = new_on; st.session_state[state_key] = vis_map; st.rerun()
            cols_to_show = [c for c, v in st.session_state[state_key].items() if v]
            if not cols_to_show:
                st.warning("Selecione ao menos uma coluna para visualizar a tabela.")
            else:
                page_size = 12
                total_pages = (len(df_analysis) - 1) // page_size + 1
                if 'page' not in st.session_state: st.session_state.page = 0
                if st.session_state.page >= total_pages: st.session_state.page = 0
                start_idx = st.session_state.page * page_size
                df_display = df_analysis.iloc[start_idx:start_idx + page_size].copy()
                for col in (MONEY_COLS & set(df_display.columns)): df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
                st.dataframe( df_display[cols_to_show], use_container_width=True, hide_index=True )
                page_cols = st.columns([1, 1, 8])
                if page_cols[0].button("Anterior", disabled=(st.session_state.page == 0), type="secondary"): st.session_state.page -= 1; st.rerun()
                if page_cols[1].button("Próxima", disabled=(st.session_state.page >= total_pages - 1), type="secondary"): st.session_state.page += 1; st.rerun()
                page_cols[2].markdown(f"<div style='padding-top:10px; color:{MUTED_TEXT_COLOR}'>Página {st.session_state.page + 1} de {total_pages}</div>", unsafe_allow_html=True)
            excel_bytes = df_to_excel_bytes(df_analysis)
            st.download_button("📥 Baixar Relatório Completo (Excel)", data=excel_bytes, file_name=f"relatorio_simulacao_{slug(selected_strategy or 'geral')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
