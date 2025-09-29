# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# ---------------------------
# CONFIGURAÇÃO E TEMA/CORES
# ---------------------------
st.set_page_config(page_title="Simulador Modular", layout="wide", initial_sidebar_state="expanded")

# Paleta consolidada (baseada nos anexos)
BG_COLOR = "#F7F7F5"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#212529"
MUTED_TEXT_COLOR = "#5a5a5a"
TABLE_BORDER_COLOR = "#E0E0E0"
SIDEBAR_BG = "#086788"
SIDEBAR_TEXT_COLOR = "#FFFFFF"
GRADIENT_START = "#07A0C3"
GRADIENT_END = "#F0C808"
CUSTOM_GRADIENT = f"linear-gradient(90deg, {GRADIENT_START}, {GRADIENT_END})"

CHART_CAIXA_COLOR = "#F0C808"
CHART_FUNDO_COLOR = "#07A0C3"
CHART_RETIRADAS_COLOR = "#DD1C1A"
CHART_MODULOS_PROPRIOS_COLOR = SIDEBAR_BG
CHART_MODULOS_ALUGADOS_COLOR = "#6c757d"
KPI_INVESTIMENTO_COLOR = "#6c757d"
KPI_PATRIMONIO_COLOR = "#212529"

# Cores adicionais usadas em gráficos comparativos
KPI_YELLOW = "#FFC000"
KPI_GREEN = "#70AD47"
KPI_BLUE = "#4472C4"
KPI_TEAL = "#2F75B5"
CHART_ORANGE = "#ED7D31"
CHART_GRAY = "#A5A5A5"

