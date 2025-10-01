# app.py
# Simulador Modular — v10.5 com Correção Crítica de Patrimônio e Financiamento (Tabela Price)

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

# --- PALETA DE CORES ---
PRIMARY_COLOR    = "#F5A623"      # Laranja para ações
SECONDARY_COLOR  = "#0EA5E9"      # Azul claro para gráficos
SUCCESS_COLOR    = "#10B981"      # Verde
DANGER_COLOR     = "#EF4444"      # Vermelho
WARNING_COLOR    = "#F59E0B"      # Amarelo
INFO_COLOR       = "#3B82F6"      # Azul info
APP_BG           = "#F0F9FF"      # Fundo azul bem claro
SIDEBAR_BG       = "#E0F2FE"      # Sidebar azul claro
CARD_COLOR       = "#FFFFFF"      # Cards brancos
TEXT_COLOR       = "#0F172A"      # Texto escuro
MUTED_TEXT_COLOR = "#334155"      # Texto secundário
TABLE_BORDER_COLOR = "#CBD5E1"
CHART_GRID_COLOR = "#E2E8F0"
KPI_BG_COLOR     = "#0369A1"      # Azul escuro para KPIs de destaque

# --- DEFINIÇÃO DE COLUNAS PARA FORMATAÇÃO ---
MONEY_COLS = {
    "Receita", "Manutenção", "Aluguel", "Parcela Terreno Inicial", "Parcelas Terrenos (Novos)", "Gastos",
    "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado",
    "Fundo Acumulado", "Retiradas Acumuladas", "Patrimônio Líquido", "Juros (Mês)",
    "Amortização (Mês)", "Saldo Devedor", "Patrimônio do Terreno", "Valor de Mercado do Terreno",
    "Juros Acumulados", "Amortização Acumulada"
}
COUNT_COLS = {"Mês", "Ano", "Módulos Ativos", "Módulos Alugados", "Módulos Próprios", "Módulos Comprados no Ano"}

# ---------------------------
# Funções Auxiliares (Helpers)
# ---------------------------
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def fmt_brl(v):
    """Formata um valor numérico como moeda brasileira de forma robusta."""
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "-"
        s = f"{float(v):,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def render_kpi_card(title, value, bg_color=KPI_BG_COLOR, icon=None, subtitle=None, dark_text=False):
    """Renderiza um cartão de KPI moderno."""
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
    """Renderiza uma métrica formatada para relatórios."""
    st.markdown(f"""
        <div class="report-metric-card">
            <div class="report-metric-title">{title}</div>
            <div class="report-metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def calculate_summary_metrics(df):
    """Calcula os principais KPIs de resumo da simulação."""
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
    """Converte um DataFrame para um arquivo Excel em memória."""
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
    """Cria um slug amigável para URLs ou chaves a partir de uma string."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:60]

def apply_plot_theme(fig, title=None, h=420):
    """Aplica um tema visual consistente aos gráficos Plotly."""
    fig.update_layout(
        title=dict(text=title or fig.layout.title.text, x=0.5, xanchor='center', font=dict(size=16, color=TEXT_COLOR)),
        height=h,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor='rgba(255,255,255,0.85)', bordercolor=TABLE_BORDER_COLOR, borderwidth=1,
            font=dict(color=TEXT_COLOR)
        ),
        plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font=dict(color=TEXT_COLOR),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR)),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR))
    )
    return fig

def compute_cache_key(cfg: dict) -> str:
    """Gera um hash MD5 da configuração para invalidar o cache do Streamlit."""
    payload = json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()

