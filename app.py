'''
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

# --- ESTADO DA SESSÃO ---
if 'config' not in st.session_state:
    st.session_state.config = {
        'rented': {'modules_init': 0, 'rent_value': 0.0, 'rent_per_new_module': 0.0},
        'owned': {'modules_init': 0, 'monthly_land_plot_parcel': 0.0, 'land_total_value': 0.0, 'land_down_payment_pct': 0.0, 'land_installments': 1, 'land_interest_rate': 8.0},
        'global': {
            'cost_per_module': 0.0, 'revenue_per_module': 0.0, 'maintenance_per_module': 0.0, # Novos campos globais
            'years': 10, 'general_correction_rate': 3.0, 'max_withdraw_value': 0.0, 'land_appreciation_rate': 3.0, 'contributions': [], 'withdrawals': [], 'reserve_funds': [], 'reinvestment_strategy': 'buy'
        }
    }
if 'simulation_df' not in st.session_state:
    st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = pd.DataFrame()
if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = 'buy'
if 'config_changed' not in st.session_state:
    st.session_state.config_changed = False

# --- PALETA DE CORES (fiel à imagem) ---
PRIMARY_COLOR   = "#FF9234"      # Laranja vibrante do header
SECONDARY_COLOR = "#6C757D"      # Cinza escuro dos textos secundários
SUCCESS_COLOR   = "#28A745"      # Verde sucesso
DANGER_COLOR    = "#DC3545"      # Vermelho erro
WARNING_COLOR   = "#FFC107"      # Alerta amarelo
INFO_COLOR      = "#17A2B8"      # Informações azuis
APP_BG          = "#FFFFFF"      # Fundo branco da página
CARD_COLOR      = "#FFFFFF"      # Fundo blanco dos cards
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
    "Dívida Futura (Total)","Investimento em Terrenos","Valor de Mercado (Total)","Patrimônio Terreno","Juros Acumulados","Amortização Acumulada","Desembolso Total",
    "Aluguel Acumulado","Parcelas Novas Acumuladas"
}
COUNT_COLS = {"Mês","Ano","Módulos Ativos","Módulos Alugados","Módulos Próprios","Módulos Comprados no Ano","Terrenos Adquiridos"}

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
    icon_html = f'<div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>' if icon else ""
    subtitle_html = f'<div class="kpi-card-subtitle">{subtitle}</div>' if subtitle else ""
    txt_color = "#0F172A" if dark_text else "#FFFFFF"
    html = f"""
<div class="kpi-card-modern" style="background:{bg_color}; color:{txt_color};">
    {icon_html}
    <div class="kpi-card-value-modern">{value}</div>
    <div class="kpi-card-title-modern">{title}</div>
    {subtitle_html}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)

def render_report_metric(title, value):
    """Função auxiliar para o cartão de métricas de relatório"""
    if isinstance(value, (int, np.integer)):
        formatted_value = f"{value:,}"
    else:
        formatted_value = fmt_brl(value)
    st.markdown(f'''
        <div class="report-metric-card">
            <div class="report-metric-title">{title}</div>
            <div class="report-metric-value">{formatted_value}</div>
        </div>
    ''', unsafe_allow_html=True)

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
    g = cfg['global']; r = cfg['rented']; o = cfg['owned']
    cost_per_module = g.get('cost_per_module', 0.0)
    
    # Custo dos módulos iniciais (próprios + alugados)
    total = (r['modules_init'] * cost_per_module) + (o['modules_init'] * cost_per_module)
    
    # Entrada do terreno inicial
    if o.get('land_total_value', 0) > 0:
        total += o['land_total_value'] * (o.get('land_down_payment_pct', 0) / 100.0)
    return total

# ---------------------------
# Config da página + CSS (fiel à imagem)
# ---------------------------
st.set_page_config(page_title="Simulador Financeiro de Investimentos", layout="wide", initial_sidebar_state="collapsed")
st.markdown(f'''
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
        .kpi-card-title-modern {{ font-size: 0.9rem; font-weight: 600; opacity: 0.9; margin-top: 0.25rem; }}
        .kpi-card-value-modern {{ font-size: 1.75rem; font-weight: 800; line-height: 1.2; }}
        .kpi-card-subtitle {{ font-size: 0.8rem; opacity: 0.8; margin-top: 0.2rem; }}
        /* Report Metrics */
        .report-metric-card {{ text-align: center; margin-bottom: 1rem; }}
        .report-metric-title {{ font-size: 0.9rem; font-weight: 600; opacity: 0.8; }}
        .report-metric-value {{ font-size: 1.25rem; font-weight: 700; }}
    </style>
