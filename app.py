# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA E ESTILOS "EXCEL DASHBOARD" ---
st.set_page_config(page_title="Gestão de Portfólio", layout="wide", initial_sidebar_state="collapsed")

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Calibri:wght@400;700&display=swap');

        /* --- Variáveis do Tema Inspirado no Excel --- */
        :root {{
            --font-family: 'Calibri', sans-serif;
            --color-bg: #EAEAEA; /* Cinza claro de fundo */
            --color-card-bg: #FFFFFF;
            --color-text: #000000;
            --color-header-bg: #44546A; /* Azul-acinzentado escuro do header */
            --color-header-text: #FFFFFF;
            --color-kpi-yellow: #FFC000;
            --color-kpi-green: #70AD47;
            --color-kpi-blue: #4472C4;
            --color-kpi-red: #C00000;
            --color-kpi-teal: #2F75B5;
            --color-border: #D0D0D0;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.1);
            --border-radius: 0px; /* Bordas retas como no Excel */
        }}

        /* --- Estilos Globais --- */
        body {{
            font-family: var(--font-family);
            color: var(--color-text);
            background-color: var(--color-bg) !important;
        }}
        .stApp {{
            background-color: var(--color-bg) !important;
        }}
        .main .block-container {{ 
            padding: 1rem 2rem 2rem 2rem; 
        }}
        h1, h2, h3, h4, h5, h6, label, .st-emotion-cache-16idsys p {{
            font-weight: 700 !important;
            color: var(--color-text) !important;
            font-family: var(--font-family);
        }}
        
        /* --- Esconde a barra lateral padrão do Streamlit --- */
        [data-testid="stSidebar"] {{ display: none; }}

        /* --- Header Superior e Abas --- */
        .excel-header {{
            background-color: var(--color-header-bg);
            padding: 0.5rem 2rem;
            margin: -1rem -2rem 0 -2rem; /* Puxa para as bordas */
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
            position: relative;
        }}

        /* --- Estilo dos Cartões de Conteúdo --- */
        .card {{
            background: var(--color-card-bg);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            border: 1px solid var(--color-border);
            height: 100%;
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
        }}
        .kpi-block-value {{
            font-size: 2rem;
            font-weight: 700;
        }}
    </style>
""", unsafe_allow_html=True)

# --- PALETA DE CORES (PARA LÓGICA) ---
KPI_YELLOW = "#FFC000"
KPI_GREEN = "#70AD47"
KPI_BLUE = "#4472C4"
KPI_RED = "#C00000"
KPI_TEAL = "#2F75B5"
CARD_COLOR = "#FFFFFF"

# ---------------------------
# NAVEGAÇÃO E CABEÇALHO
# ---------------------------
def render_header_and_tabs():
    active_page = st.session_state.get('active_page', 'Dashboards')
    dashboard_class = "active" if active_page == "Dashboards" else ""
    relatorios_class = "active" if active_page == "Relatórios" else ""
    config_class = "active" if active_page == "Configurações" else ""

    st.markdown(f"""
        <header class="excel-header">
            <nav class="tabs-nav">
                <a href="?page=Dashboards" target="_self" class="{dashboard_class}">DASHBOARDS</a>
                <a href="?page=Relatórios" target="_self" class="{relatorios_class}">ANÁLISE DE ATIVOS</a>
                <a href="?page=Configurações" target="_self" class="{config_class}">GESTÃO DE INVESTIMENTOS</a>
            </nav>
        </header>
    """, unsafe_allow_html=True)

query_params = st.query_params
if 'page' in query_params:
    st.session_state.active_page = query_params.get('page')
else:
    if 'active_page' not in st.session_state:
        st.session_state.active_page = "Dashboards"

render_header_and_tabs()

# ---------------------------
# Funções Utilitárias e de Lógica (sem alterações)
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

def get_default_config():
    return {
        'rented': { 'modules_init': 1, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_per_new_module': 750.0 },
        'owned': { 'modules_init': 0, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'monthly_land_plot_parcel': 0.0, 'land_total_value': 0.0, 'land_down_payment_pct': 20.0, 'land_installments': 120 },
        'global': { 'years': 15, 'max_withdraw_value': 50000.0, 'aportes': [], 'retiradas': [], 'fundos': [] }
    }

# --- FUNÇÃO HELPER PARA KPIs COM NOVO ESTILO ---
def render_kpi_block(title, value, color):
    st.markdown(f"""
        <div class="kpi-block" style="background-color: {color};">
            <div class="kpi-block-title">{title.upper()}</div>
            <div class="kpi-block-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)


