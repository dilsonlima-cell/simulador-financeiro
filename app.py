# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# --- PALETA DE CORES E CONFIGURAÇÕES ---
PRIMARY_COLOR = "#0072B2"
SUCCESS_COLOR = "#5CB85C"
DANGER_COLOR = "#D9534F"
WARNING_COLOR = "#F0AD4E"
INFO_COLOR = "#5BC0DE"
DARK_BACKGROUND = "#2C3E50"
LIGHT_BACKGROUND = "#ECF0F1"
TEXT_COLOR = "#34495E"
CARD_COLOR = "#FFFFFF"
MUTED_TEXT_COLOR = "#7F8C8D"
TABLE_BORDER_COLOR = "#BDC3C7"

# ---------------------------
# CSS - Estilos da Página
# ---------------------------
st.set_page_config(page_title="Simulador Modular", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"""
    <style>
        .main .block-container {{ padding: 1.5rem 2rem; }}
        [data-testid="stSidebar"] {{ background-color: {DARK_BACKGROUND}; }}
        [data-testid="stSidebar"] .stMarkdown h1 {{ padding-top: 1rem; color: {LIGHT_BACKGROUND}; }}
        [data-testid="stSidebar"] .stMarkdown p {{ color: rgba(236, 240, 241, 0.8); }}
        .stRadio > div {{ gap: 0.5rem; }}
        .stRadio > label > div {{
            font-size: 1.1rem !important; font-weight: 600 !important; padding: 0.75rem 1rem !important;
            border-radius: 8px !important; margin-bottom: 0.5rem; color: rgba(236, 240, 241, 0.8) !important;
            transition: all 0.2s; border-left: 3px solid transparent;
        }}
        .stRadio > div[role="radiogroup"] > label:has(div[data-baseweb="radio"][class*="e1y5xkzn3"]) > div {{
            background-color: rgba(255, 255, 255, 0.1) !important; color: {CARD_COLOR} !important;
            border-left: 3px solid {PRIMARY_COLOR};
        }}
        .stApp {{ background-color: {LIGHT_BACKGROUND}; }}
        h1, h2, h3, h4, h5, h6, label, .st-emotion-cache-16idsys p {{ color: {TEXT_COLOR} !important; }}
        .subhead, .st-emotion-cache-1ghhuty p {{ color: {MUTED_TEXT_COLOR} !important; }}
        .stButton > button {{
            border-radius: 8px; border: 1px solid {PRIMARY_COLOR}; background-color: {PRIMARY_COLOR};
            color: white; padding: 10px 24px; font-weight: bold;
        }}
        .stButton > button:hover {{
            background-color: #005a8c; border-color: #005a8c;
        }}
        .stButton > button[kind="secondary"] {{
            background-color: transparent; color: {PRIMARY_COLOR};
        }}
        .stButton > button[kind="secondary"]:hover {{
            background-color: rgba(0, 114, 178, 0.1); color: {PRIMARY_COLOR};
        }}

        [data-testid="stMetricLabel"] p {{ color: {MUTED_TEXT_COLOR} !important; font-size: 0.9rem; }}
        [data-testid="stMetricValue"] div {{ color: {TEXT_COLOR} !important; }}

        .card {{
            background: {CARD_COLOR}; border-radius: 8px; padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #D5DBDB; height: 100%;
        }}
        .kpi-card {{
            border-radius: 8px; padding: 1.25rem; color: white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1); height: 100%;
        }}
        .kpi-card-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; opacity: 0.9; }}
        .kpi-card-value {{ font-size: 2rem; font-weight: 700; }}
    </style>
""", unsafe_allow_html=True)


