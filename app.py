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

# --- PALETA DE CORES (fiel à imagem) ---
PRIMARY_COLOR   = "#FF9234"      # Laranja vibrante do header
SECONDARY_COLOR = "#6C757D"      # Cinza escuro dos textos secundários
SUCCESS_COLOR   = "#28A745"      # Verde sucesso
DANGER_COLOR    = "#DC3545"      # Vermelho erro
WARNING_COLOR   = "#FFC107"      # Alerta amarelo
INFO_COLOR      = "#17A2B8"      # Informações azuis
APP_BG          = "#FFFFFF"      # Fundo branco da página
CARD_COLOR      = "#FFFFFF"      # Fundo branco dos cards
TEXT_COLOR      = "#212529"      # Texto escuro principal
MUTED_TEXT_COLOR= "#6C757D"      # Texto cinza secundário
TABLE_BORDER_COLOR = "#E9ECEF"
CHART_GRID_COLOR  = "#E9ECEF"

# --- COLUNAS PARA FORMATAÇÃO ---
MONEY_COLS = {
    "Receita","Manutenção","Aluguel","Parcela Terreno Inicial","Parcelas Terrenos (Novos)","Gastos",
    "Aporte","Fundo (Mês)","Retirada (Mês)","Caixa (Final Mês)","Investimento Total Acumulado",
    "Fundo Acumulado","Retiradas Acumuladas","Patrimônio Líquido","Juros Terreno Inicial",
    "Amortização Terreno Inicial","Equity Terreno Inicial","Valor de Mercado Terreno",
    "Patrimônio Terreno","Juros Acumulados","Amortização Acumulada","Desembolso Total",
    "Aluguel Acumulado","Parcelas Novas Acumuladas"
}
COUNT_COLS = {"Mês","Ano","Módulos Ativos","Módulos Alugados","Módulos Próprios","Módulos Comprados no Ano"}

