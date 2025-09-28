# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# --- Cores personalizadas e Configurações Iniciais ---
BG_COLOR = "#F7F7F5"
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

# ---------------------------
# CSS - Estilos da Página
# ---------------------------
st.set_page_config(page_title="Simulador Modular", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"""
    <style>
        .main .block-container {{ padding: 2rem; }}
        [data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG}; }}
        [data-testid="stSidebar"] .stMarkdown h1 {{ padding-top: 1rem; color: {SIDEBAR_TEXT_COLOR}; }}
        [data-testid="stSidebar"] .stMarkdown p {{ color: rgba(255, 255, 255, 0.8); }}
        .stRadio > div {{ gap: 0.5rem; }}
        .stRadio > label > div {{ font-size: 1.1rem !important; font-weight: 600 !important; padding: 0.5rem 0.75rem !important; border-radius: 0.5rem !important; margin-bottom: 0.5rem; color: rgba(255, 255, 255, 0.8) !important; transition: all 0.2s; }}
        .stRadio > div[role="radiogroup"] > label:has(div[data-baseweb="radio"][class*="e1y5xkzn3"]) > div {{ background-color: rgba(255, 255, 255, 0.1) !important; color: {SIDEBAR_TEXT_COLOR} !important; border-left: 3px solid {GRADIENT_END}; }}
        .stApp {{ background-color: {BG_COLOR}; }}
        .header-title, h1, h2, h3, h4, h5, h6, label, .st-emotion-cache-16idsys p {{ color: {TEXT_COLOR} !important; }}
        .subhead, .st-emotion-cache-1ghhuty p {{ color: {MUTED_TEXT_COLOR} !important; }}
        [data-testid="stMetricLabel"] p {{ color: {MUTED_TEXT_COLOR} !important; }}
        [data-testid="stMetricValue"] div {{ color: {TEXT_COLOR} !important; }}
        .card {{ background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid {TABLE_BORDER_COLOR}; height: 100%; }}
        .kpi-value {{ font-size: 1.8rem; font-weight: 700; }}
        .kpi-colored {{ padding: 1.5rem; border-radius: 12px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.06); height: 100%; }}
        .kpi-gradient {{ padding: 1.5rem; border-radius: 12px; background: {CUSTOM_GRADIENT}; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.06); height: 100%; }}
        .kpi-colored .small-muted, .kpi-gradient .small-muted {{ color: rgba(255,255,255,0.8); font-size: 0.9rem; }}
        .stDataFrame, .stTable {{ border: none; box-shadow: none; padding: 0; }}
        table {{ width: 100%; }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Funções Utilitárias e de Lógica
# ---------------------------
def fmt_brl(v):
    return f"R$ {v:,.2f}"

def simulate(config, reinvestment_strategy):
    # Desempacota configurações
    cfg_rented = config['rented']
    cfg_owned = config['owned']
    cfg_global = config['global']

    months = cfg_global['years'] * 12
    rows = []
    
    # Inicia contadores de módulos
    modules_rented = cfg_rented['modules_init']
    modules_owned = cfg_owned['modules_init']
    
    caixa = 0.0
    investimento_total = (modules_rented * cfg_rented['cost_per_module']) + (modules_owned * cfg_owned['cost_per_module'])
    fundo_ac = 0.0
    retiradas_ac = 0.0
    
    custo_modulo_atual_rented = cfg_rented['cost_per_module']
    custo_modulo_atual_owned = cfg_owned['cost_per_module']

    aportes_map = {a["mes"]: a.get("valor", 0.0) for a in cfg_global['aportes']}

    # Lógica de Terreno Comprado
    valor_entrada_terreno = 0.0
    valor_parcela_terreno = 0.0
    if cfg_owned['land_total_value'] > 0:
        valor_entrada_terreno = cfg_owned['land_total_value'] * (cfg_owned['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_owned['land_total_value'] - valor_entrada_terreno
        valor_parcela_terreno = valor_financiado / cfg_owned['land_installments'] if cfg_owned['land_installments'] > 0 else 0
        investimento_total += valor_entrada_terreno

    aluguel_mensal_corrente = cfg_rented['rent_value']
    compra_intercalada_counter = 0

    for m in range(1, months + 1):
        modules_total = modules_rented + modules_owned
        receita = (modules_rented * cfg_rented['revenue_per_module']) + (modules_owned * cfg_owned['revenue_per_module'])
        manut = (modules_rented * cfg_rented['maintenance_per_module']) + (modules_owned * cfg_owned['maintenance_per_module'])
        
        novos_modulos_comprados = 0
        aporte_mes = aportes_map.get(m, 0.0)
        caixa += aporte_mes
        investimento_total += aporte_mes
        
        lucro_operacional_mes = receita - manut - aluguel_mensal_corrente
        
        parcela_terreno_mes = 0.0
        if cfg_owned['land_total_value'] > 0 and m <= cfg_owned['land_installments']:
            parcela_terreno_mes = valor_parcela_terreno
            investimento_total += valor_parcela_terreno
        
        if m == 1: caixa -= valor_entrada_terreno
        caixa -= parcela_terreno_mes
        
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

        caixa += lucro_operacional_mes
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total
        
        if m % 12 == 0:
            # Lógica de Reinvestimento Baseada na Estratégia
            custo_expansao = 0
            if reinvestment_strategy == 'buy':
                custo_expansao = custo_modulo_atual_owned + cfg_owned['cost_per_land_plot']
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
            elif reinvestment_strategy == 'alternate':
                if compra_intercalada_counter % 2 == 0: # Compra
                    custo_expansao = custo_modulo_atual_owned + cfg_owned['cost_per_land_plot']
                else: # Aluga
                    custo_expansao = custo_modulo_atual_rented
            
            if caixa >= custo_expansao:
                novos_modulos_comprados = int(caixa // custo_expansao)
                custo_da_compra = novos_modulos_comprados * custo_expansao
                caixa -= custo_da_compra
                investimento_total += custo_da_compra

                if reinvestment_strategy == 'buy':
                    modules_owned += novos_modulos_comprados
                elif reinvestment_strategy == 'rent':
                    modules_rented += novos_modulos_comprados
                    aluguel_mensal_corrente += novos_modulos_comprados * cfg_rented['rent_per_new_module']
                elif reinvestment_strategy == 'alternate':
                    for _ in range(novos_modulos_comprados):
                        if compra_intercalada_counter % 2 == 0:
                            modules_owned += 1
                        else:
                            modules_rented += 1
                            aluguel_mensal_corrente += cfg_rented['rent_per_new_module']
                        compra_intercalada_counter += 1

            custo_modulo_atual_owned *= (1 + cfg_owned['cost_correction_rate'] / 100.0)
            custo_modulo_atual_rented *= (1 + cfg_rented['cost_correction_rate'] / 100.0)
        
        patrimonio_liquido = ((modules_owned + modules_rented) * custo_modulo_atual_owned) + caixa + fundo_ac + cfg_owned['land_total_value']
        rows.append({"Mês": m, "Ano": (m - 1) // 12 + 1, "Módulos Ativos": modules_owned + modules_rented, "Módulos Alugados": modules_rented, "Módulos Próprios": modules_owned, "Receita": receita, "Manutenção": manut, "Aluguel": aluguel_mensal_corrente, "Gastos": manut + aluguel_mensal_corrente, "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total, "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa, "Investimento Total Acumulado": investimento_total, "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac, "Módulos Comprados no Ano": novos_modulos_comprados, "Patrimônio Líquido": patrimonio_liquido})
    
    return pd.DataFrame(rows)

# ---------------------------
# Inicialização e Gerenciamento do Estado
# ---------------------------
def get_default_config():
    return {
        'rented': {'modules_init': 1, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_per_new_module': 750.0},
        'owned': {'modules_init': 0, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'land_total_value': 0.0, 'land_down_payment_pct': 20.0, 'land_installments': 120, 'cost_per_land_plot': 50000.0},
        'global': {'years': 15, 'max_withdraw_value': 50000.0, 'aportes': [{"mes": 3, "valor": 0.0}], 'retiradas': [{"mes": 25, "percentual": 30.0}], 'fundos': [{"mes": 25, "percentual": 10.0}]}
    }

if 'config' not in st.session_state: st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'active_page' not in st.session_state: st.session_state.active_page = 'Configurações'

# ---------------------------
# BARRA DE NAVEGAÇÃO LATERAL
# ---------------------------
with st.sidebar:
    st.markdown("<h1>Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p>Projeção com reinvestimento</p>", unsafe_allow_html=True)
    st.session_state.active_page = st.radio("Menu Principal", ["Configurações", "Planilhas", "Dashboard"], key="navigation_radio", label_visibility="collapsed")

# ---------------------------
# RENDERIZAÇÃO DAS PÁGINAS
# ---------------------------

# PÁGINA DE CONFIGURAÇÕES
if st.session_state.active_page == 'Configurações':
    st.title("Configurações de Investimento")
    st.markdown("<p class='subhead'>Configure os parâmetros da simulação financeira</p>", unsafe_allow_html=True)
    if st.button("🔄 Reset"):
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

    with st.container(border=True):
        st.subheader("Investimento com Terreno Comprado")
        c1, c2 = st.columns(2)
        cfg_o = st.session_state.config['owned']
        cfg_o['modules_init'] = c1.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
        cfg_o['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
        cfg_o['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
        cfg_o['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
        cfg_o['cost_correction_rate'] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg_o['cost_correction_rate'], format="%.1f", key="own_corr_rate")
        cfg_o['cost_per_land_plot'] = c2.number_input("Custo por terreno para novo módulo (R$)", 0.0, value=cfg_o['cost_per_land_plot'], format="%.2f", key="own_land_cost")
        
        st.markdown("---")
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

    with st.container(border=True):
        st.subheader("Parâmetros Globais da Simulação")
        cfg_g = st.session_state.config['global']
        c1, c2 = st.columns(2)
        cfg_g['years'] = c1.number_input("Horizonte de investimento (anos)", 1, 50, cfg_g['years'])
        cfg_g['max_withdraw_value'] = c2.number_input("Valor máximo de retirada mensal (R$)", 0.0, value=cfg_g['max_withdraw_value'], format="%.2f", help="Teto para retiradas baseadas em %.")
        
        st.markdown("---")
        st.markdown("###### Aportes, Retiradas e Fundos (% sobre o lucro mensal)")
        # ... (Lógica de eventos financeiros permanece a mesma)
        
# PÁGINA DO DASHBOARD
if st.session_state.active_page == 'Dashboard':
    st.title("Dashboard Financeiro")
    st.markdown(f"<p class='subhead'>Escolha uma estratégia de reinvestimento para simular</p>", unsafe_allow_html=True)
    
    strat_cols = st.columns(3)
    if strat_cols[0].button("📈 Simular: Comprar Terreno", use_container_width=True):
        st.session_state.simulation_df = simulate(st.session_state.config, 'buy')
    if strat_cols[1].button("📈 Simular: Alugar Terreno", use_container_width=True):
        st.session_state.simulation_df = simulate(st.session_state.config, 'rent')
    if strat_cols[2].button("📈 Simular: Intercalar", use_container_width=True, type="primary"):
        st.session_state.simulation_df = simulate(st.session_state.config, 'alternate')

    if st.session_state.simulation_df.empty:
        st.info("👆 Escolha uma estratégia e clique em um dos botões acima para iniciar a simulação.")
    else:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        
        st.markdown("---")
        st.subheader("Resultados Finais")
        kpi_cols = st.columns(3)
        kpi_cols[0].markdown(f"<div class='kpi-colored' style='background-color:{KPI_INVESTIMENTO_COLOR};'><div class='small-muted'>Investimento Total</div><div class='kpi-value'>{fmt_brl(final['Investimento Total Acumulado'])}</div></div>", unsafe_allow_html=True)
        kpi_cols[1].markdown(f"<div class='kpi-colored' style='background-color:{KPI_PATRIMONIO_COLOR};'><div class='small-muted'>Patrimônio Líquido</div><div class='kpi-value'>{fmt_brl(final['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)
        kpi_cols[2].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Módulos Finais</div><div class='kpi-value'>{int(final['Módulos Ativos'])}</div></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        kpi_cols2 = st.columns(3)
        kpi_cols2[0].markdown(f"<div class='kpi-colored' style='background-color:{CHART_RETIRADAS_COLOR};'><div class='small-muted'>Retiradas Acumuladas</div><div class='kpi-value'>{fmt_brl(final['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
        kpi_cols2[1].markdown(f"<div class='kpi-colored' style='background-color:{CHART_FUNDO_COLOR};'><div class='small-muted'>Fundo Acumulado</div><div class='kpi-value'>{fmt_brl(final['Fundo Acumulado'])}</div></div>", unsafe_allow_html=True)
        kpi_cols2[2].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Caixa Final</div><div class='kpi-value'>{fmt_brl(final['Caixa (Final Mês)'])}</div></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        chart_cols = st.columns(2)
        with chart_cols[0]:
            with st.container(border=True):
                st.subheader("Crescimento de Módulos (Próprios)")
                periodo_prop = st.slider("Período (meses)", 1, len(df), (1, len(df)), key="prop_slider")
                df_prop = df[(df['Mês'] >= periodo_prop[0]) & (df['Mês'] <= periodo_prop[1])]
                fig_prop = go.Figure(go.Scatter(x=df_prop["Mês"], y=df_prop["Módulos Próprios"], name="Módulos", line=dict(color=CHART_MODULOS_PROPRIOS_COLOR, width=2.5), fill='tozeroy'))
                fig_prop.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig_prop, use_container_width=True)
        with chart_cols[1]:
            with st.container(border=True):
                st.subheader("Crescimento de Módulos (Alugados)")
                periodo_alug = st.slider("Período (meses)", 1, len(df), (1, len(df)), key="alug_slider")
                df_alug = df[(df['Mês'] >= periodo_alug[0]) & (df['Mês'] <= periodo_alug[1])]
                fig_alug = go.Figure(go.Scatter(x=df_alug["Mês"], y=df_alug["Módulos Alugados"], name="Módulos", line=dict(color=CHART_MODULOS_ALUGADOS_COLOR, width=2.5), fill='tozeroy'))
                fig_alug.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig_alug, use_container_width=True)

        with st.container(border=True):
            st.subheader("Visão Geral (Distribuição Final)")
            dist_data = {'Valores': [final['Retiradas Acumuladas'], final['Fundo Acumulado'], final['Caixa (Final Mês)']], 'Categorias': ['Retiradas', 'Fundo Total', 'Caixa Final']}
            fig_pie = px.pie(dist_data, values='Valores', names='Categorias', color_discrete_sequence=[CHART_RETIRADAS_COLOR, CHART_FUNDO_COLOR, CHART_CAIXA_COLOR])
            fig_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.1), paper_bgcolor='white')
            st.plotly_chart(fig_pie, use_container_width=True)

# PÁGINA DE PLANILHAS
if st.session_state.active_page == 'Planilhas':
    # ... (A página de planilhas permanece a mesma, mas se beneficiará dos novos dados se uma simulação for executada)
    st.title("Planilhas Demonstrativas")
    # ... (código omitido por brevidade, é o mesmo da versão anterior)