# --- FUNÇÃO HELPER PARA KPIs ---
def render_kpi_card(title, value, color):
    st.markdown(f"""
        <div class="kpi-card" style="background-color: {color};">
            <div class="kpi-card-title">{title}</div>
            <div class="kpi-card-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)


# ---------------------------
# Funções Utilitárias e de Lógica
# ---------------------------
def fmt_brl(v):
    return f"R$ {v:,.2f}"

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Simulacao_Mensal')
    return output.getvalue()

def simulate(config, reinvestment_strategy):
    cfg_rented = config['rented']
    cfg_owned = config['owned']
    cfg_global = config['global']
    months = cfg_global['years'] * 12
    rows = []
    modules_rented = cfg_rented['modules_init']
    modules_owned = cfg_owned['modules_init']
    caixa = 0.0
    investimento_total = (modules_rented * cfg_rented['cost_per_module']) + (modules_owned * cfg_owned['cost_per_module'])
    fundo_ac = 0.0
    retiradas_ac = 0.0
    custo_modulo_atual_rented = cfg_rented['cost_per_module']
    custo_modulo_atual_owned = cfg_owned['cost_per_module']
    
    # --- LÓGICA CORRIGIDA ---
    valor_terrenos_adicionais = 0.0 # Nova variável para rastrear valor de novos terrenos

    valor_entrada_terreno = 0.0
    valor_parcela_terreno_inicial = 0.0
    if cfg_owned['land_total_value'] > 0:
        valor_entrada_terreno = cfg_owned['land_total_value'] * (cfg_owned['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_owned['land_total_value'] - valor_entrada_terreno
        valor_parcela_terreno_inicial = valor_financiado / cfg_owned['land_installments'] if cfg_owned['land_installments'] > 0 else 0
        investimento_total += valor_entrada_terreno
    
    aluguel_mensal_corrente = cfg_rented['rent_value']
    parcelas_terrenos_novos_mensal_corrente = 0.0
    compra_intercalada_counter = 0

    for m in range(1, months + 1):
        receita = (modules_rented * cfg_rented['revenue_per_module']) + (modules_owned * cfg_owned['revenue_per_module'])
        manut = (modules_rented * cfg_rented['maintenance_per_module']) + (modules_owned * cfg_owned['maintenance_per_module'])
        novos_modulos_comprados = 0
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes
        lucro_operacional_mes = receita - manut - aluguel_mensal_corrente - parcelas_terrenos_novos_mensal_corrente
        parcela_terreno_inicial_mes = 0.0
        if cfg_owned['land_total_value'] > 0 and m <= cfg_owned['land_installments']:
            parcela_terreno_inicial_mes = valor_parcela_terreno_inicial
            investimento_total += valor_parcela_terreno_inicial
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
        if m % 12 == 0:
            custo_expansao = 0.0
            if reinvestment_strategy == 'buy':
                custo_expansao = custo_modulo_atual_owned
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
            elif reinvestment_strategy == 'alternate':
                if compra_intercalada_counter % 2 == 0:
                    custo_expansao = custo_modulo_atual_owned
                else:
                    custo_expansao = custo_modulo_atual_rented
            
            if custo_expansao > 0 and caixa >= custo_expansao:
                novos_modulos_comprados = int(caixa // custo_expansao)
                if novos_modulos_comprados > 0:
                    custo_da_compra = novos_modulos_comprados * custo_expansao
                    caixa -= custo_da_compra
                    investimento_total += custo_da_compra
                    if reinvestment_strategy == 'buy':
                        modules_owned += novos_modulos_comprados
                        parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * cfg_owned['monthly_land_plot_parcel']
                        valor_terrenos_adicionais += novos_modulos_comprados * cfg_owned['land_value_per_module'] # CORREÇÃO
                    elif reinvestment_strategy == 'rent':
                        modules_rented += novos_modulos_comprados
                        aluguel_mensal_corrente += novos_modulos_comprados * cfg_rented['rent_per_new_module']
                    elif reinvestment_strategy == 'alternate':
                        for _ in range(novos_modulos_comprados):
                            if compra_intercalada_counter % 2 == 0:
                                modules_owned += 1
                                parcelas_terrenos_novos_mensal_corrente += cfg_owned['monthly_land_plot_parcel']
                                valor_terrenos_adicionais += cfg_owned['land_value_per_module'] # CORREÇÃO
                            else:
                                modules_rented += 1
                                aluguel_mensal_corrente += cfg_rented['rent_per_new_module']
                            compra_intercalada_counter += 1

            custo_modulo_atual_owned *= (1 + cfg_owned['cost_correction_rate'] / 100.0)
            custo_modulo_atual_rented *= (1 + cfg_rented['cost_correction_rate'] / 100.0)
        
        # --- FÓRMULA DO PATRIMÔNIO CORRIGIDA ---
        patrimonio_liquido = ((modules_owned + modules_rented) * custo_modulo_atual_owned) + caixa + fundo_ac + cfg_owned['land_total_value'] + valor_terrenos_adicionais

        rows.append({ "Mês": m, "Ano": (m - 1) // 12 + 1, "Módulos Ativos": modules_owned + modules_rented, "Módulos Alugados": modules_rented, "Módulos Próprios": modules_owned, "Receita": receita, "Manutenção": manut, "Aluguel": aluguel_mensal_corrente, "Parcelas Terrenos (Novos)": parcelas_terrenos_novos_mensal_corrente, "Gastos": manut + aluguel_mensal_corrente + parcelas_terrenos_novos_mensal_corrente, "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total, "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa, "Investimento Total Acumulado": investimento_total, "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac, "Módulos Comprados no Ano": novos_modulos_comprados, "Patrimônio Líquido": patrimonio_liquido })
    return pd.DataFrame(rows)

# ---------------------------
# Inicialização e Gerenciamento do Estado
# ---------------------------
def get_default_config():
    return {
        'rented': { 'modules_init': 1, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_per_new_module': 750.0 },
        'owned': { 
            'modules_init': 0, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 
            'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 
            'monthly_land_plot_parcel': 0.0, 
            'land_value_per_module': 50000.0, # NOVO CAMPO
            'land_total_value': 0.0, 'land_down_payment_pct': 20.0, 'land_installments': 120 
        },
        'global': { 'years': 15, 'max_withdraw_value': 50000.0, 'aportes': [], 'retiradas': [], 'fundos': [] }
    }

if 'config' not in st.session_state:
    st.session_state.config = get_default_config()

if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state: st.session_state.comparison_df = pd.DataFrame()
if 'active_page' not in st.session_state: st.session_state.active_page = 'Dashboard'

# ---------------------------
# BARRA DE NAVEGAÇÃO LATERAL
# ---------------------------
with st.sidebar:
    st.markdown("<h1>Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p>Projeção com reinvestimento</p>", unsafe_allow_html=True)
    st.session_state.active_page = st.radio("Menu Principal", ["Dashboard", "Planilhas", "Configurações"], key="navigation_radio", label_visibility="collapsed")

# ---------------------------
# PÁGINA DE CONFIGURAÇÕES
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.title("Configurações de Investimento")
    st.markdown("<p class='subhead'>Ajuste os parâmetros da simulação financeira e adicione eventos.</p>", unsafe_allow_html=True)
    if st.button("🔄 Resetar Configurações", type="secondary"):
        st.session_state.config = get_default_config()
        st.rerun()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Investimento com Terreno Alugado")
    c1, c2 = st.columns(2)
    cfg_r = st.session_state.config['rented']
    cfg_r['modules_init'] = c1.number_input("Módulos iniciais (alugados)", 0, value=cfg_r['modules_init'], key="rent_mod_init")
    cfg_r['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_r['cost_per_module'], format="%.2f", key="rent_cost_mod")
    cfg_r['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_r['revenue_per_module'], format="%.2f", key="rent_rev_mod")
    cfg_r['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_r['maintenance_per_module'], format="%.2f", key="rent_maint_mod")
    cfg_r['cost_correction_rate'] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg_r['cost_correction_rate'], format="%.1f", key="rent_corr_rate")
    cfg_r['rent_value'] = c2.number_input("Aluguel mensal fixo (R$)", 0.0, value=cfg_r['rent_value'], format="%.2f", key="rent_base_rent")
    cfg_r['rent_per_new_module'] = c1.number_input("Custo de aluguel por novo módulo (R$)", 0.0, value=cfg_r['rent_per_new_module'], format="%.2f", key="rent_new_rent")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Investimento com Terreno Comprado")
    cfg_o = st.session_state.config['owned']
    st.markdown("###### Financiamento do Terreno Inicial (Opcional)")
    cfg_o['land_total_value'] = st.number_input("Valor total do terreno inicial (R$)", 0.0, value=cfg_o['land_total_value'], format="%.2f", key="own_total_land_val")
    valor_parcela = 0.0
    if cfg_o['land_total_value'] > 0:
        c1_fin, c2_fin = st.columns(2)
        cfg_o['land_down_payment_pct'] = c1_fin.number_input("Entrada (%)", 0.0, 100.0, value=cfg_o['land_down_payment_pct'], format="%.1f", key="own_down_pay")
        cfg_o['land_installments'] = c1_fin.number_input("Quantidade de parcelas", 1, 480, value=cfg_o['land_installments'], key="own_install")
        valor_entrada = cfg_o['land_total_value'] * (cfg_o['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_o['land_total_value'] - valor_entrada
        valor_parcela = valor_financiado / cfg_o['land_installments'] if cfg_o['land_installments'] > 0 else 0
        c2_fin.metric("Valor da Entrada", fmt_brl(valor_entrada))
        c2_fin.metric("Valor da Parcela", fmt_brl(valor_parcela))
        cfg_o['monthly_land_plot_parcel'] = valor_parcela
    else:
        # Garante que o valor seja zerado se o financiamento for desativado
        if valor_parcela == cfg_o.get('monthly_land_plot_parcel', 0.0):
             cfg_o['monthly_land_plot_parcel'] = 0.0

    st.markdown("---")
    st.markdown("###### Parâmetros do Módulo Próprio")
    c1, c2 = st.columns(2)
    cfg_o['modules_init'] = c1.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
    cfg_o['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
    cfg_o['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
    cfg_o['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
    cfg_o['cost_correction_rate'] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg_o['cost_correction_rate'], format="%.1f", key="own_corr_rate")
    
    # --- NOVO CAMPO ADICIONADO AQUI ---
    cfg_o['land_value_per_module'] = c1.number_input("Valor do terreno por novo módulo (R$)", 0.0, value=cfg_o.get('land_value_per_module', 50000.0), format="%.2f", key="own_land_value_per_module", help="O valor do ativo (terra) a ser adicionado ao patrimônio por cada novo módulo próprio.")
    
    cfg_o['monthly_land_plot_parcel'] = c2.number_input( "Parcela mensal por novo terreno (R$)", 0.0, value=cfg_o.get('monthly_land_plot_parcel', 0.0), format="%.2f", key="own_land_parcel", disabled=(cfg_o['land_total_value'] > 0), help="Este valor é preenchido automaticamente se um financiamento de terreno inicial for configurado." )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Restante da página de configurações (Parâmetros Globais, Eventos) permanece o mesmo
    # ...

# O restante do código para as páginas de Dashboard e Planilhas permanece o mesmo da versão anterior.
# Cole o restante do código a partir daqui.