# ---------------------------
# Helpers
# ---------------------------
def fmt_brl(v):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "-"
        s = f"{float(v):,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def render_kpi_card(title, value, bg_color=PRIMARY_COLOR, icon=None, subtitle=None, dark_text=False):
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
    """Função auxiliar para o cartão de métricas de relatório"""
    if isinstance(value, (int, np.integer)):
        formatted_value = f"{value:,}"
    else:
        formatted_value = fmt_brl(value)
    st.markdown(f"""
        <div class="report-metric-card">
            <div class="report-metric-title">{title}</div>
            <div class="report-metric-value">{formatted_value}</div>
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
        height=h, margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor='rgba(255,255,255,0.85)', bordercolor=TABLE_BORDER_COLOR, borderwidth=1,
                    font=dict(color=TEXT_COLOR)),
        plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font=dict(color=TEXT_COLOR),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR)),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR))
    )
    return fig

def compute_cache_key(cfg: dict) -> str:
    payload = json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()

def compute_initial_investment_total(cfg):
    r = cfg['rented']; o = cfg['owned']
    total = r['modules_init'] * r['cost_per_module'] + o['modules_init'] * o['cost_per_module']
    if o.get('land_total_value', 0) > 0:
        total += o['land_total_value'] * (o.get('land_down_payment_pct', 0) / 100.0)
    return total

# ---------------------------
# Config da página + CSS (fiel à imagem)
# ---------------------------
st.set_page_config(page_title="Simulador Financeiro de Investimentos", layout="wide", initial_sidebar_state="collapsed")
st.markdown(f"""
    <style>
        .main .block-container {{ padding: 0 1.25rem 2rem; max-width: 1400px; }}
        .stApp {{ background: {APP_BG}; }}
        h1, h2, h3, h4, h5, h6 {{ color: {TEXT_COLOR}; font-weight: 700; }}
        /* Header */
        .header {{
            background: linear-gradient(90deg, #FF9234 0%, #FFC107 100%);
            color: white; padding: 1.5rem 1.2rem; text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header-title {{
            font-size: 2rem; font-weight: 800; margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .header-sub {{
            font-size: 1rem; opacity: .95; margin-top: .35rem;
        }}
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0;
            background-color: #F8F9FA;
            border-radius: 8px;
            padding: 0.5rem;
            margin-bottom: 1rem;
            border: 1px solid {TABLE_BORDER_COLOR};
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: #FFFFFF;
            border: 1px solid {TABLE_BORDER_COLOR};
            border-radius: 6px;
            padding: 0.5rem 1rem;
            margin: 0;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background-color: #E9ECEF;
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border-color: {PRIMARY_COLOR};
        }}
        /* Cards */
        .card {{
            background: {CARD_COLOR}; border-radius: 8px; padding: 1.25rem; border: 1px solid {TABLE_BORDER_COLOR}; margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .section-title {{
            font-weight: 800; margin: .25rem 0 .75rem; color: {TEXT_COLOR}; font-size: 1.1rem;
        }}
        /* Input fields */
        .stTextInput input, .stNumberInput input {{
            background: {CARD_COLOR} !important; color: {TEXT_COLOR} !important; border: 1px solid {TABLE_BORDER_COLOR} !important;
            border-radius: 6px;
        }}
        /* Buttons */
        .stButton > button {{
            border-radius: 6px; border: 1px solid {PRIMARY_COLOR};
            background-color: {PRIMARY_COLOR}; color: white;
            padding: 8px 16px; font-weight: 700; transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            background-color: #FF7B00; border-color: #FF7B00;
        }}
        .invest-strip {{
            background: linear-gradient(90deg, #FF9234, #FFC107);
            color: white; border-radius: 8px; padding: .6rem 1rem; font-weight: 800; display:flex; justify-content:space-between; align-items:center;
            margin-bottom: 1rem;
        }}
        /* Table */
        [data-testid="stDataFrame"] th {{
            background-color: #F8F9FA !important; color: {TEXT_COLOR} !important; font-weight: 600;
        }}
        [data-testid="stDataFrame"] td {{
            color: {TEXT_COLOR};
        }}
        /* KPI Cards Modern */
        .kpi-card-modern {{
            border-radius: 18px; padding: 1.2rem 1.1rem; height: 100%; text-align: center;
            transition: transform .25s ease;
        }}
        .kpi-card-modern:hover {{ transform: translateY(-4px); }}
        .kpi-card-title-modern {{ font-size: .95rem; font-weight: 600; opacity: .95; margin-top: .35rem; }}
        .kpi-card-value-modern {{ font-size: 1.8rem; font-weight: 800; line-height: 1.1; }}
        .kpi-card-subtitle {{ font-size: .82rem; opacity: .9; margin-top: .25rem; }}
        /* Report Metric Cards */
        .report-metric-card {{
            background: {CARD_COLOR}; border: 1px solid {TABLE_BORDER_COLOR}; border-radius: 8px; 
            padding: 1rem; margin-bottom: 0.5rem; text-align: center;
        }}
        .report-metric-title {{ font-size: 0.85rem; color: {MUTED_TEXT_COLOR}; font-weight: 600; margin-bottom: 0.25rem; }}
        .report-metric-value {{ font-size: 1.2rem; color: {TEXT_COLOR}; font-weight: 700; }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Motor de Simulação (v11)
# ---------------------------
@st.cache_data(show_spinner=False)
def simulate(_config, reinvestment_strategy, cache_key: str):
    cfg_rented = _config['rented']
    cfg_owned  = _config['owned']
    cfg_global = _config['global']
    months = cfg_global['years'] * 12
    rows = []
    modules_rented = cfg_rented['modules_init']
    modules_owned  = cfg_owned['modules_init']
    caixa = 0.0
    investimento_total = (
        modules_rented * cfg_rented['cost_per_module'] +
        modules_owned  * cfg_owned['cost_per_module']
    )
    historical_value_rented = modules_rented * cfg_rented['cost_per_module']
    historical_value_owned  = modules_owned  * cfg_owned['cost_per_module']
    fundo_ac = 0.0
    retiradas_ac = 0.0
    compra_intercalada_counter = 0
    correction_rate_pct = cfg_global.get('general_correction_rate', 0.0) / 100.0
    land_appreciation_rate_pct = cfg_global.get('land_appreciation_rate', 3.0) / 100.0
    custo_modulo_atual_rented = cfg_rented['cost_per_module']
    custo_modulo_atual_owned  = cfg_owned['cost_per_module']
    receita_p_mod_rented      = cfg_rented['revenue_per_module']
    receita_p_mod_owned       = cfg_owned['revenue_per_module']
    manut_p_mod_rented        = cfg_rented['maintenance_per_module']
    manut_p_mod_owned         = cfg_owned['maintenance_per_module']
    aluguel_p_novo_mod        = cfg_rented['rent_per_new_module']
    parcela_p_novo_terreno    = cfg_owned['monthly_land_plot_parcel']
    aluguel_mensal_corrente = cfg_rented['rent_value'] + (cfg_rented['modules_init'] * cfg_rented['rent_per_new_module'])
    parcelas_terrenos_novos_mensal_corrente = 0.0
    parcela_terreno_inicial_atual = 0.0
    saldo_financiamento_terreno = 0.0
    equity_terreno_inicial = 0.0
    juros_acumulados = 0.0
    amortizacao_acumulada = 0.0
    valor_compra_terreno = 0.0
    taxa_juros_mensal = 0.0
    amortizacao_mensal = 0.0
    aluguel_acumulado = 0.0
    parcelas_novas_acumuladas = 0.0
    
    # Inicialização do financiamento do terreno
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
        manut   = (modules_rented * manut_p_mod_rented)   + (modules_owned * manut_p_mod_owned)
        novos_modulos_comprados = 0
        
        # Aportes
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['contributions'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes
        
        # Operacional
        gastos_operacionais = aluguel_mensal_corrente + parcelas_terrenos_novos_mensal_corrente
        lucro_operacional = receita - manut - gastos_operacionais
        
        # Financiamento terreno inicial
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
        
        # Distribuição (Retiradas + Fundo) limitada ao caixa
        fundo_mes_total = 0.0
        retirada_mes_efetiva = 0.0
        
        if lucro_operacional > 0:
            base = lucro_operacional
            retirada_potencial = sum(base * (r['percentual'] / 100.0) for r in cfg_global['withdrawals'] if m >= r['mes'])
            fundo_potencial    = sum(base * (f['percentual'] / 100.0) for f in cfg_global['reserve_funds'] if m >= f['mes'])
            
            if cfg_global['max_withdraw_value'] > 0 and retirada_potencial > cfg_global['max_withdraw_value']:
                retirada_mes_efetiva = cfg_global['max_withdraw_value']
                fundo_mes_total = fundo_potencial
            else:
                retirada_mes_efetiva = retirada_potencial
                fundo_mes_total = fundo_potencial
            
            total_distrib = retirada_mes_efetiva + fundo_mes_total
            if total_distrib > caixa:
                if caixa > 0:
                    proporcao = caixa / total_distrib
                    retirada_mes_efetiva *= proporcao
                    fundo_mes_total *= proporcao
                else:
                    retirada_mes_efetiva = 0.0
                    fundo_mes_total = 0.0
        
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total
        
        # Acumuladores de desembolso corrente
        aluguel_acumulado += aluguel_mensal_corrente
        parcelas_novas_acumuladas += parcelas_terrenos_novos_mensal_corrente
        
        # Reinvestimento anual
        if m % 12 == 0:
            if reinvestment_strategy == 'buy':
                custo = custo_modulo_atual_owned
                if caixa >= custo > 0:
                    novos_modulos_comprados = int(caixa // custo)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        historical_value_owned += custo_da_compra
                        modules_owned += novos_modulos_comprados
                        parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
            elif reinvestment_strategy == 'rent':
                custo = custo_modulo_atual_rented
                if caixa >= custo > 0:
                    novos_modulos_comprados = int(caixa // custo)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        historical_value_rented += custo_da_compra
                        modules_rented += novos_modulos_comprados
                        aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
            elif reinvestment_strategy == 'alternate':
                alvo = 'buy' if ((modules_owned + modules_rented) % 2 == 0) else 'rent'
                custo = custo_modulo_atual_owned if alvo == 'buy' else custo_modulo_atual_rented
                if caixa >= custo > 0:
                    novos_modulos_comprados = int(caixa // custo)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        if alvo == 'buy':
                            historical_value_owned += custo_da_compra
                            modules_owned += novos_modulos_comprados
                            parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
                        else:
                            historical_value_rented += custo_da_compra
                            modules_rented += novos_modulos_comprados
                            aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
            
            # Correção anual
            correction_factor = 1 + correction_rate_pct
            custo_modulo_atual_owned  *= correction_factor
            custo_modulo_atual_rented *= correction_factor
            receita_p_mod_rented      *= correction_factor
            receita_p_mod_owned       *= correction_factor
            manut_p_mod_rented        *= correction_factor
            manut_p_mod_owned         *= correction_factor
            aluguel_mensal_corrente   *= correction_factor
            parcelas_terrenos_novos_mensal_corrente *= correction_factor
            parcela_p_novo_terreno    *= correction_factor
            aluguel_p_novo_mod        *= correction_factor
        
        # Patrimônio
        valor_mercado_terreno = valor_compra_terreno * ((1 + land_appreciation_rate_pct) ** (m / 12))
        patrimonio_terreno = valor_mercado_terreno - saldo_financiamento_terreno
        ativos  = historical_value_owned + historical_value_rented + caixa + fundo_ac + patrimonio_terreno
        passivos= saldo_financiamento_terreno
        patrimonio_liquido = ativos - passivos
        desembolso_total = investimento_total + juros_acumulados + aluguel_acumulado + parcelas_novas_acumuladas
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
            "Aluguel Acumulado": aluguel_acumulado,
            "Parcelas Novas Acumuladas": parcelas_novas_acumuladas,
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
            'land_total_value': 0.0,
            'land_down_payment_pct': 20.0,
            'land_installments': 120,
            'land_interest_rate': 8.0,
            'land_appreciation_rate': 3.0
        },
        'global': {
            'years': 15,
            'max_withdraw_value': 50000.0,
            'general_correction_rate': 5.0,
            'land_appreciation_rate': 3.0,
            'contributions': [],
            'withdrawals': [],
            'reserve_funds': []
        }
    }

if 'config' not in st.session_state:
    st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state:
    st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = pd.DataFrame()
if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = 'buy'

# ---------------------------
# Header (fiel à imagem)
# ---------------------------
with st.container():
    st.markdown("""
        <div class="header">
            <h1 class="header-title">📊 Simulador Financeiro de Investimentos</h1>
            <p class="header-sub">Compare estratégias, analise terrenos próprios vs alugados e projete seu crescimento</p>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------
# Abas (fiel à imagem: Configuração, Transações, Resultados, Dados)
# ---------------------------
tab_config, tab_transactions, tab_results, tab_data = st.tabs([
    "⚙️ Configurações",
    "💰 Transações",
    "📈 Resultados",
    "📋 Planilha"
])

# ---------------------------
# CONFIGURAÇÕES (aba)
# ---------------------------
with tab_config:
    cfg = st.session_state.config
    st.markdown("<h3 class='section-title'>⚙️ Configuração do Investimento</h3>", unsafe_allow_html=True)
    
    # Parâmetros iniciais: 3 cards lado a lado
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🏢 Terreno Alugado")
        r = cfg['rented']
        r['modules_init'] = st.number_input("Módulos iniciais (alugados)", 0, value=r['modules_init'], key="rent_mod_init")
        r['cost_per_module'] = st.number_input("Custo por módulo (R$)", 0.0, value=r['cost_per_module'], format="%.2f", key="rent_cost_mod")
        r['revenue_per_module'] = st.number_input("Receita mensal/módulo (R$)", 0.0, value=r['revenue_per_module'], format="%.2f", key="rent_rev_mod")
        r['maintenance_per_module'] = st.number_input("Manutenção mensal/módulo (R$)", 0.0, value=r['maintenance_per_module'], format="%.2f", key="rent_maint_mod")
        r['rent_value'] = st.number_input("Aluguel mensal fixo (R$)", 0.0, value=r['rent_value'], format="%.2f", key="rent_base_rent")
        r['rent_per_new_module'] = st.number_input("Custo aluguel por novo módulo (R$)", 0.0, value=r['rent_per_new_module'], format="%.2f", key="rent_new_rent")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🏠 Terreno Próprio")
        o = cfg['owned']
        st.markdown("##### Financiamento do Terreno Inicial")
        o['land_total_value'] = st.number_input("Valor total do terreno (R$)", 0.0, value=o['land_total_value'], format="%.2f", key="own_total_land_val")
        
        if o['land_total_value'] > 0:
            o['land_down_payment_pct'] = st.number_input("Entrada (%)", 0.0, 100.0, value=o['land_down_payment_pct'], format="%.1f", key="own_down_pay")
            o['land_installments'] = st.number_input("Parcelas (qtd.)", 1, 480, value=o['land_installments'], key="own_install")
            o['land_interest_rate'] = st.number_input("Juros anual (%)", 0.0, 50.0, value=o.get('land_interest_rate', 8.0), format="%.1f", key="own_interest")
            
            valor_entrada = o['land_total_value'] * (o['land_down_payment_pct'] / 100.0)
            valor_financiado = o['land_total_value'] - valor_entrada
            taxa_juros_mensal = (o['land_interest_rate'] / 100.0) / 12
            amortizacao_mensal = valor_financiado / o['land_installments'] if o['land_installments'] > 0 else 0
            primeira_parcela = amortizacao_mensal + (valor_financiado * taxa_juros_mensal) if o['land_installments'] > 0 else 0
            
            cA, cB = st.columns(2)
            with cA: st.metric("Valor da Entrada", fmt_brl(valor_entrada))
            with cB: st.metric("1ª Parcela Estimada", fmt_brl(primeira_parcela))
        
        st.markdown("##### Módulos Próprios")
        o['modules_init'] = st.number_input("Módulos iniciais (próprios)", 0, value=o['modules_init'], key="own_mod_init")
        o['cost_per_module'] = st.number_input("Custo por módulo (R$)", 0.0, value=o['cost_per_module'], format="%.2f", key="own_cost_mod")
        o['monthly_land_plot_parcel'] = st.number_input("Parcela mensal por novo terreno (R$)", 0.0, value=o['monthly_land_plot_parcel'], format="%.2f", key="own_land_parcel")
        o['revenue_per_module'] = st.number_input("Receita mensal/módulo (R$)", 0.0, value=o['revenue_per_module'], format="%.2f", key="own_rev_mod")
        o['maintenance_per_module'] = st.number_input("Manutenção mensal/módulo (R$)", 0.0, value=o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with c3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🌐 Parâmetros Globais")
        g = cfg['global']
        g['years'] = st.number_input("Anos de projeção", 1, 50, value=g['years'], key="glob_years")
        g['general_correction_rate'] = st.number_input("Correção anual geral (%)", 0.0, 50.0, value=g['general_correction_rate'], format="%.1f", key="glob_correction")
        g['max_withdraw_value'] = st.number_input("Retirada máxima mensal (R$)", 0.0, value=g['max_withdraw_value'], format="%.2f", key="glob_max_withdraw")
        g['land_appreciation_rate'] = st.number_input("Valorização anual do terreno (%)", 0.0, 50.0, value=g.get('land_appreciation_rate', 3.0), format="%.1f", key="glob_land_appr")
        
        st.markdown("##### 🔄 Estratégia de Reinvestimento")
        reinvestment_strategy = st.selectbox(
            "Como reinvestir o lucro?",
            ["buy", "rent", "alternate"],
            format_func=lambda x: {"buy":"Comprar módulos próprios","rent":"Alugar novos módulos","alternate":"Alternar entre comprar e alugar"}[x],
            key="reinvestment_strategy"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Faixa de Investimento Inicial Total
    invest_inicial = compute_initial_investment_total(cfg)
    st.markdown(f"""
        <div class="invest-strip">
            <span>Investimento Inicial Total</span>
            <span>{fmt_brl(invest_inicial)}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Ação de simular
    if st.button("🚀 Executar Simulação", type="primary", use_container_width=True):
        with st.spinner("Calculando projeção..."):
            cache_key = compute_cache_key(st.session_state.config)
            st.session_state.simulation_df = simulate(st.session_state.config, reinvestment_strategy, cache_key)
            st.session_state.selected_strategy = reinvestment_strategy
        st.success("Simulação concluída!")

# ---------------------------
# TRANSAÇÕES (aba)
# ---------------------------
with tab_transactions:
    st.markdown("<h3 class='section-title'>💰 Gerenciador de Transações</h3>", unsafe_allow_html=True)
    cfg = st.session_state.config
    g = cfg['global']
    
    # Garantir que as listas existem
    if 'contributions' not in g:
        g['contributions'] = []
    if 'withdrawals' not in g:
        g['withdrawals'] = []
    if 'reserve_funds' not in g:
        g['reserve_funds'] = []

    st.markdown("#### 💸 Aportes de Investimento")
    colA, colB = st.columns([1,2])
    with colA:
        ap_mes = st.number_input("Mês", 1, g['years']*12, 1, key="trans_aporte_mes")
    with colB:
        ap_val = st.number_input("Valor (R$)", 0.0, key="trans_aporte_valor")
    if st.button("➕ Adicionar Aporte", key="btn_trans_add_aporte"):
        g['contributions'].append({"mes": ap_mes, "valor": ap_val})
        st.rerun()
    
    if g['contributions']:
        st.markdown("**Aportes agendados:**")
        for i, a in enumerate(g['contributions']):
            cA, cB, cC = st.columns([3,2,1])
            cA.write(f"Mês {a['mes']}")
            cB.write(fmt_brl(a['valor']))
            if cC.button("🗑️", key=f"trans_del_aporte_{i}"):
                g['contributions'].pop(i)
                st.rerun()
    
    st.markdown("---")
    st.markdown("#### ↩️ Retiradas")
    colA, colB = st.columns([1,2])
    with colA:
        r_mes = st.number_input("Mês inicial", 1, g['years']*12, 1, key="trans_retirada_mes")
    with colB:
        r_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, key="trans_retirada_pct")
    if st.button("➕ Adicionar Retirada", key="btn_trans_add_retirada"):
        g['withdrawals'].append({"mes": r_mes, "percentual": r_pct})
        st.rerun()
    
    if g['withdrawals']:
        st.markdown("**Regras ativas:**")
        for i, r_ in enumerate(g['withdrawals']):
            cA, cB, cC = st.columns([3,2,1])
            cA.write(f"A partir do mês {r_['mes']}")
            cB.write(f"{r_['percentual']}%")
            if cC.button("🗑️", key=f"trans_del_retirada_{i}"):
                g['withdrawals'].pop(i)
                st.rerun()
    
    st.markdown("---")
    st.markdown("#### 🧱 Fundo de Reserva")
    colA, colB = st.columns([1,2])
    with colA:
        f_mes = st.number_input("Mês inicial", 1, g['years']*12, 1, key="trans_fundo_mes")
    with colB:
        f_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, key="trans_fundo_pct")
    if st.button("➕ Adicionar Fundo", key="btn_trans_add_fundo"):
        g['reserve_funds'].append({"mes": f_mes, "percentual": f_pct})
        st.rerun()
    
    if g['reserve_funds']:
        st.markdown("**Regras ativas:**")
        for i, f in enumerate(g['reserve_funds']):
            cA, cB, cC = st.columns([3,2,1])
            cA.write(f"A partir do mês {f['mes']}")
            cB.write(f"{f['percentual']}%")
            if cC.button("🗑️", key=f"trans_del_fundo_{i}"):
                g['reserve_funds'].pop(i)
                st.rerun()

# ---------------------------
# RESULTADOS (aba)
# ---------------------------
with tab_results:
    st.markdown("<h3 class='section-title'>📈 Dashboard de Projeção</h3>", unsafe_allow_html=True)
    
    if not st.session_state.simulation_df.empty and not st.session_state.comparison_df.empty:
        st.session_state.simulation_df = pd.DataFrame()
    
    cfg_copy = deepcopy(st.session_state.config)
    cache_key = compute_cache_key(cfg_copy)
    
    st.markdown("### Estratégias de Reinvestimento")
    sc1, sc2, sc3, sc4 = st.columns([1,1,1,1.5])
    
    with sc1:
        if st.button("🏠 Comprar Novos", use_container_width=True, type="primary" if st.session_state.selected_strategy == 'buy' else "secondary"):
            with st.spinner("Calculando..."):
                st.session_state.simulation_df = simulate(cfg_copy, 'buy', cache_key)
                st.session_state.comparison_df = pd.DataFrame()
                st.session_state.selected_strategy = 'buy'
    
    with sc2:
        if st.button("🏢 Alugar Novos", use_container_width=True, type="primary" if st.session_state.selected_strategy == 'rent' else "secondary"):
            with st.spinner("Calculando..."):
                st.session_state.simulation_df = simulate(cfg_copy, 'rent', cache_key)
                st.session_state.comparison_df = pd.DataFrame()
                st.session_state.selected_strategy = 'rent'
    
    with sc3:
        if st.button("🔄 Intercalar Novos", use_container_width=True, type="primary" if st.session_state.selected_strategy == 'alternate' else "secondary"):
            with st.spinner("Calculando..."):
                st.session_state.simulation_df = simulate(cfg_copy, 'alternate', cache_key)
                st.session_state.comparison_df = pd.DataFrame()
                st.session_state.selected_strategy = 'alternate'
    
    with sc4:
        if st.button("📊 Comparar Todas as Estratégias", use_container_width=True):
            with st.spinner("Calculando..."):
                df_buy = simulate(cfg_copy, 'buy', cache_key)
                df_buy['Estratégia'] = 'Comprar'
                df_rent = simulate(cfg_copy, 'rent', cache_key)
                df_rent['Estratégia'] = 'Alugar'
                df_alt  = simulate(cfg_copy, 'alternate', cache_key)
                df_alt['Estratégia'] = 'Intercalar'
                st.session_state.comparison_df = pd.concat([df_buy, df_rent, df_alt], ignore_index=True)
                st.session_state.simulation_df = pd.DataFrame()
                st.session_state.selected_strategy = None
    
    if not st.session_state.comparison_df.empty:
        st.markdown("### 📈 Análise Comparativa")
        dfc = st.session_state.comparison_df
        final_buy = dfc[dfc['Estratégia']=='Comprar'].iloc[-1]
        final_rent= dfc[dfc['Estratégia']=='Alugar' ].iloc[-1]
        final_alt = dfc[dfc['Estratégia']=='Intercalar'].iloc[-1]
        
        k1, k2, k3, k4 = st.columns(4)
        with k1: 
            render_kpi_card("Comprar", fmt_brl(final_buy['Patrimônio Líquido']), PRIMARY_COLOR, "🏠", "Patrimônio Final")
        with k2: 
            render_kpi_card("Alugar", fmt_brl(final_rent['Patrimônio Líquido']), INFO_COLOR, "🏢", "Patrimônio Final")
        with k3: 
            render_kpi_card("Intercalar", fmt_brl(final_alt['Patrimônio Líquido']), WARNING_COLOR, "🔄", "Patrimônio Final")
        with k4:
            best = pd.Series({
                'Comprar': final_buy['Patrimônio Líquido'],
                'Alugar': final_rent['Patrimônio Líquido'],
                'Intercalar': final_alt['Patrimônio Líquido']
            }).idxmax()
            render_kpi_card("Melhor Estratégia", best, SUCCESS_COLOR, "🏆", "Recomendação")
        
        metric_options = [
            "Patrimônio Líquido","Módulos Ativos","Retiradas Acumuladas",
            "Fundo Acumulado","Caixa (Final Mês)","Investimento Total Acumulado"
        ]
        selected_metric = st.selectbox("Métrica para comparar", options=metric_options)
        
        fig_comp = px.line(
            dfc, x="Mês", y=selected_metric, color='Estratégia',
            color_discrete_map={'Comprar': PRIMARY_COLOR, 'Alugar': INFO_COLOR, 'Intercalar': WARNING_COLOR}
        )
        apply_plot_theme(fig_comp, f"Comparativo de {selected_metric}", h=450)
        st.plotly_chart(fig_comp, use_container_width=True)
    
    elif not st.session_state.simulation_df.empty:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        summary = calculate_summary_metrics(df)
        
        st.markdown("### 📊 Indicadores Principais")
        k = st.columns(4)
        with k[0]: 
            render_kpi_card("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']), SUCCESS_COLOR, "💰")
        with k[1]: 
            render_kpi_card("Investimento Total", fmt_brl(final['Investimento Total Acumulado']), SECONDARY_COLOR, "💼")
        with k[2]: 
            render_kpi_card("ROI Total", f"{summary['roi_pct']:.1f}%", INFO_COLOR, "📈")
        with k[3]: 
            render_kpi_card("Ponto de Equilíbrio", f"Mês {summary['break_even_month']}", WARNING_COLOR, "⚖️")
        
        if final['Patrimônio Terreno'] > 0:
            st.markdown("### 🏡 Análise do Terreno")
            c = st.columns(4)
            with c[0]: 
                render_kpi_card("Valor de Mercado", fmt_brl(final['Valor de Mercado Terreno']), INFO_COLOR, "🏠")
            with c[1]: 
                render_kpi_card("Patrimônio no Terreno", fmt_brl(final['Patrimônio Terreno']), SUCCESS_COLOR, "💰")
            with c[2]: 
                render_kpi_card("Equity Construído", fmt_brl(final['Equity Terreno Inicial']), WARNING_COLOR, "📊")
            with c[3]: 
                render_kpi_card("Juros Pagos", fmt_brl(final['Juros Acumulados']), DANGER_COLOR, "💸")
        
        # Gráficos
        g1, g2 = st.columns(2)
        with g1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Patrimônio Líquido'], mode='lines', name='Patrimônio Líquido', line=dict(color=SUCCESS_COLOR, width=3)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Investimento Total Acumulado'], mode='lines', name='Investimento Total', line=dict(color=SECONDARY_COLOR, width=2, dash='dash')))
            st.plotly_chart(apply_plot_theme(fig, "Evolução do Investimento"), use_container_width=True)
        
        with g2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Receita'], mode='lines', name='Receita', line=dict(color=SUCCESS_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Gastos'], mode='lines', name='Gastos', line=dict(color=DANGER_COLOR, width=2)))
            st.plotly_chart(apply_plot_theme(fig, "Receita vs Gastos"), use_container_width=True)
        
        # Módulos por ano (barras)
        gp = df.groupby('Ano', as_index=False).agg({
            'Módulos Próprios':'last',
            'Módulos Alugados':'last',
            'Módulos Ativos':'last'
        })
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=gp['Ano'], y=gp['Módulos Ativos'], name='Módulos Ativos', marker_color=PRIMARY_COLOR))
        st.plotly_chart(apply_plot_theme(fig_bar, "Evolução de Módulos por Ano", h=380), use_container_width=True)
        
        # Fluxo de Caixa Mensal (área empilhada)
        flow = df[['Mês','Aporte','Fundo (Mês)','Retirada (Mês)']].copy()
        flow['Retirada (Mês)'] = -flow['Retirada (Mês)']  # saída como negativo p/ visual
        flow_melt = flow.melt(id_vars='Mês', var_name='Tipo', value_name='Valor')
        fig_area = px.area(flow_melt, x='Mês', y='Valor', color='Tipo',
                           color_discrete_map={"Aporte":SECONDARY_COLOR,"Fundo (Mês)":WARNING_COLOR,"Retirada (Mês)":"#9333EA"})
        st.plotly_chart(apply_plot_theme(fig_area, "Fluxo de Caixa Mensal", h=380), use_container_width=True)
        
        # Performance (ROI% + Investimento/ Caixa)
        perf = df.copy()
        perf['ROI %'] = np.where(perf['Investimento Total Acumulado']>0,
                                 (perf['Patrimônio Líquido']-perf['Investimento Total Acumulado'])/perf['Investimento Total Acumulado']*100, 0)
        fig_perf = go.Figure()
        fig_perf.add_trace(go.Scatter(x=perf['Mês'], y=perf['Investimento Total Acumulado'], name='Investimento Total', line=dict(color=SECONDARY_COLOR)))
        fig_perf.add_trace(go.Scatter(x=perf['Mês'], y=perf['Caixa (Final Mês)'], name='Caixa', line=dict(color=PRIMARY_COLOR)))
        fig_perf.add_trace(go.Scatter(x=perf['Mês'], y=perf['ROI %'], name='ROI %', yaxis='y2', line=dict(color=INFO_COLOR, width=3)))
        fig_perf.update_layout(
            yaxis=dict(title='Valores (R$)'),
            yaxis2=dict(title='ROI (%)', overlaying='y', side='right', showgrid=False)
        )
        st.plotly_chart(apply_plot_theme(fig_perf, "Performance do Investimento", h=420), use_container_width=True)
    
    else:
        st.info("💡 Configure os parâmetros na aba 'Configurações' e execute a simulação para ver os resultados.")

# ---------------------------
# RELATÓRIOS / PLANILHA (aba)
# ---------------------------
with tab_data:
    st.markdown("<h3 class='section-title'>📋 Relatórios e Dados</h3>", unsafe_allow_html=True)
    
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty:
        df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty:
        df_to_show = st.session_state.simulation_df
    
    if df_to_show.empty:
        st.info("💡 Execute uma simulação primeiro para ver os relatórios.")
    else:
        base = df_to_show
        selected_strategy = None
        
        if 'Estratégia' in base.columns:
            selected_strategy = st.selectbox("Estratégia para análise", base['Estratégia'].unique(), key="relat_strategy_select")
            df_analysis = base[base['Estratégia']==selected_strategy].copy()
        else:
            df_analysis = base.copy()
        
        # Análise por ponto no tempo
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📅 Análise por Ponto no Tempo")
        c1, c2 = st.columns(2)
        anos = sorted(df_analysis['Ano'].unique())
        sel_year = c1.selectbox("Ano", options=anos, key="relat_ano_select")
        
        # Filtrar pelo ano selecionado
        subset = df_analysis[df_analysis['Ano']==sel_year].copy()
        if not subset.empty:
            # Obter meses disponíveis para o ano selecionado
            available_months = sorted(subset['Mês'].unique())
            sel_m = c2.selectbox("Mês", options=available_months, key="relat_mes_select")
            
            # Filtrar pelo mês específico
            filtered = subset[subset['Mês'] == sel_m]
            if not filtered.empty:
                p = filtered.iloc[0] # Pegar a primeira linha (deve ser apenas uma)
                r = st.columns(4)
                with r[0]:
                    render_report_metric("Módulos Ativos", int(p['Módulos Ativos']))
                    render_report_metric("Patrimônio Líquido", p['Patrimônio Líquido'])
                with r[1]:
                    render_report_metric("Caixa no Mês", p['Caixa (Final Mês)'])
                    render_report_metric("Investimento Total", p['Investimento Total Acumulado'])
                with r[2]:
                    render_report_metric("Fundo (Mês)", p['Fundo (Mês)'])
                    render_report_metric("Fundo Acumulado", p['Fundo Acumulado'])
                with r[3]:
                    render_report_metric("Retirada (Mês)", p['Retirada (Mês)'])
                    render_report_metric("Retiradas Acumuladas", p['Retiradas Acumuladas'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Tabela completa selecionável + download
        with st.expander("Clique para ver a Tabela Completa da Simulação"):
            all_cols = df_analysis.columns.tolist()
            state_key = f"col_vis_{slug(selected_strategy or 'default')}"
            
            if state_key not in st.session_state:
                default_cols = ['Mês','Ano','Módulos Ativos','Receita','Gastos','Caixa (Final Mês)','Patrimônio Líquido','Investimento Total Acumulado']
                st.session_state[state_key] = {c: (c in default_cols) for c in all_cols}
            
            st.markdown("Selecione as colunas para exibir:")
            cols_to_show = []
            grid = st.columns(3)
            
            for idx, c in enumerate(all_cols):
                with grid[idx % 3]:
                    tkey = f"toggle_{slug(c)}_{state_key}"
                    st.session_state[state_key][c] = st.toggle(c, value=st.session_state[state_key][c], key=tkey)
                    if st.session_state[state_key][c]:
                        cols_to_show.append(c)
            
            if not cols_to_show:
                st.warning("Selecione ao menos uma coluna.")
            else:
                df_disp = df_analysis.copy()
                for col in (MONEY_COLS & set(df_disp.columns)):
                    df_disp[col] = df_disp[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
                st.dataframe(df_disp[cols_to_show], use_container_width=True, hide_index=True)
            
            excel_bytes = df_to_excel_bytes(df_analysis)
            st.download_button(
                "📥 Baixar Relatório Completo (Excel)",
                data=excel_bytes,
                file_name=f"relatorio_simulacao_{slug(selected_strategy or 'geral')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