# --- INICIALIZAÇÃO DO ESTADO ---
if 'config' not in st.session_state: st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state: st.session_state.comparison_df = pd.DataFrame()
if 'column_visibility' not in st.session_state: st.session_state.column_visibility = {}


# ---------------------------
# PÁGINA DE CONFIGURAÇÕES
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.header("Gestão de Investimentos")
    # ... (código completo da página de configurações) ...

# ---------------------------
# PÁGINA DE DASHBOARDS
# ---------------------------
if st.session_state.active_page == 'Dashboards':
    kpi_col, chart_col = st.columns([1, 3])
    
    with kpi_col:
        # Lógica para obter os dados para os KPIs
        # Exemplo com valores estáticos
        render_kpi_block("Valor Investido", fmt_brl(92250000), KPI_YELLOW)
        st.markdown("<br>", unsafe_allow_html=True)
        render_kpi_block("Valor Retirado", fmt_brl(102630000), KPI_GREEN)
        st.markdown("<br>", unsafe_allow_html=True)
        render_kpi_block("Rendimento Bruto", fmt_brl(10380000), KPI_BLUE)
        st.markdown("<br>", unsafe_allow_html=True)
        render_kpi_block("Taxas", fmt_brl(1770500), KPI_RED)
        st.markdown("<br>", unsafe_allow_html=True)
        render_kpi_block("Rendimento Líquido", fmt_brl(8609500), KPI_TEAL)

    with chart_col:
        with st.container(border=True):
            st.subheader("Visualizações do Portfólio")
            c1, c2, c3 = st.columns(3)
            # ... (código para os 3 gráficos de pizza) ...

# ---------------------------
# PÁGINA DE RELATÓRIOS
# ---------------------------
if st.session_state.active_page == 'Relatórios':
    st.header("Análise Detalhada de Ativos")
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty: df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty: df_to_show = st.session_state.simulation_df

    if df_to_show.empty:
        st.info("Vá para a página 'Dashboards' para iniciar uma simulação.")
    else:
        df = df_to_show
        with st.container(border=True):
            st.subheader("Tabela Completa da Simulação")
            df_display_base = df
            if 'Estratégia' in df.columns:
                selected_strategy = st.selectbox("Selecione a estratégia para filtrar a tabela:", df['Estratégia'].unique())
                df_display_base = df[df['Estratégia'] == selected_strategy]
            
            all_columns = df_display_base.columns.tolist()
            if 'Estratégia' in all_columns: all_columns.remove('Estratégia')
            default_cols = ['Mês', 'Ano', 'Módulos Ativos', 'Receita', 'Gastos', 'Caixa (Final Mês)', 'Patrimônio Líquido']
            
            if set(st.session_state.column_visibility.keys()) != set(all_columns):
                st.session_state.column_visibility = {col: (col in default_cols) for col in all_columns}
            
            with st.expander("Exibir/Ocultar Colunas da Tabela"):
                toggle_cols = st.columns(4)
                for i, col_name in enumerate(all_columns):
                    with toggle_cols[i % 4]:
                        st.session_state.column_visibility[col_name] = st.toggle(col_name, value=st.session_state.column_visibility.get(col_name, False))
            
            cols_to_show = [col for col, is_visible in st.session_state.column_visibility.items() if is_visible]
            st.dataframe( df_display_base[cols_to_show] if cols_to_show else df_display_base, use_container_width=True, hide_index=True)
            st.download_button( "📥 Baixar Relatório Completo (Excel)", data=df_to_excel_bytes(df_display_base), file_name="relatorio_simulacao.xlsx")