''', unsafe_allow_html=True)

# ---------------------------
# Motor de Simulação
# ---------------------------
@st.cache_data(show_spinner=False)
def simulate(_config: dict) -> pd.DataFrame:
    cfg_rented = _config['rented']
    cfg_owned  = _config['owned']
    cfg_global = _config['global']
    
    # Variáveis globais unificadas
    cost_per_module = cfg_global['cost_per_module']
    revenue_per_module = cfg_global['revenue_per_module']
    maintenance_per_module = cfg_global['maintenance_per_module']
    
    months = cfg_global['years'] * 12
    rows = []
    modules_rented = cfg_rented['modules_init']
    modules_owned  = cfg_owned['modules_init']
    caixa = 0.0
    investimento_total = (
        modules_rented * cost_per_module +
        modules_owned  * cost_per_module
    )
    historical_value_rented = modules_rented * cost_per_module
    historical_value_owned  = modules_owned  * cost_per_module
    
    # Financiamento do terreno inicial
    valor_compra_terreno = cfg_owned['land_total_value']
    entrada_pct = cfg_owned['land_down_payment_pct'] / 100.0
    valor_entrada_terreno = valor_compra_terreno * entrada_pct
    investimento_total += valor_entrada_terreno
    
    saldo_financiamento_terreno = valor_compra_terreno - valor_entrada_terreno
    taxa_juros_mensal = (cfg_owned['land_interest_rate'] / 100.0) / 12
    amortizacao_mensal_terreno = saldo_financiamento_terreno / cfg_owned['land_installments'] if cfg_owned['land_installments'] > 0 else 0
    
    # Variáveis de controle
    fundo_ac = 0.0
    retiradas_ac = 0.0
    aluguel_mensal_corrente = modules_rented * cfg_rented['rent_value']
    aluguel_acumulado = 0.0
    juros_acumulados = 0.0
    amortizacao_acumulada = 0.0
    parcelas_novas_acumuladas = 0.0
    
    # Variáveis para novos terrenos
    terrenos_adquiridos_count = 1 if valor_compra_terreno > 0 else 0
    investimento_terrenos_total = valor_entrada_terreno
    parcelas_terrenos_novos_mensal_corrente = 0.0
    saldo_devedor_novos_terrenos = 0.0
    parcela_p_novo_terreno = cfg_owned['monthly_land_plot_parcel']

    # Variáveis de correção anual
    correction_rate_pct = cfg_global.get('general_correction_rate', 0.0) / 100.0
    land_appreciation_rate_pct = cfg_global.get('land_appreciation_rate', 3.0) / 100.0
    
    # Variáveis unificadas
    custo_modulo_atual = cost_per_module
    receita_p_mod      = revenue_per_module
    manut_p_mod        = maintenance_per_module
    aluguel_p_novo_mod = cfg_rented['rent_value']

    reinvestment_strategy = cfg_global['reinvestment_strategy']

    for m in range(1, months + 1):
        receita = (modules_rented * receita_p_mod) + (modules_owned * receita_p_mod)
        manut   = (modules_rented * manut_p_mod)   + (modules_owned * manut_p_mod)
        novos_modulos_comprados_ano = 0

        # Pagamento do financiamento do terreno inicial
        juros_terreno_mes = saldo_financiamento_terreno * taxa_juros_mensal
        amortizacao_terreno_mes = amortizacao_mensal_terreno if saldo_financiamento_terreno > 0 else 0
        parcela_terreno_inicial_mes = juros_terreno_mes + amortizacao_terreno_mes
        
        if saldo_financiamento_terreno > 0:
            saldo_financiamento_terreno -= amortizacao_terreno_mes
            if saldo_financiamento_terreno < 0: saldo_financiamento_terreno = 0
        else:
            juros_terreno_mes = 0
            amortizacao_terreno_mes = 0
            parcela_terreno_inicial_mes = 0

        # Amortização dos novos terrenos
        amortizacao_novos_terrenos = parcelas_terrenos_novos_mensal_corrente
        if saldo_devedor_novos_terrenos > 0:
            saldo_devedor_novos_terrenos -= amortizacao_novos_terrenos
            if saldo_devedor_novos_terrenos < 0: saldo_devedor_novos_terrenos = 0

        # Aportes e retiradas
        aporte_mes = next((c['value'] for c in cfg_global['contributions'] if c['month'] == m), 0)
        retirada_mes = next((w['value'] for w in cfg_global['withdrawals'] if w['month'] == m), 0)
        reserva_fundo = next((r['value'] for r in cfg_global['reserve_funds'] if r['month'] == m), 0)
        
        fundo_mes_bruto = receita - manut - aluguel_mensal_corrente - parcela_terreno_inicial_mes - parcelas_terrenos_novos_mensal_corrente + aporte_mes
        fundo_mes_total = fundo_mes_bruto - reserva_fundo
        
        retirada_mes_efetiva = min(retirada_mes, fundo_mes_total) if fundo_mes_total > 0 else 0
        fundo_ac += fundo_mes_total - retirada_mes_efetiva
        retiradas_ac += retirada_mes_efetiva
        
        caixa += fundo_mes_total - retirada_mes_efetiva
        
        # Acumuladores
        juros_acumulados += juros_terreno_mes
        amortizacao_acumulada += amortizacao_terreno_mes + amortizacao_novos_terrenos
        aluguel_acumulado += aluguel_mensal_corrente
        parcelas_novas_acumuladas += parcelas_terrenos_novos_mensal_corrente

        # Reinvestimento (ocorre no final do ano)
        if m % 12 == 0:
            if reinvestment_strategy == 'buy':
                custo = custo_modulo_atual
                if caixa >= custo > 0:
                    modules_to_buy = int(caixa // custo)
                    for _ in range(modules_to_buy):
                        modules_owned += 1
                        terrenos_adquiridos_count += 1
                        investimento_total += custo
                        historical_value_owned += custo
                        investimento_terrenos_total += custo
                        parcelas_terrenos_novos_mensal_corrente += parcela_p_novo_terreno
                        saldo_devedor_novos_terrenos += custo
                        caixa -= custo
                    novos_modulos_comprados_ano = modules_to_buy
            elif reinvestment_strategy == 'rent':
                custo = custo_modulo_atual
                if caixa >= custo > 0:
                    modules_to_rent = int(caixa // custo)
                    custo_da_compra = modules_to_rent * custo
                    caixa -= custo_da_compra
                    investimento_total += custo_da_compra
                    historical_value_rented += custo_da_compra
                    modules_rented += modules_to_rent
                    aluguel_mensal_corrente += modules_to_rent * aluguel_p_novo_mod
                    novos_modulos_comprados_ano = modules_to_rent
            elif reinvestment_strategy == 'alternate':
                alvo = 'buy' if ((m // 12) % 2 == 0) else 'rent'
                custo = custo_modulo_atual
                if caixa >= custo > 0:
                    if alvo == 'buy':
                        modules_to_buy = int(caixa // custo)
                        for _ in range(modules_to_buy):
                            modules_owned += 1
                            terrenos_adquiridos_count += 1
                            investimento_total += custo
                            historical_value_owned += custo
                            investimento_terrenos_total += custo
                            parcelas_terrenos_novos_mensal_corrente += parcela_p_novo_terreno
                            saldo_devedor_novos_terrenos += custo
                            caixa -= custo
                        novos_modulos_comprados_ano = modules_to_buy
                    else:
                        modules_to_rent = int(caixa // custo)
                        custo_da_compra = modules_to_rent * custo
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        historical_value_rented += custo_da_compra
                        modules_rented += modules_to_rent
                        aluguel_mensal_corrente += modules_to_rent * aluguel_p_novo_mod
                        novos_modulos_comprados_ano = modules_to_rent
            
            # Correção anual
            correction_factor = 1 + correction_rate_pct
            custo_modulo_atual  *= correction_factor
            receita_p_mod       *= correction_factor
            manut_p_mod         *= correction_factor
            aluguel_mensal_corrente   *= correction_factor
            parcelas_terrenos_novos_mensal_corrente *= correction_factor
            parcela_p_novo_terreno    *= correction_factor
            aluguel_p_novo_mod        *= correction_factor
        
        # Patrimônio
        valor_mercado_terreno_inicial = valor_compra_terreno * ((1 + land_appreciation_rate_pct) ** (m / 12)) if valor_compra_terreno > 0 else 0
        valor_mercado_terrenos_novos = (terrenos_adquiridos_count - (1 if valor_compra_terreno > 0 else 0)) * custo_modulo_atual * ((1 + land_appreciation_rate_pct) ** (m / 12))
        valor_mercado_terrenos_total = valor_mercado_terreno_inicial + valor_mercado_terrenos_novos
        
        dívida_futura_total = saldo_financiamento_terreno + saldo_devedor_novos_terrenos
        
        patrimonio_terreno = valor_mercado_terreno_inicial - saldo_financiamento_terreno
        ativos  = historical_value_owned + historical_value_rented + caixa + fundo_ac + patrimonio_terreno
        passivos= dívida_futura_total
        patrimonio_liquido = valor_mercado_terrenos_total + caixa + fundo_ac - passivos
        
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
            "Patrimônio Líquido": patrimonio_liquido,
            "Equity Terreno Inicial": valor_entrada_terreno + amortizacao_acumulada,
            "Valor de Mercado Terreno": valor_mercado_terreno_inicial,
            "Módulos Comprados no Ano": novos_modulos_comprados_ano,
            "Dívida Futura (Total)": dívida_futura_total,
            "Investimento em Terrenos": investimento_terrenos_total,
            "Terrenos Adquiridos": terrenos_adquiridos_count,
            "Valor de Mercado (Total)": valor_mercado_terrenos_total,
            "Patrimônio Terreno": patrimonio_terreno,
            "Juros Acumulados": juros_acumulados,
            "Amortização Acumulada": amortizacao_acumulada,
            "Desembolso Total": desembolso_total,
            "Aluguel Acumulado": aluguel_acumulado,
            "Parcelas Novas Acumuladas": parcelas_novas_acumuladas
        })
    return pd.DataFrame(rows)

# ---------------------------
# LAYOUT
# ---------------------------
st.markdown('<div class="header"><h1 class="header-title">Simulador Financeiro de Investimentos</h1><p class="header-sub">by Manus Web</p></div>', unsafe_allow_html=True)
st.write("")

tab_config, tab_transactions, tab_results, tab_spreadsheet = st.tabs([
    "⚙️ Configurações",
    "💸 Transações",
    "📈 Resultados",
    "📋 Planilha"
])

# ---------------------------
# CONFIGURAÇÕES (aba)
# ---------------------------
with tab_config:
    cfg = st.session_state.config
    g = cfg['global']
    o = cfg['owned']
    r = cfg['rented']
    
    invest_inicial = compute_initial_investment_total(cfg)
    st.markdown(f'''
        <div class="invest-strip">
            <span>Investimento Inicial Total</span>
            <span>{fmt_brl(invest_inicial)}</span>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("<h3 class='section-title'>⚙️ Configuração do Investimento</h3>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🌐 Parâmetros Globais e Módulos")
        
        g['years'] = st.number_input("Anos de projeção", 1, 50, value=g['years'], key="glob_years")
        g['general_correction_rate'] = st.number_input("Correção anual geral (%)", 0.0, 50.0, value=g['general_correction_rate'], format="%.1f", key="glob_correction")
        g['max_withdraw_value'] = st.number_input("Retirada máxima mensal (R$)", 0.0, value=g['max_withdraw_value'], format="%.2f", key="glob_max_withdraw")
        g['land_appreciation_rate'] = st.number_input("Valorização anual do terreno (%)", 0.0, 50.0, value=g.get('land_appreciation_rate', 3.0), format="%.1f", key="glob_land_appr")
        
        st.markdown("---")
        st.markdown("#### ⚙️ Configuração do Módulo")
        
        g['cost_per_module'] = st.number_input("Custo por módulo (R$)", 0.0, value=g['cost_per_module'], format="%.2f", key="glob_cost_mod")
        g['revenue_per_module'] = st.number_input("Receita mensal/módulo (R$)", 0.0, value=g['revenue_per_module'], format="%.2f", key="glob_rev_mod")
        g['maintenance_per_module'] = st.number_input("Manutenção mensal/módulo (R$)", 0.0, value=g['maintenance_per_module'], format="%.2f", key="glob_maint_mod")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🏠 Estratégia de Terreno")
        
        r['modules_init'] = st.number_input("Módulos iniciais (alugados)", 0, value=r['modules_init'], key="rent_mod_init")
        o['modules_init'] = st.number_input("Módulos iniciais (próprios)", 0, value=o['modules_init'], key="own_mod_init")
        
        st.markdown("---")
        st.markdown("#### 🔄 Estratégia de Reinvestimento")
        
        reinvestment_strategy = st.selectbox(
            "Como reinvestir o lucro?",
            ["buy", "rent", "alternate"],
            format_func=lambda x: {"buy":"Comprar módulos próprios","rent":"Alugar novos módulos","alternate":"Alternar entre comprar e alugar"}[x],
            key="reinvestment_strategy",
            on_change=lambda: st.session_state.config['global'].update({'reinvestment_strategy': st.session_state.reinvestment_strategy})
        )
        
        st.markdown("---")
        st.markdown("#### 💰 Configuração do Financiamento")
        
        r['rent_value'] = st.number_input("Aluguel mensal fixo por módulo (R$)", 0.0, value=r['rent_value'], format="%.2f", key="rent_base_rent")
        
        if 'buy' in [reinvestment_strategy, st.session_state.config['global'].get('reinvestment_strategy')] or o['modules_init'] > 0:
            st.markdown("##### Financiamento do Terreno Inicial")
            o['land_total_value'] = st.number_input("Valor total do terreno (R$)", 0.0, value=o['land_total_value'], format="%.2f", key="own_total_land_val")
            
            primeira_parcela = 0.0
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
            
            o['monthly_land_plot_parcel'] = primeira_parcela
            st.number_input("Parcela mensal por novo terreno (R$)", 0.0, value=o['monthly_land_plot_parcel'], format="%.2f", key="own_land_parcel", disabled=True)
            
            if o['land_total_value'] == 0:
                o['land_down_payment_pct'] = 0.0
                o['land_installments'] = 1
                o['land_interest_rate'] = 0.0
                o['monthly_land_plot_parcel'] = 0.0
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.info("💡 Configure as transações na aba **Transações** e clique em **Executar Simulação** para iniciar a projeção.")

