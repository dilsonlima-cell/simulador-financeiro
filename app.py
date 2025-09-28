# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA E ESTILOS "EXCEL DASHBOARD" ---
st.set_page_config(page_title="Planilha de Gestão de Portfólio", layout="wide", initial_sidebar_state="collapsed")

# --- PALETA DE CORES (PARA LÓGICA E TEMATIZAÇÃO CONSISTENTE) ---
KPI_YELLOW = "#FFC000"
KPI_GREEN = "#70AD47"
KPI_BLUE = "#4472C4"
KPI_RED = "#C00000"
KPI_TEAL = "#2F75B5"
CARD_COLOR = "#FFFFFF" # Mantido como variável Python para uso em Plotly e outros
CHART_ORANGE = "#ED7D31"
CHART_GRAY = "#A5A5A5"

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Calibri:wght@400;700&display=swap');

        /* --- Variáveis do Tema Inspirado no Excel --- */
        :root {{
            --font-family: 'Calibri', sans-serif;
            --color-bg: #EAEAEA; /* Cinza claro de fundo */
            --color-card-bg: {CARD_COLOR}; /* Usando a variável Python para consistência */
            --color-text: #000000;
            --color-header-bg: #44546A; /* Azul-acinzentado escuro do header */
            --color-header-text: #FFFFFF;
            --color-border: #D0D0D0;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.1);
            --border-radius: 0px; /* Bordas retas como no Excel */
        }}

        /* --- Estilos Globais --- */
        body, .stApp {{
            font-family: var(--font-family);
            color: var(--color-text);
            background-color: var(--color-bg) !important;
        }}
        .main .block-container {{ 
            padding: 1.5rem 2rem; 
        }}
        h1, h2, h3, h4, h5, h6, label, .st-emotion-cache-16idsys p, .st-emotion-cache-nahz7x p {{
            font-weight: 700 !important;
            color: var(--color-text) !important;
            font-family: var(--font-family);
        }}
        
        /* --- Esconde a barra lateral padrão do Streamlit --- */
        [data-testid="stSidebar"] {{ display: none; }}

        /* --- Header Superior e Abas --- */
        .excel-header {{
            background-color: var(--color-header-bg);
            padding: 0.5rem 2rem 0 2rem;
            margin: -1.5rem -2rem 1.5rem -2rem; /* Puxa para as bordas e ajusta espaçamento */
        }}
        .tabs-nav {{
            display: flex;
            background-color: var(--color-header-bg);
        }}
        .tabs-nav a {{
            padding: 0.6rem 1.2rem;
            text-decoration: none;
            color: var(--color-header-text);
            font-weight: 700;
            border-right: 1px solid #5A697A;
            background-color: #5F7897; /* Cor da aba inativa */
        }}
        .tabs-nav a.active {{
            background-color: #2F5597; /* Cor da aba ativa */
        }}

        /* --- Estilo dos KPIs Coloridos --- */
        .kpi-block {{
            padding: 1rem;
            color: var(--color-header-text);
            border-radius: var(--border-radius);
            height: 100%;
        }}
        .kpi-block-title {{
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: white; /* Força texto branco para contraste */
        }}
        .kpi-block-value {{
            font-size: 2rem;
            font-weight: 700;
            color: white; /* Força texto branco para contraste */
        }}

        /* --- Ajustes para botões e informações (resolvendo fundos pretos) --- */
        /* Botões */
        .stButton button {{
            background-color: #2F5597; /* Azul mais escuro, como a aba ativa */
            color: white;
            border: 1px solid #2F5597;
            border-radius: var(--border-radius);
            padding: 0.5rem 1rem;
            font-weight: 700;
        }}
        .stButton button:hover {{
            background-color: #3B66A8; /* Um pouco mais claro no hover */
            border-color: #3B66A8;
            color: white;
        }}
        .stButton button:focus:not(:active) {{
            border-color: #7AA2DA; /* Borda de foco */
            box-shadow: none;
            color: white;
        }}
        /* st.info - Ajusta o texto para ser legível */
        .st-emotion-cache-nahz7x p {{ /* Seletor para o texto dentro do st.info */
            color: var(--color-text) !important; /* Força a cor do texto padrão */
        }}
        .st-emotion-cache-nahz7x {{ /* Fundo do st.info */
            background-color: #d1ecf1 !important; /* Cor de info padrão mais clara */
            border-color: #bee5eb !important;
            color: #0c5460 !important; /* Cor do texto padrão do info */
            border-radius: 0px;
        }}
        /* st.warning (para o erro do NameError) */
        .st-emotion-cache-1f06xja p {{
            color: #721c24 !important; /* Texto mais escuro */
        }}
        .st-emotion-cache-1f06xja {{
            background-color: #f8d7da !important; /* Fundo mais claro */
            border-color: #f5c6cb !important;
            border-radius: 0px;
        }}
        /* Container com borda */
        .st-emotion-cache-1mds4y6 {{ /* Selector for st.container(border=True) */
            background-color: var(--color-card-bg);
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            padding: 1rem;
        }}
        /* Text inputs, number inputs, selects, toggles */
        .st-emotion-cache-eq1z3c, .st-emotion-cache-e3zps9, .st-emotion-cache-j7rqx1, .st-emotion-cache-1c7zf7t {{ /* General input styling */
            background-color: white !important;
            color: var(--color-text) !important;
            border-radius: var(--border-radius);
            border: 1px solid var(--color-border);
        }}
        .st-emotion-cache-1c7zf7t input[type="text"], .st-emotion-cache-1c7zf7t input[type="number"] {{
            color: var(--color-text) !important;
        }}
        .st-emotion-cache-1c7zf7t > div > label {{ /* Label for toggle */
            color: var(--color-text) !important;
        }}
        .st-emotion-cache-1c7zf7t .st-emotion-cache-uf99v8 {{ /* Toggle switch background */
            background-color: var(--color-border) !important;
        }}
        .st-emotion-cache-1c7zf7t .st-emotion-cache-uf99v8[aria-checked="true"] {{
            background-color: {KPI_BLUE} !important; /* Active toggle color */
        }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# NAVEGAÇÃO E CABEÇALHO
# ---------------------------
def render_header_and_tabs():
    active_page = st.session_state.get('active_page', 'Dashboard')
    dashboard_class = "active" if active_page == "Dashboard" else ""
    planilhas_class = "active" if active_page == "Planilhas" else ""
    config_class = "active" if active_page == "Configurações" else ""

    st.markdown(f"""
        <header class="excel-header">
            <nav class="tabs-nav">
                <a href="?page=Dashboard" target="_self" class="{dashboard_class}">DASHBOARD</a>
                <a href="?page=Planilhas" target="_self" class="{planilhas_class}">RELATÓRIOS E DADOS</a>
                <a href="?page=Configurações" target="_self" class="{config_class}">CONFIGURAÇÕES</a>
            </nav>
        </header>
    """, unsafe_allow_html=True)

query_params = st.query_params
if 'page' in query_params:
    st.session_state.active_page = query_params.get('page')
else:
    if 'active_page' not in st.session_state:
        st.session_state.active_page = "Dashboard"

render_header_and_tabs()

# ---------------------------
# Funções Utilitárias e de Lógica
# ---------------------------
def render_kpi_block(title, value, color):
    st.markdown(f"""
        <div class="kpi-block" style="background-color: {color};">
            <div class="kpi-block-title">{title.upper()}</div>
            <div class="kpi-block-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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

def get_default_config():
    return {
        'rented': { 'modules_init': 1, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_per_new_module': 750.0 },
        'owned': { 'modules_init': 0, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'monthly_land_plot_parcel': 0.0, 'land_total_value': 0.0, 'land_down_payment_pct': 20.0, 'land_installments': 120 },
        'global': { 'years': 15, 'max_withdraw_value': 50000.0, 'aportes': [], 'retiradas': [], 'fundos': [] }
    }

# --- INICIALIZAÇÃO DO ESTADO ---
if 'config' not in st.session_state: st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state: st.session_state.comparison_df = pd.DataFrame()
if 'column_visibility' not in st.session_state: st.session_state.column_visibility = {}


# ---------------------------
# PÁGINA DE CONFIGURAÇÕES
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.title("Configurações de Investimento")
    st.markdown("Ajuste os parâmetros da simulação financeira e adicione eventos.")
    if st.button("🔄 Resetar Configurações"):
        st.session_state.config = get_default_config()
        st.rerun()

    with st.container(border=True):
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("Investimento com Terreno Comprado")
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
            cfg_o['monthly_land_plot_parcel'] = valor_parcela
        
        st.markdown("---")
        st.markdown("###### Parâmetros do Módulo Próprio")
        c1, c2 = st.columns(2)
        cfg_o['modules_init'] = c1.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
        cfg_o['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
        cfg_o['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
        cfg_o['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
        cfg_o['cost_correction_rate'] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg_o['cost_correction_rate'], format="%.1f", key="own_corr_rate")
        cfg_o['monthly_land_plot_parcel'] = c2.number_input( "Parcela mensal por novo terreno (R$)", 0.0, value=cfg_o.get('monthly_land_plot_parcel', 0.0), format="%.2f", key="own_land_parcel", disabled=(cfg_o['land_total_value'] > 0))

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("Parâmetros Globais e Eventos Financeiros")
        cfg_g = st.session_state.config['global']
        c1, c2 = st.columns(2)
        cfg_g['years'] = c1.number_input("Horizonte de investimento (anos)", 1, 50, cfg_g['years'])
        cfg_g['max_withdraw_value'] = c2.number_input("Valor máximo de retirada mensal (R$)", 0.0, value=cfg_g['max_withdraw_value'], format="%.2f", help="Teto para retiradas baseadas em % do lucro.")
        
        st.markdown("---")
        st.markdown("<h6>Aportes (investimentos pontuais)</h6>", unsafe_allow_html=True)
        for i, aporte in enumerate(st.session_state.config['global']['aportes']):
            cols = st.columns([2, 3, 1])
            aporte['mes'] = cols[0].number_input("Mês", min_value=1, value=aporte['mes'], key=f"aporte_mes_{i}")
            aporte['valor'] = cols[1].number_input("Valor (R$)", min_value=0.0, value=aporte['valor'], format="%.2f", key=f"aporte_valor_{i}")
            if cols[2].button("Remover", key=f"aporte_remover_{i}"):
                st.session_state.config['global']['aportes'].pop(i); st.rerun()
        if st.button("Adicionar Aporte"):
            st.session_state.config['global']['aportes'].append({"mes": 1, "valor": 0.0}); st.rerun()
        
        st.markdown("---")
        st.markdown("<h6>Retiradas (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
        for i, retirada in enumerate(st.session_state.config['global']['retiradas']):
            cols = st.columns([2, 3, 1])
            retirada['mes'] = cols[0].number_input("Mês início", min_value=1, value=retirada['mes'], key=f"retirada_mes_{i}")
            retirada['percentual'] = cols[1].number_input("% do lucro", min_value=0.0, max_value=100.0, value=retirada['percentual'], format="%.1f", key=f"retirada_pct_{i}")
            if cols[2].button("Remover", key=f"retirada_remover_{i}"):
                st.session_state.config['global']['retiradas'].pop(i); st.rerun()
        if st.button("Adicionar Retirada"):
            st.session_state.config['global']['retiradas'].append({"mes": 1, "percentual": 30.0}); st.rerun()
        
        st.markdown("---")
        st.markdown("<h6>Fundos de Reserva (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
        for i, fundo in enumerate(st.session_state.config['global']['fundos']):
            cols = st.columns([2, 3, 1])
            fundo['mes'] = cols[0].number_input("Mês início", min_value=1, value=fundo['mes'], key=f"fundo_mes_{i}")
            fundo['percentual'] = cols[1].number_input("% do lucro", min_value=0.0, max_value=100.0, value=fundo['percentual'], format="%.1f", key=f"fundo_pct_{i}")
            if cols[2].button("Remover", key=f"fundo_remover_{i}"):
                st.session_state.config['global']['fundos'].pop(i); st.rerun()
        if st.button("Adicionar Fundo"):
            st.session_state.config['global']['fundos'].append({"mes": 1, "percentual": 10.0}); st.rerun()

# ---------------------------
# PÁGINA DO DASHBOARD
# ---------------------------
if st.session_state.active_page == 'Dashboard':
    with st.container(border=True):
        st.subheader("Simulador de Estratégias")
        strat_cols = st.columns(3)
        if strat_cols[0].button("📈 Simular: Comprar", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'buy'); st.session_state.comparison_df = pd.DataFrame()
        if strat_cols[1].button("📈 Simular: Alugar", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'rent'); st.session_state.comparison_df = pd.DataFrame()
        if strat_cols[2].button("📈 Simular: Intercalar", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'alternate'); st.session_state.comparison_df = pd.DataFrame()
        st.markdown("---")
        if st.button("📊 Comparar Todas as Estratégias", use_container_width=True):
            with st.spinner("Calculando as três simulações..."):
                df_buy = simulate(st.session_state.config, 'buy'); df_buy['Estratégia'] = 'Comprar'
                df_rent = simulate(st.session_state.config, 'rent'); df_rent['Estratégia'] = 'Alugar'
                df_alt = simulate(st.session_state.config, 'alternate'); df_alt['Estratégia'] = 'Intercalar'
                st.session_state.comparison_df = pd.concat([df_buy, df_rent, df_alt]); st.session_state.simulation_df = pd.DataFrame()

    st.markdown("---")

    if not st.session_state.comparison_df.empty:
        st.header("Análise Comparativa de Estratégias")
        df_comp = st.session_state.comparison_df
        final_buy = df_comp[df_comp['Estratégia'] == 'Comprar'].iloc[-1]
        final_rent = df_comp[df_comp['Estratégia'] == 'Alugar'].iloc[-1]
        final_alt = df_comp[df_comp['Estratégia'] == 'Intercalar'].iloc[-1]
        kpi_cols = st.columns(4)
        with kpi_cols[0]: render_kpi_block("Patrimônio (Comprar)", fmt_brl(final_buy['Patrimônio Líquido']), KPI_BLUE)
        with kpi_cols[1]: render_kpi_block("Patrimônio (Alugar)", fmt_brl(final_rent['Patrimônio Líquido']), KPI_TEAL)
        with kpi_cols[2]: render_kpi_block("Patrimônio (Intercalar)", fmt_brl(final_alt['Patrimônio Líquido']), CHART_ORANGE)
        with kpi_cols[3]:
            best_strategy = pd.Series({'Comprar': final_buy['Patrimônio Líquido'], 'Alugar': final_rent['Patrimônio Líquido'], 'Intercalar': final_alt['Patrimônio Líquido']}).idxmax()
            render_kpi_block("Melhor Estratégia", best_strategy, KPI_GREEN)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Métricas ao Longo do Tempo")
            metric_options = { "Patrimônio Líquido": "Patrimônio Líquido", "Módulos Ativos": "Módulos Ativos", "Retiradas Acumuladas": "Retiradas Acumuladas"}
            selected_metric = st.selectbox("Selecione uma métrica para comparar:", options=list(metric_options.keys()))
            fig_comp = px.line(df_comp, x="Mês", y=metric_options[selected_metric], color='Estratégia', color_discrete_map={'Comprar': KPI_BLUE, 'Alugar': KPI_TEAL, 'Intercalar': CHART_ORANGE })
            fig_comp.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font_family="Calibri")
            st.plotly_chart(fig_comp, use_container_width=True)

    elif not st.session_state.simulation_df.empty:
        st.header("Resultados da Simulação")
        df = st.session_state.simulation_df; final = df.iloc[-1]; cfg = st.session_state.config
        inv_inicial_modulos = (cfg['rented']['modules_init'] * cfg['rented']['cost_per_module']) + (cfg['owned']['modules_init'] * cfg['owned']['cost_per_module'])
        entrada_terreno = 0
        if cfg['owned']['land_total_value'] > 0:
            entrada_terreno = cfg['owned']['land_total_value'] * (cfg['owned']['land_down_payment_pct'] / 100.0)
        investimento_inicial_total = inv_inicial_modulos + entrada_terreno
        
        kpi_col, chart_col = st.columns([1, 3])
        with kpi_col:
            render_kpi_block("Valor Investido", fmt_brl(investimento_inicial_total), KPI_YELLOW)
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            render_kpi_block("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']), KPI_GREEN)
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            render_kpi_block("Retiradas Acumuladas", fmt_brl(final['Retiradas Acumuladas']), KPI_BLUE)
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            render_kpi_block("Fundo Acumulado", fmt_brl(final['Fundo Acumulado']), KPI_TEAL)
        
        with chart_col:
            with st.container(border=True):
                st.subheader("Evolução do Patrimônio vs. Investimento")
                fig_pat = go.Figure()
                fig_pat.add_trace(go.Scatter(x=df["Mês"], y=df["Patrimônio Líquido"], name="Patrimônio", line=dict(color=KPI_GREEN, width=2.5)))
                fig_pat.add_trace(go.Scatter(x=df["Mês"], y=df["Investimento Total Acumulado"], name="Investimento", line=dict(color=CHART_GRAY, width=1.5)))
                fig_pat.update_layout(height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font_family="Calibri")
                st.plotly_chart(fig_pat, use_container_width=True)

    else:
        st.info("👆 Selecione uma estratégia de simulação para visualizar os resultados.")

# ---------------------------
# PÁGIN