# ---------------------------
# CSS e Configuração da Página
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
            transition: transform 0.3s ease; background: {KPI_BG_COLOR};
        }}
        .kpi-card-modern:hover {{ transform: translateY(-5px); }}
        .kpi-card-title-modern {{ font-size: 0.95rem; font-weight: 600; opacity: .95; margin-top: 0.5rem; color: white; }}
        .kpi-card-value-modern {{ font-size: 2rem; font-weight: 800; line-height: 1.1; color: white; }}
        .kpi-card-subtitle {{ font-size: 0.85rem; opacity: .9; margin-top: 0.35rem; color: white; }}
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
# Motor de Simulação (v10.5 — CORRIGIDO)
# ---------------------------
@st.cache_data(show_spinner=False)
def simulate(_config, reinvestment_strategy, cache_key: str):
    cfg_rented = _config['rented']
    cfg_owned = _config['owned']
    cfg_global = _config['global']
    months = cfg_global['years'] * 12
    rows = []

    # --- Variáveis de Estado ---
    modules_rented = cfg_rented['modules_init']
    modules_owned = cfg_owned['modules_init']
    caixa = 0.0
    fundo_ac = 0.0
    retiradas_ac = 0.0
    juros_acumulados = 0.0
    amortizacao_acumulada = 0.0
    compra_intercalada_counter = 0

    # Capital que entrou no negócio ( aportes + custos de implantação)
    investimento_total = (
        modules_rented * cfg_rented['cost_per_module'] +
        modules_owned * cfg_owned['cost_per_module']
    )
    # Valor dos ativos que a empresa possui
    historical_value_owned = modules_owned * cfg_owned['cost_per_module']

    # --- Configuração do Financiamento (Tabela Price) ---
    saldo_devedor = 0.0
    parcela_mensal_fixa = 0.0
    valor_compra_terreno = cfg_owned['land_total_value']

    if valor_compra_terreno > 0 and cfg_owned['land_installments'] > 0:
        valor_entrada = valor_compra_terreno * (cfg_owned['land_down_payment_pct'] / 100.0)
        valor_financiado = valor_compra_terreno - valor_entrada
        saldo_devedor = valor_financiado
        investimento_total += valor_entrada

        taxa_juros_mensal = (cfg_owned.get('land_interest_rate', 8.0) / 100.0) / 12
        n_parcelas = cfg_owned['land_installments']

        if n_parcelas > 0:
            if taxa_juros_mensal > 0:
                # Fórmula da Parcela Fixa (PMT / Tabela Price)
                parcela_mensal_fixa = valor_financiado * (taxa_juros_mensal * (1 + taxa_juros_mensal)**n_parcelas) / ((1 + taxa_juros_mensal)**n_parcelas - 1)
            else: # Juros zero
                parcela_mensal_fixa = valor_financiado / n_parcelas

    # --- Variáveis de Custos e Receitas Correntes ---
    correction_rate_pct = cfg_global.get('general_correction_rate', 0.0) / 100.0
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

    # --- Laço Principal da Simulação ---
    for m in range(1, months + 1):
        receita = (modules_rented * receita_p_mod_rented) + (modules_owned * receita_p_mod_owned)
        manut = (modules_rented * manut_p_mod_rented) + (modules_owned * manut_p_mod_owned)
        novos_modulos_comprados = 0
        
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes

        # --- Pagamento do Financiamento (Lógica Price Corrigida) ---
        juros_mes = 0.0
        amortizacao_mes = 0.0
        parcela_paga_mes = 0.0
        if saldo_devedor > 0:
            parcela_paga_mes = min(parcela_mensal_fixa, saldo_devedor * (1.0 + taxa_juros_mensal))
            if parcela_paga_mes > 0:
                juros_mes = saldo_devedor * taxa_juros_mensal
                amortizacao_mes = parcela_paga_mes - juros_mes
                
                saldo_devedor -= amortizacao_mes
                juros_acumulados += juros_mes
                amortizacao_acumulada += amortizacao_mes

        # --- Fluxo de Caixa ---
        gastos_operacionais = manut + aluguel_mensal_corrente + juros_mes + parcelas_terrenos_novos_mensal_corrente
        lucro_antes_distribuicao = receita - gastos_operacionais
        caixa += lucro_antes_distribuicao
        caixa -= amortizacao_mes

        # --- Distribuição de Lucro ---
        fundo_mes_total = 0.0
        retirada_mes_efetiva = 0.0
        if lucro_antes_distribuicao > 0:
            base_distribuicao = lucro_antes_distribuicao
            retirada_potencial = sum(base_distribuicao * (r['percentual'] / 100.0) for r in cfg_global['retiradas'] if m >= r['mes'])
            fundo_potencial = sum(base_distribuicao * (f['percentual'] / 100.0) for f in cfg_global['fundos'] if m >= f['mes'])

            if cfg_global['max_withdraw_value'] > 0 and retirada_potencial > cfg_global['max_withdraw_value']:
                retirada_mes_efetiva = cfg_global['max_withdraw_value']
                fundo_mes_total = fundo_potencial
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
                    retirada_mes_efetiva, fundo_mes_total = 0.0, 0.0
        
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total

        # --- Reinvestimento Anual ---
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
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
                if caixa >= custo_expansao and custo_expansao > 0:
                    novos_modulos_comprados = int(caixa // custo_expansao)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo_expansao
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
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
                            modules_rented += novos_modulos_comprados
                            aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
                            compra_intercalada_counter += novos_modulos_comprados

            # Correção monetária anual
            correction_factor = 1 + correction_rate_pct
            custo_modulo_atual_owned *= correction_factor
            custo_modulo_atual_rented *= correction_factor
            receita_p_mod_rented *= correction_factor
            receita_p_mod_owned *= correction_factor
            manut_p_mod_rented *= correction_factor
            manut_p_mod_owned *= correction_factor
            aluguel_mensal_corrente *= correction_factor
            parcelas_terrenos_novos_mensal_corrente *= correction_factor
            aluguel_p_novo_mod *= correction_factor
            parcela_p_novo_terreno *= correction_factor

        # --- CÁLCULO DE PATRIMÔNIO CORRIGIDO ---
        land_appreciation_rate_pct = cfg_global.get('land_appreciation_rate', 3.0) / 100.0
        valor_mercado_terreno = valor_compra_terreno * ((1 + land_appreciation_rate_pct) ** (m / 12))
        patrimonio_do_terreno = valor_mercado_terreno - saldo_devedor if valor_compra_terreno > 0 else 0

        # CORREÇÃO 1: Custo de módulos alugados NÃO é um ativo. Foi removido.
        # CORREÇÃO 2: A dívida ('passivos') NÃO é subtraída duas vezes. Já está contida em 'patrimonio_do_terreno'.
        ativos = historical_value_owned + caixa + fundo_ac + patrimonio_do_terreno
        patrimonio_liquido = ativos

        rows.append({
            "Mês": m, "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules_owned + modules_rented,
            "Módulos Alugados": modules_rented, "Módulos Próprios": modules_owned,
            "Receita": receita, "Manutenção": manut, "Aluguel": aluguel_mensal_corrente,
            "Juros (Mês)": juros_mes, "Amortização (Mês)": amortizacao_mes,
            "Parcela Terreno Inicial": parcela_paga_mes,
            "Parcelas Terrenos (Novos)": parcelas_terrenos_novos_mensal_corrente,
            "Gastos": gastos_operacionais, "Aporte": aporte_mes,
            "Fundo (Mês)": fundo_mes_total, "Retirada (Mês)": retirada_mes_efetiva,
            "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Patrimônio Líquido": patrimonio_liquido,
            "Valor de Mercado do Terreno": valor_mercado_terreno,
            "Patrimônio do Terreno": patrimonio_do_terreno,
            "Saldo Devedor": saldo_devedor,
            "Juros Acumulados": juros_acumulados,
            "Amortização Acumulada": amortizacao_acumulada,
        })

    return pd.DataFrame(rows)

# ---------------------------
# Estado Inicial da Sessão
# ---------------------------
def get_default_config():
    """Retorna a configuração padrão do simulador."""
    return {
        'rented': {
            'modules_init': 1, 'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0,
            'rent_value': 750.0, 'rent_per_new_module': 950.0
        },
        'owned': {
            'modules_init': 0, 'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0,
            'monthly_land_plot_parcel': 200.0,
            'land_total_value': 0.0, 'land_down_payment_pct': 20.0,
            'land_installments': 120, 'land_interest_rate': 8.0
        },
        'global': {
            'years': 15, 'max_withdraw_value': 50000.0,
            'general_correction_rate': 5.0, 'land_appreciation_rate': 3.0,
            'aportes': [], 'retiradas': [], 'fundos': []
        }
    }

# Inicialização do st.session_state
if 'config' not in st.session_state:
    st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state:
    st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = pd.DataFrame()
if 'active_page' not in st.session_state:
    st.session_state.active_page = 'Dashboard'
if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = None

# ---------------------------
# Barra Lateral (Sidebar)
# ---------------------------
with st.sidebar:
    st.markdown("<h1>📊 Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #1F2937; margin-bottom: 1rem;'>Projeção com reinvestimento inteligente</p>", unsafe_allow_html=True)
    nav_options = {"Dashboard": "📈", "Relatórios e Dados": "📋", "Configurações": "⚙️"}
    selected = st.radio("Menu", list(nav_options.keys()), key="nav_radio", label_visibility="collapsed", format_func=lambda x: f"{nav_options[x]} {x}")
    st.session_state.active_page = selected
    st.markdown("---")
    st.markdown("<p style='color: #334155; font-size: 0.85rem;'>Versão 10.5</p>", unsafe_allow_html=True)

# ---------------------------
# Página: Configurações
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.markdown("<h1 class='gradient-header'>Configurações de Investimento</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Ajuste os parâmetros da simulação financeira e adicione eventos.</p>", unsafe_allow_html=True)
    cfg_g = st.session_state.config['global']

    with st.container(border=True):
        st.markdown('<div class="section-title">🏢 Terreno Alugado</div>', unsafe_allow_html=True)
        cfg_r = st.session_state.config['rented']
        col1, col2, col3 = st.columns(3)
        with col1:
            cfg_r['modules_init'] = st.number_input("Módulos iniciais (alugados)", 0, value=cfg_r['modules_init'], key="rent_mod_init")
            cfg_r['cost_per_module'] = st.number_input("Custo de implantação/módulo (R$)", 0.0, value=cfg_r['cost_per_module'], format="%.2f", key="rent_cost_mod")
        with col2:
            cfg_r['revenue_per_module'] = st.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_r['revenue_per_module'], format="%.2f", key="rent_rev_mod")
            cfg_r['maintenance_per_module'] = st.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_r['maintenance_per_module'], format="%.2f", key="rent_maint_mod")
        with col3:
            cfg_r['rent_value'] = st.number_input("Aluguel mensal fixo (R$)", 0.0, value=cfg_r['rent_value'], format="%.2f", key="rent_base_rent")
            cfg_r['rent_per_new_module'] = st.number_input("Custo de aluguel por novo módulo (R$)", 0.0, value=cfg_r['rent_per_new_module'], format="%.2f", key="rent_new_rent")
    
    with st.container(border=True):
        st.markdown('<div class="section-title">🏠 Terreno Próprio</div>', unsafe_allow_html=True)
        cfg_o = st.session_state.config['owned']
        st.markdown("##### 🏗️ Financiamento do Terreno Inicial")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            cfg_o['land_total_value'] = st.number_input("Valor total do terreno (R$)", 0.0, value=cfg_o['land_total_value'], format="%.2f", key="own_total_land_val")
        if cfg_o['land_total_value'] > 0:
            with col2:
                cfg_o['land_down_payment_pct'] = st.number_input("Entrada (%)", 0.0, 100.0, value=cfg_o['land_down_payment_pct'], format="%.1f", key="own_down_pay")
            with col3:
                cfg_o['land_installments'] = st.number_input("Nº de parcelas", 1, 480, value=cfg_o['land_installments'], key="own_install")
            with col4:
                cfg_o['land_interest_rate'] = st.number_input("Juros anual (%)", 0.0, 50.0, value=cfg_o.get('land_interest_rate', 8.0), format="%.1f", key="own_interest")
        
        st.markdown("##### 📦 Módulos Próprios")
        col1, col2 = st.columns(2)
        with col1:
            cfg_o['modules_init'] = st.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
            cfg_o['cost_per_module'] = st.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
        with col2:
            cfg_o['revenue_per_module'] = st.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
            cfg_o['maintenance_per_module'] = st.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")

    with st.container(border=True):
        st.markdown('<div class="section-title">🌐 Parâmetros Globais</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            cfg_g['years'] = st.number_input("Anos de projeção", 1, 50, value=cfg_g['years'], key="glob_years")
            cfg_g['general_correction_rate'] = st.number_input("Correção anual geral (%)", 0.0, 50.0, value=cfg_g['general_correction_rate'], format="%.1f", key="glob_correction")
        with col2:
            cfg_g['max_withdraw_value'] = st.number_input("Retirada máxima mensal (R$)", 0.0, value=cfg_g['max_withdraw_value'], format="%.2f", key="glob_max_withdraw")
            cfg_g['land_appreciation_rate'] = st.number_input("Valorização anual do terreno (%)", -20.0, 50.0, value=cfg_g.get('land_appreciation_rate', 3.0), format="%.1f", key="glob_land_appr")

    with st.container(border=True):
        st.markdown('<div class="section-title">📅 Eventos Financeiros</div>', unsafe_allow_html=True)
        tab_aportes, tab_retiradas, tab_fundos = st.tabs(["Aportes", "Retiradas", "Fundos"])
        with tab_aportes:
            st.markdown("**Aportes de Capital (opcional)**")
            aporte_cols = st.columns([1, 2, 1])
            with aporte_cols[0]:
                aporte_mes = st.number_input("Mês do aporte", 1, cfg_g['years'] * 12, 1, key="aporte_mes")
            with aporte_cols[1]:
                aporte_valor = st.number_input("Valor (R$)", 0.0, step=1000.0, format="%.2f", key="aporte_valor")
            with aporte_cols[2]:
                st.write("") 
                if st.button("➕ Adicionar Aporte"):
                    if aporte_valor > 0:
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
            st.markdown("**Regras de Retirada (% do lucro)**")
            retirada_cols = st.columns([1, 2, 1])
            with retirada_cols[0]:
                retirada_mes = st.number_input("Mês inicial", 1, cfg_g['years'] * 12, 1, key="retirada_mes")
            with retirada_cols[1]:
                retirada_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, step=5.0, key="retirada_pct")
            with retirada_cols[2]:
                st.write("")
                if st.button("➕ Adicionar Retirada"):
                    if retirada_pct > 0:
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
            st.markdown("**Regras de Fundo de Reserva (% do lucro)**")
            fundo_cols = st.columns([1, 2, 1])
            with fundo_cols[0]:
                fundo_mes = st.number_input("Mês inicial", 1, cfg_g['years'] * 12, 1, key="fundo_mes")
            with fundo_cols[1]:
                fundo_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, step=5.0, key="fundo_pct")
            with fundo_cols[2]:
                st.write("")
                if st.button("➕ Adicionar Fundo"):
                    if fundo_pct > 0:
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

    if st.button("🔄 Resetar Configurações", type="secondary"):
        st.session_state.config = get_default_config()
        st.rerun()