# ---------------------------
# TRANSAÇÕES (aba)
# ---------------------------
with tab_transactions:
    cfg = st.session_state.config
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 class="section-title">💸 Aportes, Retiradas e Reservas</h3>', unsafe_allow_html=True)
    
    t_c1, t_c2, t_c3 = st.columns(3)
    with t_c1:
        st.markdown('<h5>➕ Aportes Programados</h5>', unsafe_allow_html=True)
        aportes = st.data_editor(cfg['global']['contributions'], num_rows="dynamic", key="aportes_editor",
                                 column_config={"month": st.column_config.NumberColumn("Mês", min_value=1),
                                                "value": st.column_config.NumberColumn("Valor (R$)", format="%.2f")})
        cfg['global']['contributions'] = aportes

    with t_c2:
        st.markdown('<h5>➖ Retiradas Programadas</h5>', unsafe_allow_html=True)
        retiradas = st.data_editor(cfg['global']['withdrawals'], num_rows="dynamic", key="retiradas_editor",
                                   column_config={"month": st.column_config.NumberColumn("Mês", min_value=1),
                                                  "value": st.column_config.NumberColumn("Valor (R$)", format="%.2f")})
        cfg['global']['withdrawals'] = retiradas

    with t_c3:
        st.markdown('<h5>🛡️ Reservas de Fundo</h5>', unsafe_allow_html=True)
        reservas = st.data_editor(cfg['global']['reserve_funds'], num_rows="dynamic", key="reservas_editor",
                                  column_config={"month": st.column_config.NumberColumn("Mês", min_value=1),
                                                 "value": st.column_config.NumberColumn("Valor (R$)", format="%.2f")})
        cfg['global']['reserve_funds'] = reservas
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# BOTÃO DE SIMULAÇÃO
# ---------------------------
st.write("")
if st.button("Executar Simulação", use_container_width=True):
    with st.spinner("Executando simulação... Por favor, aguarde."):
        st.session_state.simulation_df = simulate(st.session_state.config)
        st.session_state.config_changed = False
        st.success("Simulação concluída com sucesso!")

