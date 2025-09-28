# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA E ESTILOS AVANÇADOS ---
st.set_page_config(page_title="Simulador Modular", layout="wide", initial_sidebar_state="collapsed")

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Inter:wght@400;500&display=swap');

        /* --- Variáveis do Tema "Corporate Insight" --- */
        :root {{
            --font-heading: 'Poppins', sans-serif;
            --font-body: 'Inter', sans-serif;
            --color-bg: #F8F9FA;
            --color-card-bg: #FFFFFF;
            --color-text: #212529;
            --color-muted-text: #6C757D;
            --color-primary: #005A9E;
            --color-primary-hover: #004376;
            --color-border: #DEE2E6;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
            --border-radius: 12px;
        }}

        /* --- Reset e Estilos Globais --- */
        body {{
            font-family: var(--font-body);
            color: var(--color-text);
            background-color: var(--color-bg);
        }}
        .main .block-container {{ padding: 1.5rem 2.5rem; }}
        h1, h2, h3, h4, h5, h6, label {{
            font-family: var(--font-heading);
            font-weight: 700 !important;
            color: var(--color-text) !important;
        }}
        h1 {{ font-size: 2.25rem; }}
        h2 {{ font-size: 1.75rem; }}
        h3 {{ font-size: 1.25rem; }}
        
        /* --- Esconde a barra lateral padrão do Streamlit --- */
        [data-testid="stSidebar"] {{
            display: none;
        }}

        /* --- Estilo dos Cartões de Conteúdo (usado em Configurações) --- */
        .card {{
            background: var(--color-card-bg);
            border-radius: var(--border-radius);
            padding: 1.5rem 2rem;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--color-border);
            height: 100%;
        }}

        /* --- Estilo dos Cartões de KPI --- */
        .kpi-card {{
            border-radius: var(--border-radius);
            padding: 1.25rem;
            color: white;
            box-shadow: var(--shadow-md);
            border: none;
            height: 100%;
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }}
        .kpi-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        .kpi-card-title {{
            font-family: var(--font-body);
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
            opacity: 0.9;
        }}
        .kpi-card-value {{
            font-family: var(--font-heading);
            font-size: 2rem;
            font-weight: 700;
        }}

        /* --- Estilo dos Botões CTA --- */
        .stButton > button {{
            border-radius: 8px;
            border: 2px solid var(--color-primary);
            background-color: var(--color-primary);
            color: white;
            padding: 12px 28px;
            font-weight: 600;
            font-family: var(--font-heading);
            transition: all 0.2s ease-in-out;
        }}
        .stButton > button:hover {{
            background-color: var(--color-primary-hover);
            border-color: var(--color-primary-hover);
        }}
        .stButton > button[kind="secondary"] {{
            background-color: transparent;
            color: var(--color-primary);
        }}
        .stButton > button[kind="secondary"]:hover {{
            background-color: rgba(0, 90, 158, 0.1);
            color: var(--color-primary-hover);
            border-color: var(--color-primary);
        }}
        
        /* --- Estilo do Menu Superior Fixo (adicionado via HTML) --- */
        .top-nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background-color: #212529; /* Cinza escuro */
            padding: 0.75rem 2.5rem;
            box-shadow: var(--shadow-sm);
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .top-nav .title {{
            font-family: var(--font-heading);
            font-weight: 700;
            font-size: 1.25rem;
            color: #FFFFFF;
        }}
        .top-nav .nav-links a {{
            color: #E9ECEF; /* Branco suave */
            margin-left: 1.5rem;
            text-decoration: none;
            font-family: var(--font-body);
            font-weight: 500;
            padding-bottom: 5px;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        .top-nav .nav-links a:hover {{
            color: #FFFFFF;
        }}
        .top-nav .nav-links a.active {{
            color: #FFFFFF;
            font-weight: 600;
            border-bottom-color: var(--color-primary);
        }}
        .stApp {{
            margin-top: 80px; /* Espaço para o menu superior fixo */
        }}
    </style>
""", unsafe_allow_html=True)


# --- PALETA DE CORES (PARA GRÁFICOS) ---
PRIMARY_COLOR = "#005A9E"
SUCCESS_COLOR = "#28A745"
DANGER_COLOR = "#DC3545"
WARNING_COLOR = "#FFC107"
INFO_COLOR = "#17A2B8"
MUTED_TEXT_COLOR = "#6C757D"
CARD_COLOR = "#FFFFFF"

# ---------------------------
# NAVEGAÇÃO CUSTOMIZADA
# ---------------------------
def render_custom_nav():
    active_page = st.session_state.get('active_page', 'Dashboard')
    dashboard_class = "active" if active_page == "Dashboard" else ""
    planilhas_class = "active" if active_page == "Planilhas" else ""
    config_class = "active" if active_page == "Configurações" else ""
    st.markdown(f"""
        <nav class="top-nav">
            <div class="title">Simulador Modular</div>
            <div class="nav-links">
                <a href="?page=Dashboard" target="_self" class="{dashboard_class}">Dashboard</a>
                <a href="?page=Planilhas" target="_self" class="{planilhas_class}">Relatórios</a>
                <a href="?page=Configurações" target="_self" class="{config_class}">Configurações</a>
            </div>
        </nav>
    """, unsafe_allow_html=True)

# Lógica para controlar a página ativa usando query params
query_params = st.query_params
if 'page' in query_params:
    st.session_state.active_page = query_params.get('page')
else:
    # Define 'Dashboard' como padrão na primeira execução
    if 'active_page' not in st.session_state:
        st.session_state.active_page = "Dashboard"

render_custom_nav()


# --- FUNÇÃO HELPER PARA KPIs ---
def render_kpi_card(title, value, color):
    st.markdown(f"""
        <div class="kpi-card" style="background: {color};">
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
    valor_terrenos_adicionais = 0.0
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
                    elif reinvestment_strategy == 'rent':
                        modules_rented += novos_modulos_comprados
                        aluguel_mensal_corrente += novos_modulos_comprados * cfg_rented['rent_per_new_module']
                    elif reinvestment_strategy == 'alternate':
                        for _ in range(novos_modulos_comprados):
                            if compra_intercalada_counter % 2 == 0:
                                modules_owned += 1
                                parcelas_terrenos_novos_mensal_corrente += cfg_owned['monthly_land_plot_parcel']
                            else:
                                modules_rented += 1
                                aluguel_mensal_corrente += cfg_rented['rent_per_new_module']
                            compra_intercalada_counter += 1
            custo_modulo_atual_owned *= (1 + cfg_owned['cost_correction_rate'] / 100.0)
            custo_modulo_atual_rented *= (1 + cfg_rented['cost_correction_rate'] / 100.0)
        patrimonio_liquido = ((modules_owned + modules_rented) * custo_modulo_atual_owned) + caixa + fundo_ac + cfg_owned['land_total_value'] + valor_terrenos_adicionais
        rows.append({ "Mês": m, "Ano": (m - 1) // 12 + 1, "Módulos Ativos": modules_owned + modules_rented, "Módulos Alugados": modules_rented, "Módulos Próprios": modules_owned, "Receita": receita, "Manutenção": manut, "Aluguel": aluguel_mensal_corrente, "Parcelas Terrenos (Novos)": parcelas_terrenos_novos_mensal_corrente, "Gastos": manut + aluguel_mensal_corrente + parcelas_terrenos_novos_mensal_corrente, "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total, "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa, "Investimento Total Acumulado": investimento_total, "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac, "Módulos Comprados no Ano": novos_modulos_comprados, "Patrimônio Líquido": patrimonio_liquido })
    return pd.DataFrame(rows)


# ---------------------------
# Inicialização e Gerenciamento do Estado
# ---------------------------
def get_default_config():
    return {
        'rented': { 'modules_init': 1, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_per_new_module': 750.0 },
        'owned': { 'modules_init': 0, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'monthly_land_plot_parcel': 0.0, 'land_total_value': 0.0, 'land_down_payment_pct': 20.0, 'land_installments': 120 },
        'global': { 'years': 15, 'max_withdraw_value': 50000.0, 'aportes': [], 'retiradas': [], 'fundos': [] }
    }

if 'config' not in st.session_state:
    st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state: st.session_state.comparison_df = pd.DataFrame()
if 'column_visibility' not in st.session_state: st.session_state.column_visibility = {}


# ---------------------------
# PÁGINA DE CONFIGURAÇÕES
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.title("Configurações de Investimento")
    st.markdown("Ajuste os parâmetros da simulação financeira e adicione eventos.")
    
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
    st.markdown("<h6>Financiamento do Terreno Inicial (Opcional)</h6>", unsafe_allow_html=True)
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
        if valor_parcela == cfg_o.get('monthly_land_plot_parcel', 0.0):
             cfg_o['monthly_land_plot_parcel'] = 0.0
    st.markdown("---")
    st.markdown("<h6>Parâmetros do Módulo Próprio</h6>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    cfg_o['modules_init'] = c1.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
    cfg_o['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
    cfg_o['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
    cfg_o['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
    cfg_o['cost_correction_rate'] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg_o['cost_correction_rate'], format="%.1f", key="own_corr_rate")
    cfg_o['monthly_land_plot_parcel'] = c1.number_input( "Parcela mensal por novo terreno (R$)", 0.0, value=cfg_o.get('monthly_land_plot_parcel', 0.0), format="%.2f", key="own_land_parcel", disabled=(cfg_o['land_total_value'] > 0), help="Este valor é preenchido automaticamente se um financiamento de terreno inicial for configurado." )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Parâmetros Globais e Eventos Financeiros")
    c1, c2 = st.columns(2)
    cfg_g = st.session_state.config['global']
    cfg_g['years'] = c1.number_input("Horizonte de investimento (anos)", 1, 50, cfg_g['years'])
    cfg_g['max_withdraw_value'] = c2.number_input("Valor máximo de retirada mensal (R$)", 0.0, value=cfg_g['max_withdraw_value'], format="%.2f", help="Teto para retiradas baseadas em % do lucro.")
    st.markdown("---")
    st.markdown("<h6>Aportes (investimentos pontuais)</h6>", unsafe_allow_html=True)
    for i, aporte in enumerate(st.session_state.config['global']['aportes']):
        cols = st.columns([2, 3, 1])
        aporte['mes'] = cols[0].number_input("Mês", min_value=1, value=aporte['mes'], key=f"aporte_mes_{i}")
        aporte['valor'] = cols[1].number_input("Valor (R$)", min_value=0.0, value=aporte['valor'], format="%.2f", key=f"aporte_valor_{i}")
        if cols[2].button("Remover", key=f"aporte_remover_{i}", type="secondary"):
            st.session_state.config['global']['aportes'].pop(i)
            st.rerun()
    if st.button("Adicionar Aporte"):
        st.session_state.config['global']['aportes'].append({"mes": 1, "valor": 0.0})
        st.rerun()
    st.markdown("---")
    st.markdown("<h6>Retiradas (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, retirada in enumerate(st.session_state.config['global']['retiradas']):
        cols = st.columns([2, 3, 1])
        retirada['mes'] = cols[0].number_input("Mês início", min_value=1, value=retirada['mes'], key=f"retirada_mes_{i}")
        retirada['percentual'] = cols[1].number_input("% do lucro", min_value=0.0, max_value=100.0, value=retirada['percentual'], format="%.1f", key=f"retirada_pct_{i}")
        if cols[2].button("Remover", key=f"retirada_remover_{i}", type="secondary"):
            st.session_state.config['global']['retiradas'].pop(i)
            st.rerun()
    if st.button("Adicionar Retirada"):
        st.session_state.config['global']['retiradas'].append({"mes": 1, "percentual": 30.0})
        st.rerun()
    st.markdown("---")
    st.markdown("<h6>Fundos de Reserva (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, fundo in enumerate(st.session_state.config['global']['fundos']):
        cols = st.columns([2, 3, 1])
        fundo['mes'] = cols[0].number_input("Mês início", min_value=1, value=fundo['mes'], key=f"fundo_mes_{i}")
        fundo['percentual'] = cols[1].number_input("% do lucro", min_value=0.0, max_value=100.0, value=fundo['percentual'], format="%.1f", key=f"fundo_pct_{i}")
        if cols[2].button("Remover", key=f"fundo_remover_{i}", type="secondary"):
            st.session_state.config['global']['fundos'].pop(i)
            st.rerun()
    if st.button("Adicionar Fundo"):
        st.session_state.config['global']['fundos'].append({"mes": 1, "percentual": 10.0})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# PÁGINA DO DASHBOARD
# ---------------------------
if st.session_state.active_page == 'Dashboard':
    st.title("Dashboard Estratégico")
    st.markdown("Simule e compare estratégias de reinvestimento para tomar a melhor decisão.")

    with st.container(border=True):
        strat_cols = st.columns(3)
        if strat_cols[0].button("📈 Simular: Comprar", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'buy')
                st.session_state.comparison_df = pd.DataFrame()
        if strat_cols[1].button("📈 Simular: Alugar", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'rent')
                st.session_state.comparison_df = pd.DataFrame()
        if strat_cols[2].button("📈 Simular: Intercalar", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'alternate')
                st.session_state.comparison_df = pd.DataFrame()

        st.markdown("---")
        if st.button("📊 Comparar Todas as Estratégias", use_container_width=True):
            with st.spinner("Calculando as três simulações..."):
                df_buy = simulate(st.session_state.config, 'buy'); df_buy['Estratégia'] = 'Comprar'
                df_rent = simulate(st.session_state.config, 'rent'); df_rent['Estratégia'] = 'Alugar'
                df_alt = simulate(st.session_state.config, 'alternate'); df_alt['Estratégia'] = 'Intercalar'
                st.session_state.comparison_df = pd.concat([df_buy, df_rent, df_alt])
                st.session_state.simulation_df = pd.DataFrame()

    if not st.session_state.comparison_df.empty:
        st.header("Análise Comparativa")
        df_comp = st.session_state.comparison_df
        final_buy = df_comp[df_comp['Estratégia'] == 'Comprar'].iloc[-1]
        final_rent = df_comp[df_comp['Estratégia'] == 'Alugar'].iloc[-1]
        final_alt = df_comp[df_comp['Estratégia'] == 'Intercalar'].iloc[-1]
        st.subheader("Resultados Finais")
        kpi_cols = st.columns(4)
        with kpi_cols[0]: render_kpi_card("Patrimônio (Comprar)", fmt_brl(final_buy['Patrimônio Líquido']), PRIMARY_COLOR)
        with kpi_cols[1]: render_kpi_card("Patrimônio (Alugar)", fmt_brl(final_rent['Patrimônio Líquido']), MUTED_TEXT_COLOR)
        with kpi_cols[2]: render_kpi_card("Patrimônio (Intercalar)", fmt_brl(final_alt['Patrimônio Líquido']), WARNING_COLOR)
        with kpi_cols[3]:
            best_strategy = pd.Series({'Comprar': final_buy['Patrimônio Líquido'], 'Alugar': final_rent['Patrimônio Líquido'], 'Intercalar': final_alt['Patrimônio Líquido']}).idxmax()
            render_kpi_card("Melhor Estratégia", best_strategy, SUCCESS_COLOR)
        
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Comparativo de Métricas ao Longo do Tempo")
            metric_options = { "Patrimônio Líquido": "Patrimônio Líquido", "Módulos Ativos": "Módulos Ativos", "Retiradas Acumuladas": "Retiradas Acumuladas", "Fundo Acumulado": "Fundo Acumulado", "Caixa (Final Mês)": "Caixa (Final Mês)" }
            selected_metric = st.selectbox("Selecione uma métrica para comparar:", options=list(metric_options.keys()))
            fig_comp = px.line(df_comp, x="Mês", y=metric_options[selected_metric], color='Estratégia', title=f'Comparativo de {selected_metric}', color_discrete_map={'Comprar': PRIMARY_COLOR, 'Alugar': MUTED_TEXT_COLOR, 'Intercalar': WARNING_COLOR })
            fig_comp.update_layout(height=450, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font_family="Inter")
            st.plotly_chart(fig_comp, use_container_width=True)

    elif not st.session_state.simulation_df.empty:
        st.header("Resultados da Simulação")
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        cfg = st.session_state.config
        inv_inicial_modulos = (cfg['rented']['modules_init'] * cfg['rented']['cost_per_module']) + (cfg['owned']['modules_init'] * cfg['owned']['cost_per_module'])
        entrada_terreno = 0
        if cfg['owned']['land_total_value'] > 0:
            entrada_terreno = cfg['owned']['land_total_value'] * (cfg['owned']['land_down_payment_pct'] / 100.0)
        investimento_inicial_total = inv_inicial_modulos + entrada_terreno

        kpi_cols = st.columns(5)
        with kpi_cols[0]: render_kpi_card("Investimento Inicial", fmt_brl(investimento_inicial_total), SUCCESS_COLOR)
        with kpi_cols[1]: render_kpi_card("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']), PRIMARY_COLOR)
        with kpi_cols[2]: render_kpi_card("Retiradas Acumuladas", fmt_brl(final['Retiradas Acumuladas']), DANGER_COLOR)
        with kpi_cols[3]: render_kpi_card("Fundo Acumulado", fmt_brl(final['Fundo Acumulado']), INFO_COLOR)
        with kpi_cols[4]: render_kpi_card("Módulos Ativos Finais", f"{int(final['Módulos Ativos'])}", MUTED_TEXT_COLOR)

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1, st.container(border=True):
            st.subheader("Patrimônio vs. Investimento")
            fig_pat = go.Figure()
            fig_pat.add_trace(go.Scatter(x=df["Mês"], y=df["Patrimônio Líquido"], name="Patrimônio", line=dict(color=PRIMARY_COLOR, width=2.5)))
            fig_pat.add_trace(go.Scatter(x=df["Mês"], y=df["Investimento Total Acumulado"], name="Investimento", line=dict(color=MUTED_TEXT_COLOR, width=1.5)))
            fig_pat.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font_family="Inter")
            st.plotly_chart(fig_pat, use_container_width=True)
        with c2, st.container(border=True):
            st.subheader("Distribuição Final dos Recursos")
            dist_data = { 'Valores': [final['Retiradas Acumuladas'], final['Fundo Acumulado'], final['Caixa (Final Mês)']], 'Categorias': ['Retiradas', 'Fundo Total', 'Caixa Final'] }
            fig_pie = px.pie(dist_data, values='Valores', names='Categorias', color_discrete_sequence=[DANGER_COLOR, INFO_COLOR, WARNING_COLOR], hole=0.4)
            fig_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.1), paper_bgcolor=CARD_COLOR, font_family="Inter")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("👆 Escolha uma estratégia de simulação ou compare todas para visualizar os resultados.")

# ---------------------------
# PÁGINA DE PLANILHAS
# ---------------------------
if st.session_state.active_page == 'Planilhas':
    st.title("Relatórios e Dados Detalhados")
    st.markdown("Explore os dados da simulação mês a mês e personalize a visualização.")
    
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty:
        df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty:
        df_to_show = st.session_state.simulation_df

    if df_to_show.empty:
        st.info("👈 Vá para a página 'Dashboard' para iniciar uma simulação.")
    else:
        df = df_to_show
        
        main_cols = st.columns([6, 4])
        with main_cols[0], st.container(border=True):
            st.subheader("Análise Pontual")
            df_analysis = df
            if 'Estratégia' in df.columns:
                selected_strategy = st.selectbox("Selecione a estratégia para análise:", df['Estratégia'].unique())
                df_analysis = df[df['Estratégia'] == selected_strategy].copy()
            c1, c2 = st.columns(2)
            anos_disponiveis = df_analysis['Ano'].unique()
            selected_year = c1.selectbox("Selecione o ano", options=anos_disponiveis)
            months_in_year = df_analysis[df_analysis['Ano'] == selected_year]['Mês'].unique()
            month_labels = [((m - 1) % 12) + 1 for m in months_in_year]
            selected_month_label = c2.selectbox("Selecione o mês", options=month_labels)
            selected_month_abs = df_analysis[(df_analysis['Ano'] == selected_year) & (((df_analysis['Mês'] - 1) % 12) + 1 == selected_month_label)]['Mês'].iloc[0]
            data_point = df_analysis.loc[df_analysis["Mês"] == selected_month_abs].iloc[0]
            st.markdown("---")
            res_cols = st.columns(4)
            with res_cols[0]:
                render_kpi_card("Total de Módulos", f"{int(data_point['Módulos Ativos'])}", MUTED_TEXT_COLOR)
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                render_kpi_card("Patrimônio Líquido", fmt_brl(data_point['Patrimônio Líquido']), PRIMARY_COLOR)
            with res_cols[1]:
                render_kpi_card("Caixa no Mês", fmt_brl(data_point['Caixa (Final Mês)']), WARNING_COLOR)
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                render_kpi_card("Investimento Total", fmt_brl(data_point['Investimento Total Acumulado']), SUCCESS_COLOR)
            with res_cols[2]:
                render_kpi_card("Fundo (Mês)", fmt_brl(data_point['Fundo (Mês)']), INFO_COLOR)
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                render_kpi_card("Fundo Acumulado", fmt_brl(data_point['Fundo Acumulado']), INFO_COLOR)
            with res_cols[3]:
                render_kpi_card("Retirada (Mês)", fmt_brl(data_point['Retirada (Mês)']), DANGER_COLOR)
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                render_kpi_card("Retiradas Acumuladas", fmt_brl(data_point['Retiradas Acumuladas']), DANGER_COLOR)

        with main_cols[1], st.container(border=True):
            st.subheader("Fluxo Financeiro do Mês")
            chart_data = pd.DataFrame({"Categoria": ["Receita", "Gastos", "Retirada", "Fundo"], "Valor": [data_point['Receita'], data_point['Gastos'], data_point['Retirada (Mês)'], data_point['Fundo (Mês)']]})
            fig_monthly = px.bar(chart_data, x="Categoria", y="Valor", text_auto='.2s', title=f"Mês {selected_month_abs}", color="Categoria", color_discrete_map={"Receita": SUCCESS_COLOR, "Gastos": WARNING_COLOR, "Retirada": DANGER_COLOR, "Fundo": INFO_COLOR})
            fig_monthly.update_layout(showlegend=False, height=450, margin=dict(l=10,r=10,t=40,b=10), plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font_family="Inter")
            st.plotly_chart(fig_monthly, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Tabela Completa da Simulação")
            df_display_base = df
            if 'Estratégia' in df.columns:
                 st.markdown(f"Mostrando dados da estratégia: **{selected_strategy}**")
                 df_display_base = df_analysis
            all_columns = df_display_base.columns.tolist()
            if 'Estratégia' in all_columns: all_columns.remove('Estratégia')
            default_cols = ['Mês', 'Ano', 'Módulos Ativos', 'Receita', 'Gastos', 'Caixa (Final Mês)', 'Patrimônio Líquido']
            if set(st.session_state.column_visibility.keys()) != set(all_columns):
                st.session_state.column_visibility = {col: (col in default_cols) for col in all_columns}
            with st.expander("Exibir/Ocultar Colunas da Tabela"):
                toggle_cols = st.columns(4)
                col_idx = 0
                for col_name in all_columns:
                    with toggle_cols[col_idx % 4]:
                        st.session_state.column_visibility[col_name] = st.toggle(col_name, value=st.session_state.column_visibility.get(col_name, False))
                    col_idx += 1
            cols_to_show = [col for col, is_visible in st.session_state.column_visibility.items() if is_visible]
            
            page_size = 12
            total_pages = (len(df_display_base) - 1) // page_size + 1
            if 'page' not in st.session_state: st.session_state.page = 0
            if st.session_state.page >= total_pages: st.session_state.page = 0
            start_idx = st.session_state.page * page_size
            end_idx = start_idx + page_size
            df_display = df_display_base.iloc[start_idx:end_idx].copy()
            format_cols = ["Receita", "Manutenção", "Aluguel", "Parcelas Terrenos (Novos)", "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado", "Fundo Acumulado", "Retiradas Acumuladas", "Patrimônio Líquido", "Gastos"]
            for col in format_cols:
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
            if cols_to_show:
                st.dataframe( df_display[cols_to_show], use_container_width=True, hide_index=True )
            else:
                st.warning("Selecione ao menos uma coluna para exibir os dados.")
            page_cols = st.columns([1, 1, 8])
            if page_cols[0].button("Anterior", disabled=(st.session_state.page == 0), type="secondary"):
                st.session_state.page -= 1; st.rerun()
            if page_cols[1].button("Próxima", disabled=(st.session_state.page >= total_pages - 1), type="secondary"):
                st.session_state.page += 1; st.rerun()
            page_cols[2].markdown(f"<div style='padding-top:10px; color:var(--color-muted-text)'>Página {st.session_state.page + 1} de {total_pages}</div>", unsafe_allow_html=True)

            st.download_button( "📥 Baixar Relatório Completo (Excel)", data=df_to_excel_bytes(df), file_name="relatorio_simulacao.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