# ---------------------------
# Página: Dashboard
# ---------------------------
elif st.session_state.active_page == 'Dashboard':
    st.markdown("<h1 class='gradient-header'>Dashboard de Projeção</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Selecione uma estratégia para simular ou compare todas para uma análise completa.</p>", unsafe_allow_html=True)
    config_copy = deepcopy(st.session_state.config)
    cache_key = compute_cache_key(config_copy)

    with st.container(border=True):
        st.markdown("### 🎯 Estratégias de Reinvestimento Anual")
        strat_cols = st.columns(4)
        with strat_cols[0]:
            if st.button("🏠 Comprar Novos", use_container_width=True, type="primary" if st.session_state.selected_strategy == 'buy' else "secondary"):
                with st.spinner("Calculando simulação 'Comprar'..."):
                    st.session_state.simulation_df = simulate(config_copy, 'buy', cache_key)
                    st.session_state.comparison_df = pd.DataFrame()
                    st.session_state.selected_strategy = 'buy'
                    st.rerun()
        with strat_cols[1]:
            if st.button("🏢 Alugar Novos", use_container_width=True, type="primary" if st.session_state.selected_strategy == 'rent' else "secondary"):
                with st.spinner("Calculando simulação 'Alugar'..."):
                    st.session_state.simulation_df = simulate(config_copy, 'rent', cache_key)
                    st.session_state.comparison_df = pd.DataFrame()
                    st.session_state.selected_strategy = 'rent'
                    st.rerun()
        with strat_cols[2]:
            if st.button("🔄 Intercalar Novos", use_container_width=True, type="primary" if st.session_state.selected_strategy == 'alternate' else "secondary"):
                with st.spinner("Calculando simulação 'Intercalar'..."):
                    st.session_state.simulation_df = simulate(config_copy, 'alternate', cache_key)
                    st.session_state.comparison_df = pd.DataFrame()
                    st.session_state.selected_strategy = 'alternate'
                    st.rerun()
        with strat_cols[3]:
            if st.button("📊 Comparar Todas", use_container_width=True):
                with st.spinner("Calculando as três simulações..."):
                    df_buy = simulate(config_copy, 'buy', cache_key); df_buy['Estratégia'] = 'Comprar'
                    df_rent = simulate(config_copy, 'rent', cache_key); df_rent['Estratégia'] = 'Alugar'
                    df_alt = simulate(config_copy, 'alternate', cache_key); df_alt['Estratégia'] = 'Intercalar'
                    st.session_state.comparison_df = pd.concat([df_buy, df_rent, df_alt])
                    st.session_state.simulation_df = pd.DataFrame()
                    st.session_state.selected_strategy = 'compare'
                    st.rerun()

    if not st.session_state.comparison_df.empty:
        st.markdown("<h2 class='gradient-header'>📈 Análise Comparativa</h2>", unsafe_allow_html=True)
        df_comp = st.session_state.comparison_df
        final_buy = df_comp[df_comp['Estratégia'] == 'Comprar'].iloc[-1]
        final_rent = df_comp[df_comp['Estratégia'] == 'Alugar'].iloc[-1]
        final_alt = df_comp[df_comp['Estratégia'] == 'Intercalar'].iloc[-1]
        
        st.markdown("##### Patrimônio Líquido Final")
        k1, k2, k3, k4 = st.columns(4)
        with k1: render_kpi_card("Comprar", fmt_brl(final_buy['Patrimônio Líquido']), PRIMARY_COLOR, "🏠")
        with k2: render_kpi_card("Alugar", fmt_brl(final_rent['Patrimônio Líquido']), INFO_COLOR, "🏢")
        with k3: render_kpi_card("Intercalar", fmt_brl(final_alt['Patrimônio Líquido']), WARNING_COLOR, "🔄")
        with k4:
            best = pd.Series({'Comprar': final_buy['Patrimônio Líquido'], 'Alugar': final_rent['Patrimônio Líquido'], 'Intercalar': final_alt['Patrimônio Líquido']}).idxmax()
            render_kpi_card("Melhor Estratégia", best, SUCCESS_COLOR, "🏆")
        
        with st.container(border=True):
            metric_options = ["Patrimônio Líquido", "Caixa (Final Mês)", "Retiradas Acumuladas", "Módulos Ativos", "Patrimônio do Terreno", "Investimento Total Acumulado"]
            selected_metric = st.selectbox("Selecione uma métrica para comparar:", options=metric_options)
            fig = px.line(df_comp, x="Mês", y=selected_metric, color='Estratégia', color_discrete_map={'Comprar': PRIMARY_COLOR, 'Alugar': INFO_COLOR, 'Intercalar': WARNING_COLOR})
            st.plotly_chart(apply_plot_theme(fig, f'Comparativo de {selected_metric}'), use_container_width=True)

    elif not st.session_state.simulation_df.empty:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        summary = calculate_summary_metrics(df)
        st.markdown(f"<h2 class='gradient-header'>Resultados: Estratégia '{st.session_state.selected_strategy.title()}'</h2>", unsafe_allow_html=True)
        
        st.markdown("##### 📊 Resumo Financeiro Final")
        resumo_cols = st.columns(4)
        with resumo_cols[0]: render_kpi_card("Patrimônio Líquido", fmt_brl(final['Patrimônio Líquido']), SUCCESS_COLOR, "💰")
        with resumo_cols[1]: render_kpi_card("ROI Total", f"{summary['roi_pct']:.1f}%", INFO_COLOR, "📈")
        with resumo_cols[2]: render_kpi_card("Ponto de Equilíbrio", f"Mês {summary['break_even_month']}", WARNING_COLOR, "⚖️")
        with resumo_cols[3]: render_kpi_card("Investimento Total", fmt_brl(final['Investimento Total Acumulado']), SECONDARY_COLOR, "💼")
        
        if final['Patrimônio do Terreno'] > 0:
            st.markdown("##### 🏡 Análise do Terreno")
            terreno_cols = st.columns(4)
            with terreno_cols[0]: render_kpi_card("Valor de Mercado", fmt_brl(final['Valor de Mercado do Terreno']), INFO_COLOR, "🏠")
            with terreno_cols[1]: render_kpi_card("Patrimônio no Terreno", fmt_brl(final['Patrimônio do Terreno']), SUCCESS_COLOR, "💰")
            with terreno_cols[2]: render_kpi_card("Amortização Total", fmt_brl(final['Amortização Acumulada']), WARNING_COLOR, "📊")
            with terreno_cols[3]: render_kpi_card("Juros Pagos", fmt_brl(final['Juros Acumulados']), DANGER_COLOR, "💸")
        
        st.markdown("##### 📈 Gráficos de Evolução")
        chart_cols = st.columns(2)
        with chart_cols[0], st.container(border=True):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Patrimônio Líquido'], mode='lines', name='Patrimônio Líquido', line=dict(color=SUCCESS_COLOR, width=3), fill='tozeroy'))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Investimento Total Acumulado'], mode='lines', name='Investimento Total', line=dict(color=SECONDARY_COLOR, width=2, dash='dash')))
            st.plotly_chart(apply_plot_theme(fig, "Patrimônio Líquido vs Investimento"), use_container_width=True)
        with chart_cols[1], st.container(border=True):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Receita'], mode='lines', name='Receita', line=dict(color=SUCCESS_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Gastos'], mode='lines', name='Gastos', line=dict(color=DANGER_COLOR, width=2)))
            st.plotly_chart(apply_plot_theme(fig, "Receita vs Gastos Operacionais"), use_container_width=True)
    else:
        st.info("💡 Bem-vindo! Vá para a página 'Configurações' para ajustar os parâmetros e depois volte aqui para executar uma simulação.")