# ---------------------------
# RESULTADOS (aba)
# ---------------------------
with tab_results:
    df = st.session_state.simulation_df
    if df.empty:
        st.warning("Nenhuma simulação foi executada ainda. Configure os parâmetros e clique em 'Executar Simulação'.")
    else:
        summary = calculate_summary_metrics(df)
        final = df.iloc[-1]

        st.markdown('<h3 class="section-title">📊 Indicadores Principais</h3>', unsafe_allow_html=True)
        k = st.columns(4)
        with k[0]:
            render_kpi_card("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']), SUCCESS_COLOR, "💰")
        with k[1]:
            render_kpi_card("Investimento Total", fmt_brl(summary['total_investment']), SECONDARY_COLOR, "💼")
        with k[2]:
            render_kpi_card("ROI Total", f"{summary['roi_pct']:.1f}%", INFO_COLOR, "📈")
        with k[3]:
            render_kpi_card("Ponto de Equilíbrio", f"Mês {summary['break_even_month']}", WARNING_COLOR, "⚖️")

        st.markdown('<h3 class="section-title">⚙️ Módulos Ativos</h3>', unsafe_allow_html=True)
        k_new = st.columns(1)
        with k_new[0]:
            render_kpi_card("Total de Módulos Ativos", f"{int(final['Módulos Ativos'])}", PRIMARY_COLOR, "⚙️")

        st.markdown('<h3 class="section-title">🏡 Análise do Terreno</h3>', unsafe_allow_html=True)
        k2 = st.columns(4)
        with k2[0]:
            render_kpi_card("Valor de Mercado (Total)", fmt_brl(final['Valor de Mercado (Total)']), INFO_COLOR, "🏠")
        with k2[1]:
            render_kpi_card("Investimento em Terrenos", fmt_brl(final['Investimento em Terrenos']), SUCCESS_COLOR, "💼")
        with k2[2]:
            render_kpi_card("Dívida Futura (Total)", fmt_brl(final['Dívida Futura (Total)']), DANGER_COLOR, "💸")
        with k2[3]:
            render_kpi_card("Terrenos Adquiridos", f"{int(final['Terrenos Adquiridos'])}", WARNING_COLOR, "🏗️")

        st.markdown('<h3 class="section-title">📈 Evolução do Investimento</h3>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Mês'], y=df['Patrimônio Líquido'], name='Patrimônio Líquido', fill='tozeroy', line=dict(color=SUCCESS_COLOR)))
        fig.add_trace(go.Scatter(x=df['Mês'], y=df['Investimento Total Acumulado'], name='Investimento Total', line=dict(color=SECONDARY_COLOR, dash='dash')))
        apply_plot_theme(fig, title="Patrimônio Líquido vs. Investimento Total")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<h3 class="section-title">💰 Receita vs Gastos</h3>', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df['Mês'], y=df['Receita'], name='Receita', marker_color=SUCCESS_COLOR))
        fig2.add_trace(go.Bar(x=df['Mês'], y=df['Gastos'], name='Gastos', marker_color=DANGER_COLOR))
        apply_plot_theme(fig2, title="Receita vs. Gastos Mensais")
        st.plotly_chart(fig2, use_container_width=True)

# ---------------------------
# PLANILHA (aba)
# ---------------------------
with tab_spreadsheet:
    df = st.session_state.simulation_df
    if df.empty:
        st.warning("Nenhuma simulação foi executada ainda.")
    else:
        st.markdown('<h3 class="section-title">📑 Planilha de Simulação Detalhada</h3>', unsafe_allow_html=True)
        
        df_display = df.copy()
        for col in MONEY_COLS:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(fmt_brl)
        
        st.dataframe(df_display, use_container_width=True, height=600)
        
        st.download_button(
            label="📥 Baixar Planilha em Excel",
            data=df_to_excel_bytes(df),
            file_name=f"simulacao_financeira_{slug(st.session_state.config['global']['reinvestment_strategy'])}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
'''
