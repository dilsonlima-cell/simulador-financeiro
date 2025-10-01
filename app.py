# app.py
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
PRIMARY_COLOR   = "#FF9234"      # Laranja vibrante
SECONDARY_COLOR = "#6C757D"      # Cinza escuro
SUCCESS_COLOR   = "#28A745"      # Verde sucesso
DANGER_COLOR    = "#DC3545"      # Vermelho erro
WARNING_COLOR   = "#FFC107"      # Amarelo alerta
INFO_COLOR      = "#17A2B8"      # Azul info
APP_BG          = "#FFFFFF"      # Fundo branco
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
# Config da página + CSS
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
        /* Campos de entrada */
        .stTextInput input, .stNumberInput input {{
            background: {CARD_COLOR} !important; color: {TEXT_COLOR} !important; border: 1px solid {TABLE_BORDER_COLOR} !important;
            border-radius: 6px;
        }}
        /* Botões */
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
        /* Tabela */
        [data-testid="stDataFrame"] th {{
            background-color: #F8F9FA !important; color: {TEXT_COLOR} !important; font-weight: 600;
        }}
        [data-testid="stDataFrame"] td {{
            color: {TEXT_COLOR};
        }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Motor de Simulação (v11) - Corrigido
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
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
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
            retirada_potencial = sum(base * (r['percentual'] / 100.0) for r in cfg_global['retiradas'] if m >= r['mes'])
            fundo_potencial    = sum(base * (f['percentual'] / 100.0) for f in cfg_global['fundos'] if m >= f['mes'])
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

if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = 'buy'

# ---------------------------
# Header (fiel à imagem)
# ---------------------------
with st.container():
    st.markdown("""
        <div class="header">
            <h1 class="header-title">📊 Simulador Financeiro de Investimentos</h1>
            <p class="header-sub">Simule cenários de crescimento e otimize seus investimentos em módulos</p>
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
    st.markdown("<h3 class='section-title'>⚙️ Configuração Inicial</h3>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        cfg['rented']['modules_init'] = st.number_input(
            "Número inicial de módulos", 0, 1000, value=int(cfg['rented']['modules_init']),
            key="config_modules_init"
        )
    with c2:
        cfg['rented']['cost_per_module'] = st.number_input(
            "Valor por Módulo (R$)", 0.0, 1000000.0, value=cfg['rented']['cost_per_module'],
            format="%.2f", key="config_cost_per_module"
        )

    # Cartão de Investimento Inicial Total (laranja)
    invest_inicial = compute_initial_investment_total(cfg)
    st.markdown(f"""
        <div class="invest-strip">
            <span>Investimento Inicial Total:</span>
            <span>{fmt_brl(invest_inicial)}</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        cfg['rented']['revenue_per_module'] = st.number_input(
            "Receita Mensal por Módulo (R$)", 0.0, 100000.0, value=cfg['rented']['revenue_per_module'],
            format="%.2f", key="config_revenue_per_module"
        )
    with c2:
        cfg['rented']['maintenance_per_module'] = st.number_input(
            "Custo Manutenção Mensal por Módulo (R$)", 0.0, 10000.0, value=cfg['rented']['maintenance_per_module'],
            format="%.2f", key="config_maintenance_per_module"
        )

    c1, c2 = st.columns(2)
    with c1:
        cfg['rented']['rent_value'] = st.number_input(
            "Aluguel Mensal Terreno (R$)", 0.0, 100000.0, value=cfg['rented']['rent_value'],
            format="%.2f", key="config_rent_value"
        )
    with c2:
        cfg['rented']['rent_per_new_module'] = st.number_input(
            "Mês de Início do Aluguel", 0, 1000, value=int(cfg['rented']['rent_per_new_module']),
            key="config_rent_start_month"
        )

    st.markdown("<h3 class='section-title'>🏡 Financiamento de Terreno Próprio</h3>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        cfg['owned']['land_total_value'] = st.number_input(
            "Valor Total do Terreno (R$)", 0.0, 10000000.0, value=cfg['owned']['land_total_value'],
            format="%.2f", key="config_land_total_value"
        )
    with c2:
        cfg['owned']['land_down_payment_pct'] = st.number_input(
            "Entrada (%)", 0.0, 100.0, value=cfg['owned']['land_down_payment_pct'],
            format="%.1f", key="config_land_down_payment_pct"
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        cfg['owned']['land_installments'] = st.number_input(
            "Número de Parcelas", 1, 480, value=int(cfg['owned']['land_installments']),
            key="config_land_installments"
        )
    with c2:
        cfg['owned']['land_interest_rate'] = st.number_input(
            "Taxa de Juros Anual (%)", 0.0, 50.0, value=cfg['owned']['land_interest_rate'],
            format="%.1f", key="config_land_interest_rate"
        )
    with c3:
        cfg['owned']['land_appreciation_rate'] = st.number_input(
            "Valorização Anual do Terreno (%)", 0.0, 50.0, value=cfg['owned']['land_appreciation_rate'],
            format="%.1f", key="config_land_appreciation_rate"
        )

    # Resumo do financiamento
    if cfg['owned']['land_total_value'] > 0:
        valor_entrada = cfg['owned']['land_total_value'] * (cfg['owned']['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg['owned']['land_total_value'] - valor_entrada
        st.markdown(f"""
            <div class="card" style="padding: 0.75rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span>Valor da Entrada:</span>
                    <span>{fmt_brl(valor_entrada)}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Valor Financiado:</span>
                    <span>{fmt_brl(valor_financiado)}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Botão de simular
    if st.button("🚀 Executar Simulação", type="primary", use_container_width=True):
        with st.spinner("Calculando projeção..."):
            cache_key = compute_cache_key(st.session_state.config)
            st.session_state.simulation_df = simulate(st.session_state.config, 'buy', cache_key)
        st.success("Simulação concluída!")

# ---------------------------
# TRANSAÇÕES (aba) - Mantido Somente Aqui
# ---------------------------
with tab_transactions:
    st.markdown("<h3 class='section-title'>💰 Gerenciador de Transações</h3>", unsafe_allow_html=True)
    cfg = st.session_state.config
    g = cfg['global']

    st.markdown("#### 💸 Contribuições de Investimento")
    colA, colB = st.columns([1,2])
    with colA:
        ap_mes = st.number_input("Mês", 1, g['years']*12, 1, key="trans_aporte_mes")
    with colB:
        ap_val = st.number_input("Valor (R$)", 0.0, key="trans_aporte_valor")
    if st.button("➕ Adicionar Aporte", key="btn_trans_add_aporte"):
        g['aportes'].append({"mes": ap_mes, "valor": ap_val})
        st.rerun()
    if g['aportes']:
        st.markdown("**Aportes agendados:**")
        for i, a in enumerate(g['aportes']):
            cA, cB, cC = st.columns([3,2,1])
            cA.write(f"Mês {a['mes']}")
            cB.write(fmt_brl(a['valor']))
            if cC.button("🗑️", key=f"trans_del_aporte_{i}"):
                g['aportes'].pop(i); st.rerun()

    st.markdown("---")

    st.markdown("#### ↩️ Retiradas")
    colA, colB = st.columns([1,2])
    with colA:
        r_mes = st.number_input("Mês inicial", 1, g['years']*12, 1, key="trans_retirada_mes")
    with colB:
        r_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, key="trans_retirada_pct")
    if st.button("➕ Adicionar Retirada", key="btn_trans_add_retirada"):
        g['retiradas'].append({"mes": r_mes, "percentual": r_pct})
        st.rerun()
    if g['retiradas']:
        st.markdown("**Regras ativas:**")
        for i, r_ in enumerate(g['retiradas']):
            cA, cB, cC = st.columns([3,2,1])
            cA.write(f"A partir do mês {r_['mes']}")
            cB.write(f"{r_['percentual']}%")
            if cC.button("🗑️", key=f"trans_del_retirada_{i}"):
                g['retiradas'].pop(i); st.rerun()

    st.markdown("---")

    st.markdown("#### 🧱 Fundo de Reserva")
    colA, colB = st.columns([1,2])
    with colA:
        f_mes = st.number_input("Mês inicial", 1, g['years']*12, 1, key="trans_fundo_mes")
    with colB:
        f_pct = st.number_input("Percentual do lucro (%)", 0.0, 100.0, key="trans_fundo_pct")
    if st.button("➕ Adicionar Fundo", key="btn_trans_add_fundo"):
        g['fundos'].append({"mes": f_mes, "percentual": f_pct})
        st.rerun()
    if g['fundos']:
        st.markdown("**Regras ativas:**")
        for i, f in enumerate(g['fundos']):
            cA, cB, cC = st.columns([3,2,1])
            cA.write(f"A partir do mês {f['mes']}")
            cB.write(f"{f['percentual']}%")
            if cC.button("🗑️", key=f"trans_del_fundo_{i}"):
                g['fundos'].pop(i); st.rerun()

# ---------------------------
# RESULTADOS (aba)
# ---------------------------
with tab_results:
    st.markdown("<h3 class='section-title'>📈 Resultados da Simulação</h3>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("💡 Execute uma simulação na aba 'Configuração' para ver os resultados.")
    else:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        summary = calculate_summary_metrics(df)

        # KPIs principais
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Patrimônio Líquido", fmt_brl(final['Patrimônio Líquido']))
        with k2:
            st.metric("Investimento Total", fmt_brl(final['Investimento Total Acumulado']))
        with k3:
            st.metric("ROI Total", f"{summary['roi_pct']:.1f}%")
        with k4:
            st.metric("Ponto de Equilíbrio", f"Mês {summary['break_even_month']}")

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

        # Módulos por ano
        gp = df.groupby('Ano', as_index=False).agg({
            'Módulos Próprios':'last',
            'Módulos Alugados':'last',
            'Módulos Ativos':'last'
        })
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=gp['Ano'], y=gp['Módulos Ativos'], name='Módulos Ativos', marker_color=PRIMARY_COLOR))
        st.plotly_chart(apply_plot_theme(fig_bar, "Evolução de Módulos por Ano", h=380), use_container_width=True)

# ---------------------------
# DADOS (aba)
# ---------------------------
with tab_data:
    st.markdown("<h3 class='section-title'>📋 Dados Detalhados</h3>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("💡 Execute uma simulação na aba 'Configuração' para ver os dados detalhados.")
    else:
        df = st.session_state.simulation_df
        st.markdown("#### Tabela Completa da Simulação")
        # Seleção de colunas
        all_cols = df.columns.tolist()
        state_key = "col_vis_data"
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
            df_disp = df.copy()
            for col in (MONEY_COLS & set(df_disp.columns)):
                df_disp[col] = df_disp[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
            st.dataframe(df_disp[cols_to_show], use_container_width=True, hide_index=True)

        excel_bytes = df_to_excel_bytes(df)
        st.download_button(
            "📥 Baixar Relatório Completo (Excel)",
            data=excel_bytes,
            file_name="relatorio_simulacao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