# ---------------------------
# Página: Relatórios e Dados
# ---------------------------
elif st.session_state.active_page == 'Relatórios e Dados':
    st.markdown("<h1 class='gradient-header'>Relatórios e Dados</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subhead'>Tabelas detalhadas e exportação dos dados da simulação.</p>", unsafe_allow_html=True)
    
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty:
        df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty:
        df_to_show = st.session_state.simulation_df
        
    if df_to_show.empty:
        st.info("💡 Execute uma simulação no 'Dashboard' primeiro para ver os relatórios detalhados.")
    else:
        df_analysis_base = df_to_show
        selected_strategy_report = None
        
        if 'Estratégia' in df_analysis_base.columns:
            strategy_list = df_analysis_base['Estratégia'].unique().tolist()
            selected_strategy_report = st.selectbox("Selecione a estratégia para análise:", strategy_list, key="relat_strategy_select")
            df_analysis = df_analysis_base[df_analysis_base['Estratégia'] == selected_strategy_report].copy()
        else:
            df_analysis = df_analysis_base.copy()
            selected_strategy_report = st.session_state.selected_strategy.title() if st.session_state.selected_strategy else "Simulação Única"

        with st.container(border=True):
            st.markdown(f"##### 📅 Análise por Ponto no Tempo: <span style='color:{PRIMARY_COLOR};'>{selected_strategy_report}</span>", unsafe_allow_html=True)
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
                    res_cols = st.columns(4)
                    with res_cols[0]:
                        render_report_metric("Módulos Ativos", f"{int(data_point['Módulos Ativos'])}")
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
        
        with st.expander("Clique para ver a Tabela Completa da Simulação"):
            all_columns = df_analysis.columns.tolist()
            state_key = f"col_vis_{slug(selected_strategy_report or 'default')}"
            
            if state_key not in st.session_state:
                default_cols = ['Mês', 'Ano', 'Módulos Ativos', 'Receita', 'Gastos', 'Caixa (Final Mês)', 'Patrimônio Líquido', 'Investimento Total Acumulado']
                st.session_state[state_key] = {c: (c in default_cols) for c in all_columns}
            
            st.markdown("Selecione as colunas para exibir:")
            cols_to_show = []
            toggle_cols = st.columns(4)
            for idx, c in enumerate(all_columns):
                with toggle_cols[idx % 4]:
                    is_on = st.session_state[state_key].get(c, False)
                    if st.toggle(c, value=is_on, key=f"toggle_{slug(c)}_{state_key}"):
                        cols_to_show.append(c)
            
            if not cols_to_show:
                st.warning("Selecione ao menos uma coluna para exibir a tabela.")
            else:
                df_display = df_analysis[cols_to_show].copy()
                for col in (MONEY_COLS & set(df_display.columns)):
                    df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            excel_bytes = df_to_excel_bytes(df_analysis)
            st.download_button(
                "📥 Baixar Relatório Completo (Excel)",
                data=excel_bytes,
                file_name=f"relatorio_simulacao_{slug(selected_strategy_report or 'geral')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