# ---------------------------
# CSS - Estilos
# ---------------------------
st.markdown(f"""
    <style>
        .main .block-container {{ padding: 2rem; }}
        [data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG}; }}
        [data-testid="stSidebar"] .stMarkdown h1 {{ padding-top: 1rem; color: {SIDEBAR_TEXT_COLOR}; }}
        [data-testid="stSidebar"] .stMarkdown p {{ color: rgba(255, 255, 255, 0.8); }}
        .stRadio > div {{ gap: 0.5rem; }}
        .stRadio > label > div {{
            font-size: 1.1rem !important; font-weight: 600 !important; padding: 0.5rem 0.75rem !important;
            border-radius: 0.5rem !important; margin-bottom: 0.5rem; color: rgba(255, 255, 255, 0.8) !important; transition: all 0.2s;
        }}
        .stRadio > div[role="radiogroup"] > label:has(div[data-baseweb="radio"][class*="e1y5xkzn3"]) > div {{
            background-color: rgba(255, 255, 255, 0.1) !important; color: {SIDEBAR_TEXT_COLOR} !important; border-left: 3px solid {GRADIENT_END};
        }}
        .stApp {{ background-color: {BG_COLOR}; }}
        .header-title, h1, h2, h3, h4, h5, h6, label, .st-emotion-cache-16idsys p {{ color: {TEXT_COLOR} !important; }}
        .subhead, .st-emotion-cache-1ghhuty p {{ color: {MUTED_TEXT_COLOR} !important; }}
        [data-testid="stMetricLabel"] p {{ color: {MUTED_TEXT_COLOR} !important; }}
        [data-testid="stMetricValue"] div {{ color: {TEXT_COLOR} !important; }}
        .card {{
            background: {CARD_COLOR}; border-radius: 12px; padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid {TABLE_BORDER_COLOR}; height: 100%;
        }}
        .kpi-value {{ font-size: 1.8rem; font-weight: 700; }}
        .kpi-colored {{
            padding: 1.5rem; border-radius: 12px; color: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.06); height: 100%;
        }}
        .kpi-gradient {{
            padding: 1.5rem; border-radius: 12px; background: {CUSTOM_GRADIENT}; color: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.06); height: 100%;
        }}
        .kpi-colored .small-muted, .kpi-gradient .small-muted {{ color: rgba(255,255,255,0.8); font-size: 0.9rem; }}
        .stDataFrame, .stTable {{ border: none; box-shadow: none; padding: 0; }}
        table {{ width: 100%; }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Funções Utilitárias e Lógica
# ---------------------------
def fmt_brl(v):
    # Formatação BRL (padrão do segundo anexo)
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Simulacao_Mensal')
    return output.getvalue()

def get_default_config():
    # Config consolidada baseada no anexo com parcelas de terreno mensal por novo módulo
    return {
        'rented': {
            'modules_init': 1,
            'cost_per_module': 75000.0,
            'cost_correction_rate': 5.0,
            'revenue_per_module': 4500.0,
            'maintenance_per_module': 200.0,
            'rent_value': 750.0,
            'rent_per_new_module': 750.0
        },
        'owned': {
            'modules_init': 0,
            'cost_per_module': 75000.0,
            'cost_correction_rate': 5.0,
            'revenue_per_module': 4500.0,
            'maintenance_per_module': 200.0,
            'monthly_land_plot_parcel': 0.0,  # parcela mensal de novo terreno
            'land_total_value': 0.0,          # terreno inicial (opcional)
            'land_down_payment_pct': 20.0,
            'land_installments': 120
        },
        'global': {
            'years': 15,
            'max_withdraw_value': 50000.0,
            'aportes': [],     # [{mes:int, valor:float}]
            'retiradas': [],   # [{mes:int, percentual:float}]
            'fundos': []       # [{mes:int, percentual:float}]
        }
    }

def simulate(config, reinvestment_strategy):
    """
    Simulador consolidado com:
    - aluguel base e aluguel por novo módulo alugado
    - parcela mensal por novo terreno quando comprar módulos próprios
    - eventos: aportes, retiradas (% do lucro), fundos (% do lucro) com teto máx. de retirada
    """
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

    # Terreno inicial (opcional)
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

        # Aporte do mês
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes

        # Lucro operacional (antes de retiradas/fundos)
        lucro_operacional_mes = receita - manut - aluguel_mensal_corrente - parcelas_terrenos_novos_mensal_corrente

        # Parcelas do terreno inicial, se houver
        parcela_terreno_inicial_mes = 0.0
        if cfg_owned['land_total_value'] > 0 and m <= cfg_owned['land_installments']:
            parcela_terreno_inicial_mes = valor_parcela_terreno_inicial
            investimento_total += valor_parcela_terreno_inicial

        # Movimento de caixa do mês
        if m == 1:
            caixa -= valor_entrada_terreno
        caixa += lucro_operacional_mes
        caixa -= parcela_terreno_inicial_mes

        # Distribuição: retiradas e fundos (% do lucro) com teto de retirada
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

        # Reinvestimento anual (a cada 12 meses)
        if m % 12 == 0:
            custo_expansao = 0.0
            if reinvestment_strategy == 'buy':
                custo_expansao = custo_modulo_atual_owned
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
            elif reinvestment_strategy == 'alternate':
                custo_expansao = custo_modulo_atual_owned if (compra_intercalada_counter % 2 == 0) else custo_modulo_atual_rented

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

            # Correção anual do custo
            custo_modulo_atual_owned *= (1 + cfg_owned['cost_correction_rate'] / 100.0)
            custo_modulo_atual_rented *= (1 + cfg_rented['cost_correction_rate'] / 100.0)

        patrimonio_liquido = ((modules_owned + modules_rented) * custo_modulo_atual_owned) + caixa + fundo_ac + cfg_owned['land_total_value']

        rows.append({
            "Mês": m,
            "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules_owned + modules_rented,
            "Módulos Alugados": modules_rented,
            "Módulos Próprios": modules_owned,
            "Receita": receita,
            "Manutenção": manut,
            "Aluguel": aluguel_mensal_corrente,
            "Parcelas Terrenos (Novos)": parcelas_terrenos_novos_mensal_corrente,
            "Gastos": manut + aluguel_mensal_corrente + parcelas_terrenos_novos_mensal_corrente,
            "Aporte": aporte_mes,
            "Fundo (Mês)": fundo_mes_total,
            "Retirada (Mês)": retirada_mes_efetiva,
            "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac,
            "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Patrimônio Líquido": patrimonio_liquido
        })

    return pd.DataFrame(rows)

# ---------------------------
# ESTADO INICIAL
# ---------------------------
if 'config' not in st.session_state:
    st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state:
    st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = pd.DataFrame()
if 'active_page' not in st.session_state:
    st.session_state.active_page = 'Configurações'
if 'column_visibility' not in st.session_state:
    st.session_state.column_visibility = {}
# Paginador da tabela de relatórios
if 'rel_page' not in st.session_state:
    st.session_state.rel_page = 0

# ---------------------------
# SIDEBAR - NAVEGAÇÃO
# ---------------------------
with st.sidebar:
    st.markdown("<h1>Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p>Projeção com reinvestimento</p>", unsafe_allow_html=True)
    st.session_state.active_page = st.radio(
        "Menu Principal",
        ["Configurações", "Dashboard", "Relatórios e Dados"],
        key="navigation_radio",
        label_visibility="collapsed"
    )

# ---------------------------
# PÁGINA: CONFIGURAÇÕES
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.title("Configurações de Investimento")
    st.markdown("<p class='subhead'>Ajuste os parâmetros da simulação financeira e adicione eventos.</p>", unsafe_allow_html=True)

    if st.button("🔄 Resetar Configurações"):
        st.session_state.config = get_default_config()
        st.rerun()

    # Terreno Alugado
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

    # Terreno Comprado
    st.markdown('<div class="card">', unsafe_allow_html=True)
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
    c1p, c2p = st.columns(2)
    cfg_o['modules_init'] = c1p.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
    cfg_o['cost_per_module'] = c1p.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
    cfg_o['revenue_per_module'] = c1p.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
    cfg_o['maintenance_per_module'] = c2p.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
    cfg_o['cost_correction_rate'] = c2p.number_input("Correção anual do custo (%)", 0.0, value=cfg_o['cost_correction_rate'], format="%.1f", key="own_corr_rate")
    cfg_o['monthly_land_plot_parcel'] = c2p.number_input(
        "Parcela mensal por novo terreno (R$)",
        0.0,
        value=cfg_o.get('monthly_land_plot_parcel', 0.0),
        format="%.2f",
        key="own_land_parcel",
        disabled=(cfg_o['land_total_value'] > 0)
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Parâmetros Globais e Eventos
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Parâmetros Globais e Eventos Financeiros")
    cfg_g = st.session_state.config['global']
    cg1, cg2 = st.columns(2)
    cfg_g['years'] = cg1.number_input("Horizonte de investimento (anos)", 1, 50, cfg_g['years'])
    cfg_g['max_withdraw_value'] = cg2.number_input(
        "Valor máximo de retirada mensal (R$)",
        0.0, value=cfg_g['max_withdraw_value'], format="%.2f",
        help="Teto para retiradas baseadas em % do lucro."
    )

    st.markdown("---")
    st.markdown("<h6>Aportes (investimentos pontuais)</h6>", unsafe_allow_html=True)
    for i, aporte in enumerate(cfg_g['aportes']):
        cols = st.columns([2, 3, 1])
        aporte['mes'] = cols[0].number_input("Mês", min_value=1, value=aporte['mes'], key=f"aporte_mes_{i}")
        aporte['valor'] = cols[1].number_input("Valor (R$)", min_value=0.0, value=aporte['valor'], format="%.2f", key=f"aporte_valor_{i}")
        if cols[2].button("Remover", key=f"aporte_remover_{i}"):
            cfg_g['aportes'].pop(i); st.rerun()
    if st.button("Adicionar Aporte"):
        cfg_g['aportes'].append({"mes": 1, "valor": 0.0}); st.rerun()

    st.markdown("---")
    st.markdown("<h6>Retiradas (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, retirada in enumerate(cfg_g['retiradas']):
        cols = st.columns([2, 3, 1])
        retirada['mes'] = cols[0].number_input("Mês início", min_value=1, value=retirada['mes'], key=f"retirada_mes_{i}")
        retirada['percentual'] = cols[1].number_input("% do lucro", min_value=0.0, max_value=100.0, value=retirada['percentual'], format="%.1f", key=f"retirada_pct_{i}")
        if cols[2].button("Remover", key=f"retirada_remover_{i}"):
            cfg_g['retiradas'].pop(i); st.rerun()
    if st.button("Adicionar Retirada"):
        cfg_g['retiradas'].append({"mes": 1, "percentual": 30.0}); st.rerun()

    st.markdown("---")
    st.markdown("<h6>Fundos de Reserva (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, fundo in enumerate(cfg_g['fundos']):
        cols = st.columns([2, 3, 1])
        fundo['mes'] = cols[0].number_input("Mês início", min_value=1, value=fundo['mes'], key=f"fundo_mes_{i}")
        fundo['percentual'] = cols[1].number_input("% do lucro", min_value=0.0, max_value=100.0, value=fundo['percentual'], format="%.1f", key=f"fundo_pct_{i}")
        if cols[2].button("Remover", key=f"fundo_remover_{i}"):
            cfg_g['fundos'].pop(i); st.rerun()
    if st.button("Adicionar Fundo"):
        cfg_g['fundos'].append({"mes": 1, "percentual": 10.0}); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# PÁGINA: DASHBOARD
# ---------------------------
if st.session_state.active_page == 'Dashboard':
    st.title("Dashboard Estratégico")
    st.markdown("<p class='subhead'>Escolha uma estratégia de reinvestimento para simular ou compare todas.</p>", unsafe_allow_html=True)

    with st.container(border=True):
        strat_cols = st.columns(3)
        if strat_cols[0].button("📈 Simular: Comprar", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'buy')
                st.session_state.comparison_df = pd.DataFrame()
        if strat_cols[1].button("📈 Simular: Alugar", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'rent')
                st.session_state.comparison_df = pd.DataFrame()
        if strat_cols[2].button("📈 Simular: Intercalar", use_container_width=True, type="primary"):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'alternate')
                st.session_state.comparison_df = pd.DataFrame()

        st.markdown("---")
        if st.button("📊 Comparar Todas as Estratégias", use_container_width=True):
            with st.spinner("Calculando as três simulações..."):
                df_buy = simulate(st.session_state.config, 'buy'); df_buy['Estratégia'] = 'Comprar'
                df_rent = simulate(st.session_state.config, 'rent'); df_rent['Estratégia'] = 'Alugar'
                df_alt  = simulate(st.session_state.config, 'alternate'); df_alt['Estratégia'] = 'Intercalar'
                st.session_state.comparison_df = pd.concat([df_buy, df_rent, df_alt])
                st.session_state.simulation_df = pd.DataFrame()

    st.markdown("---")

    # Bloco de comparação
    if not st.session_state.comparison_df.empty:
        st.header("Análise Comparativa de Estratégias")
        df_comp = st.session_state.comparison_df

        final_buy = df_comp[df_comp['Estratégia'] == 'Comprar'].iloc[-1]
        final_rent = df_comp[df_comp['Estratégia'] == 'Alugar'].iloc[-1]
        final_alt = df_comp[df_comp['Estratégia'] == 'Intercalar'].iloc[-1]

        kpi_cols = st.columns(4)
        kpi_cols[0].markdown(f"<div class='kpi-colored' style='background-color:{KPI_BLUE};'><div class='small-muted'>Patrimônio (Comprar)</div><div class='kpi-value'>{fmt_brl(final_buy['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)
        kpi_cols[1].markdown(f"<div class='kpi-colored' style='background-color:{KPI_TEAL};'><div class='small-muted'>Patrimônio (Alugar)</div><div class='kpi-value'>{fmt_brl(final_rent['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)
        kpi_cols[2].markdown(f"<div class='kpi-colored' style='background-color:{CHART_ORANGE};'><div class='small-muted'>Patrimônio (Intercalar)</div><div class='kpi-value'>{fmt_brl(final_alt['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)
        melhor = pd.Series({'Comprar': final_buy['Patrimônio Líquido'], 'Alugar': final_rent['Patrimônio Líquido'], 'Intercalar': final_alt['Patrimônio Líquido']}).idxmax()
        kpi_cols[3].markdown(f"<div class='kpi-colored' style='background-color:{KPI_GREEN};'><div class='small-muted'>Melhor Estratégia</div><div class='kpi-value'>{melhor}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Métricas ao Longo do Tempo")
            metric_options = {
                "Patrimônio Líquido": "Patrimônio Líquido",
                "Módulos Ativos": "Módulos Ativos",
                "Retiradas Acumuladas": "Retiradas Acumuladas"
            }
            selected_metric = st.selectbox("Selecione uma métrica para comparar:", options=list(metric_options.keys()))
            fig_comp = px.line(
                df_comp, x="Mês", y=metric_options[selected_metric], color='Estratégia',
                color_discrete_map={'Comprar': KPI_BLUE, 'Alugar': KPI_TEAL, 'Intercalar': CHART_ORANGE}
            )
            fig_comp.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                   plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR)
            st.plotly_chart(fig_comp, use_container_width=True)

    # Resultado de uma simulação única
    elif not st.session_state.simulation_df.empty:
        st.header("Resultados da Simulação")
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        cfg = st.session_state.config

        inv_inicial_modulos = (cfg['rented']['modules_init'] * cfg['rented']['cost_per_module']) + (cfg['owned']['modules_init'] * cfg['owned']['cost_per_module'])
        entrada_terreno = 0.0
        if cfg['owned']['land_total_value'] > 0:
            entrada_terreno = cfg['owned']['land_total_value'] * (cfg['owned']['land_down_payment_pct'] / 100.0)
        investimento_inicial_total = inv_inicial_modulos + entrada_terreno

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("KPIs Finais")
        with st.container(border=True):
            kpi_cols = st.columns(4)
            kpi_cols[0].markdown(f"<div class='kpi-colored' style='background-color:{KPI_INVESTIMENTO_COLOR};'><div class='small-muted'>Investimento Inicial</div><div class='kpi-value'>{fmt_brl(investimento_inicial_total)}</div></div>", unsafe_allow_html=True)
            kpi_cols[1].markdown(f"<div class='kpi-colored' style='background-color:{KPI_PATRIMONIO_COLOR};'><div class='small-muted'>Patrimônio Líquido</div><div class='kpi-value'>{fmt_brl(final['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)
            kpi_cols[2].markdown(f"<div class='kpi-colored' style='background-color:{CHART_RETIRADAS_COLOR};'><div class='small-muted'>Retiradas Acumuladas</div><div class='kpi-value'>{fmt_brl(final['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
            kpi_cols[3].markdown(f"<div class='kpi-colored' style='background-color:{CHART_FUNDO_COLOR};'><div class='small-muted'>Fundo Acumulado</div><div class='kpi-value'>{fmt_brl(final['Fundo Acumulado'])}</div></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            kpi_cols2 = st.columns(4)
            kpi_cols2[0].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Módulos Finais</div><div class='kpi-value'>{int(final['Módulos Ativos'])}</div></div>", unsafe_allow_html=True)
            kpi_cols2[1].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Caixa Final</div><div class='kpi-value'>{fmt_brl(final['Caixa (Final Mês)'])}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Análise Gráfica Detalhada")
        with st.container(border=True):
            st.markdown("###### Evolução do Patrimônio vs. Investimento")
            periodo_pat = st.slider("Período (meses)", 1, len(df), (1, len(df)), key="pat_slider")
            df_pat = df.loc[periodo_pat[0]-1:periodo_pat[1]-1]
            fig_pat = go.Figure()
            fig_pat.add_trace(go.Scatter(x=df_pat["Mês"], y=df_pat["Patrimônio Líquido"], name="Patrimônio Líquido", line=dict(color=KPI_PATRIMONIO_COLOR, width=2.5)))
            fig_pat.add_trace(go.Scatter(x=df_pat["Mês"], y=df_pat["Investimento Total Acumulado"], name="Investimento Total", line=dict(color=KPI_INVESTIMENTO_COLOR, width=1.5)))
            fig_pat.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                  plot_bgcolor='white', paper_bgcolor='white')
            st.plotly_chart(fig_pat, use_container_width=True)

        chart_cols = st.columns(2)
        with chart_cols[0]:
            with st.container(border=True):
                st.markdown("###### Composição dos Módulos")
                periodo_comp = st.slider("Período (meses)", 1, len(df), (1, len(df)), key="comp_slider")
                df_comp = df.loc[periodo_comp[0]-1:periodo_comp[1]-1]
                fig_comp_area = go.Figure()
                fig_comp_area.add_trace(go.Scatter(x=df_comp['Mês'], y=df_comp['Módulos Próprios'], name='Próprios', stackgroup='one', line=dict(color=CHART_MODULOS_PROPRIOS_COLOR)))
                fig_comp_area.add_trace(go.Scatter(x=df_comp['Mês'], y=df_comp['Módulos Alugados'], name='Alugados', stackgroup='one', line=dict(color=CHART_MODULOS_ALUGADOS_COLOR)))
                fig_comp_area.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                            plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig_comp_area, use_container_width=True)
        with chart_cols[1]:
            with st.container(border=True):
                st.markdown("###### Distribuição Final dos Recursos")
                dist_data = {
                    'Valores': [final['Retiradas Acumuladas'], final['Fundo Acumulado'], final['Caixa (Final Mês)']],
                    'Categorias': ['Retiradas', 'Fundo Total', 'Caixa Final']
                }
                fig_pie = px.pie(dist_data, values='Valores', names='Categorias',
                                 color_discrete_sequence=[CHART_RETIRADAS_COLOR, CHART_FUNDO_COLOR, CHART_CAIXA_COLOR])
                fig_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10),
                                      legend=dict(orientation="h", yanchor="bottom", y=-0.1), paper_bgcolor='white')
                st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("👆 Selecione uma estratégia de simulação para visualizar os resultados.")

# ---------------------------
# PÁGINA: RELATÓRIOS E DADOS
# ---------------------------
if st.session_state.active_page == 'Relatórios e Dados':
    st.title("Relatórios e Dados")
    st.markdown("<p class='subhead'>Explore os dados detalhados da simulação mês a mês.</p>", unsafe_allow_html=True)

    # Seleção da base a exibir (comparação ou simulação única)
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty:
        df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty:
        df_to_show = st.session_state.simulation_df

    if df_to_show.empty:
        st.info("👈 Vá para o 'Dashboard' para iniciar uma simulação.")
    else:
        df = df_to_show

        main_cols = st.columns([6, 4])

        # ANÁLISE POR PONTO NO TEMPO
        with main_cols[0]:
            with st.container(border=True):
                st.subheader("Análise por Ponto no Tempo")

                df_analysis = df
                selected_strategy = None
                if 'Estratégia' in df.columns:
                    selected_strategy = st.selectbox("Estratégia para análise:", df['Estratégia'].unique(), key="planilha_strat_select")
                    df_analysis = df[df['Estratégia'] == selected_strategy].copy()

                c1, c2 = st.columns(2)
                anos_disponiveis = df_analysis['Ano'].unique()
                selected_year = c1.selectbox("Selecione o ano", options=anos_disponiveis, key="planilha_year_select")

                months_in_year = df_analysis[df_analysis['Ano'] == selected_year]['Mês'].apply(lambda x: ((x - 1) % 12) + 1).unique()
                selected_month_label = c2.selectbox("Selecione o mês", options=sorted(months_in_year), key="planilha_month_select")

                selected_month_abs_candidate = df_analysis[(df_analysis['Ano'] == selected_year) & (((df_analysis['Mês'] - 1) % 12) + 1 == selected_month_label)]
                if not selected_month_abs_candidate.empty:
                    data_point = selected_month_abs_candidate.iloc[0]
                else:
                    st.warning("Dados para o mês/ano selecionado não encontrados.")
                    data_point = pd.Series({})

                if not data_point.empty:
                    st.markdown("---")
                    res_cols = st.columns(2)
                    res_cols[0].metric("Total de Módulos", f"{int(data_point['Módulos Ativos'])} ({int(data_point['Módulos Alugados']) if 'Módulos Alugados' in data_point else 0} Alug. / {int(data_point['Módulos Próprios']) if 'Módulos Próprios' in data_point else 0} Próp.)")
                    res_cols[0].metric("Caixa no Mês", fmt_brl(data_point['Caixa (Final Mês)']))
                    res_cols[1].metric("Patrimônio Líquido", fmt_brl(data_point['Patrimônio Líquido']))
                    res_cols[1].metric("Investimento Total", fmt_brl(data_point['Investimento Total Acumulado']))

        # RESUMO GRÁFICO DO MÊS
        with main_cols[1]:
            with st.container(border=True):
                st.subheader("Resumo Gráfico do Mês")
                if 'data_point' in locals() and not data_point.empty:
                    chart_data = pd.DataFrame({
                        "Categoria": ["Receita", "Gastos", "Retirada", "Fundo"],
                        "Valor": [
                            data_point.get('Receita', 0.0),
                            data_point.get('Gastos', 0.0),
                            data_point.get('Retirada (Mês)', 0.0),
                            data_point.get('Fundo (Mês)', 0.0)
                        ]
                    })
                    fig_monthly = px.bar(
                        chart_data, x="Categoria", y="Valor", text_auto='.2s', color="Categoria",
                        color_discrete_map={"Receita": KPI_GREEN, "Gastos": CHART_ORANGE, "Retirada": CHART_RETIRADAS_COLOR, "Fundo": KPI_TEAL}
                    )
                    fig_monthly.update_layout(showlegend=False, height=450, plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR)
                    st.plotly_chart(fig_monthly, use_container_width=True)
                else:
                    st.info("Selecione um mês válido para ver o resumo.")

        st.markdown("<br>", unsafe_allow_html=True)

        # TABELA COMPLETA COM TOGGLES E PAGINAÇÃO
        with st.container(border=True):
            st.subheader("Tabela Completa da Simulação")

            df_display_base = df
            if 'Estratégia' in df.columns and selected_strategy is not None:
                st.markdown(f"Mostrando dados da estratégia: <b>{selected_strategy}</b>", unsafe_allow_html=True)
                df_display_base = df[df['Estratégia'] == selected_strategy].copy()

            all_columns = df_display_base.columns.tolist()
            # Visibilidade inicial padrão
            default_cols = ['Mês', 'Ano', 'Módulos Ativos', 'Receita', 'Gastos', 'Caixa (Final Mês)', 'Patrimônio Líquido']
            current_set = set(st.session_state.column_visibility.keys())
            if (not st.session_state.column_visibility) or (set(all_columns) != current_set):
                st.session_state.column_visibility = {col: (col in default_cols) for col in all_columns}

            with st.expander("Exibir/Ocultar Colunas da Tabela"):
                toggle_cols = st.columns(4)
                for i, col_name in enumerate(all_columns):
                    with toggle_cols[i % 4]:
                        st.session_state.column_visibility[col_name] = st.toggle(
                            col_name, value=st.session_state.column_visibility.get(col_name, False), key=f"toggle_{col_name}"
                        )

            cols_to_show = [col for col, is_visible in st.session_state.column_visibility.items() if is_visible]
            if not cols_to_show:
                st.warning("Selecione ao menos uma coluna para exibir os dados.")
            else:
                page_size = 12
                total_pages = (len(df_display_base) - 1) // page_size + 1 if len(df_display_base) > 0 else 1
                if st.session_state.rel_page >= total_pages:
                    st.session_state.rel_page = 0
                start_idx = st.session_state.rel_page * page_size
                end_idx = start_idx + page_size
                df_display = df_display_base.iloc[start_idx:end_idx].copy()

                # Formatação de colunas monetárias
                format_cols = ["Receita", "Manutenção", "Aluguel", "Parcelas Terrenos (Novos)", "Aporte", "Fundo (Mês)", "Retirada (Mês)",
                               "Caixa (Final Mês)", "Investimento Total Acumulado", "Fundo Acumulado", "Retiradas Acumuladas",
                               "Patrimônio Líquido", "Gastos"]
                for col in format_cols:
                    if col in df_display.columns:
                        df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")

                st.dataframe(df_display[cols_to_show], use_container_width=True, hide_index=True)

                page_cols = st.columns([1, 1, 8])
                if page_cols[0].button("Anterior", disabled=(st.session_state.rel_page == 0), key="prev_page_btn"):
                    st.session_state.rel_page -= 1; st.rerun()
                if page_cols[1].button("Próxima", disabled=(st.session_state.rel_page >= total_pages - 1), key="next_page_btn"):
                    st.session_state.rel_page += 1; st.rerun()
                page_cols[2].markdown(f"<div style='padding-top:10px;'>Página {st.session_state.rel_page + 1} de {total_pages}</div>", unsafe_allow_html=True)

                # Download
                excel_bytes = df_to_excel_bytes(df_display_base)
                file_years = st.session_state.config['global']['years']
                st.download_button(
                    "📥 Baixar Relatório Completo (Excel)",
                    data=excel_bytes,
                    file_name=f"relatorio_simulacao_{file_years}_anos.xlsx",
                    key="download_excel_btn"
                )
