# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# --- Cores personalizadas e Configurações Iniciais ---
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
CHART_MODULOS_COLOR = SIDEBAR_BG
CHART_RECEITA_COLOR = "#2a9d8f"
CHART_GASTOS_COLOR = "#e76f51"
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
        .card {{ background: {CARD_COLOR}; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid {TABLE_BORDER_COLOR}; height: 100%; }}
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

def simulate(config):
    # Desempacota a configuração simplificada
    years, modules_init, cost_per_module, cost_correction_rate, revenue_per_module, maintenance_per_module, rent_value, rent_start_month, max_withdraw_value, aportes, retiradas, fundos = (
        config['years'], config['modules_init'], config['cost_per_module'], config['cost_correction_rate'], config['revenue_per_module'], config['maintenance_per_module'],
        config['rent_value'], config['rent_start_month'], config['max_withdraw_value'], config['aportes'], config['retiradas'], config['fundos']
    )
    months = years * 12
    rows = []
    modules = modules_init
    caixa = 0.0
    investimento_total = modules * cost_per_module
    fundo_ac = 0.0
    retiradas_ac = 0.0
    custo_modulo_atual = cost_per_module
    aportes_map = {a["mes"]: a.get("valor", 0.0) for a in aportes}
    for m in range(1, months + 1):
        receita = modules * revenue_per_module
        manut = modules * maintenance_per_module
        aluguel = rent_value if m >= rent_start_month else 0.0
        novos_modulos_comprados = 0
        aporte_mes = aportes_map.get(m, 0.0)
        caixa += aporte_mes
        investimento_total += aporte_mes
        
        lucro_operacional_mes = receita - manut - aluguel
        
        fundo_mes_total = 0.0
        retirada_mes_total_potencial = 0.0
        if lucro_operacional_mes > 0:
            base_distribuicao = lucro_operacional_mes
            for r in retiradas:
                if m >= r["mes"]: retirada_mes_total_potencial += base_distribuicao * (r["percentual"] / 100.0)
            for f in fundos:
                if m >= f["mes"]: fundo_mes_total += base_distribuicao * (f["percentual"] / 100.0)

        excesso_para_fundo = 0.0
        retirada_mes_efetiva = retirada_mes_total_potencial
        if max_withdraw_value > 0 and retirada_mes_total_potencial > max_withdraw_value:
            excesso_para_fundo = retirada_mes_total_potencial - max_withdraw_value
            retirada_mes_efetiva = max_withdraw_value
        
        fundo_mes_total += excesso_para_fundo
        
        caixa += lucro_operacional_mes
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total
        
        if m % 12 == 0:
            if caixa >= custo_modulo_atual:
                novos_modulos_comprados = int(caixa // custo_modulo_atual)
                custo_da_compra = novos_modulos_comprados * custo_modulo_atual
                caixa -= custo_da_compra
                modules += novos_modulos_comprados
                investimento_total += custo_da_compra
            custo_modulo_atual *= (1 + cost_correction_rate / 100.0)
            
        patrimonio_liquido = (modules * custo_modulo_atual) + caixa + fundo_ac

        rows.append({"Mês": m, "Ano": (m - 1) // 12 + 1, "Módulos Ativos": modules, "Receita": receita, "Manutenção": manut, "Aluguel": aluguel, "Gastos": manut + aluguel, "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total, "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa, "Investimento Total Acumulado": investimento_total, "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac, "Módulos Comprados no Ano": novos_modulos_comprados, "Patrimônio Líquido": patrimonio_liquido})
    
    return pd.DataFrame(rows)

# ---------------------------
# Inicialização e Gerenciamento do Estado
# ---------------------------
def get_default_config():
    return {'years': 15, 'modules_init': 1, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_start_month': 1, 'max_withdraw_value': 50000.0, 'aportes': [{"mes": 3, "valor": 0.0}], 'retiradas': [{"mes": 25, "percentual": 30.0}], 'fundos': [{"mes": 25, "percentual": 10.0}]}

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
    
    action_cols = st.columns([1,1,5])
    if action_cols[0].button("🔄 Reset"):
        st.session_state.config = get_default_config()
        st.rerun()
    if action_cols[1].button("🚀 Simular e ir para Dashboard", type="primary"):
        with st.spinner("Calculando simulação..."):
            st.session_state.simulation_df = simulate(st.session_state.config)
        st.session_state.active_page = 'Dashboard'
        st.rerun()

    with st.container(border=True):
        st.subheader("Configuração Geral")
        c1, c2 = st.columns(2)
        cfg = st.session_state.config
        cfg['years'] = c1.number_input("Horizonte de investimento (anos)", 1, 50, cfg['years'])
        cfg['modules_init'] = c1.number_input("Módulos iniciais", 1, value=cfg['modules_init'])
        cfg['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg['cost_per_module'], format="%.2f")
        cfg['revenue_per_module'] = c2.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg['revenue_per_module'], format="%.2f")
        cfg['cost_correction_rate'] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg['cost_correction_rate'], format="%.1f")
        cfg['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg['maintenance_per_module'], format="%.2f")
    
    with st.container(border=True):
        st.subheader("Custos Fixos e Distribuições")
        c1, c2 = st.columns(2)
        cfg['rent_value'] = c1.number_input("Aluguel mensal fixo (R$)", 0.0, value=cfg['rent_value'], format="%.2f")
        cfg['rent_start_month'] = c2.number_input("Mês de início do aluguel", 1, cfg['years']*12, cfg['rent_start_month'])
        cfg['max_withdraw_value'] = c1.number_input("Valor máximo de retirada mensal (R$)", 0.0, value=cfg['max_withdraw_value'], format="%.2f", help="Teto para retiradas baseadas em % do lucro.")

    with st.container(border=True):
        st.subheader("Eventos Financeiros (% sobre o lucro mensal)")
        st.markdown("###### Aportes (investimentos pontuais)")
        for i, aporte in enumerate(cfg['aportes']):
            c1, c2, c3 = st.columns([1, 2, 1])
            cfg['aportes'][i]['mes'] = c1.number_input("Mês", 1, cfg['years']*12, int(aporte['mes']), key=f"ap_mes_{i}")
            cfg['aportes'][i]['valor'] = c2.number_input("Valor (R$)", 0.0, float(aporte['valor']), format="%.2f", key=f"ap_val_{i}")
            if c3.button("Remover", key=f"ap_rem_{i}"): cfg['aportes'].pop(i); st.rerun()
        if st.button("Adicionar Aporte"): cfg['aportes'].append({"mes": 1, "valor": 10000.0}); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("###### Retiradas (% sobre o lucro mensal)")
        for i, retirada in enumerate(cfg['retiradas']):
            c1, c2, c3 = st.columns([1, 2, 1])
            cfg['retiradas'][i]['mes'] = c1.number_input("Mês início", 1, cfg['years']*12, int(retirada['mes']), key=f"ret_mes_{i}")
            cfg['retiradas'][i]['percentual'] = c2.number_input("% do lucro", 0.0, 100.0, float(retirada['percentual']), format="%.1f", key=f"ret_pct_{i}")
            if c3.button("Remover", key=f"ret_rem_{i}"): cfg['retiradas'].pop(i); st.rerun()
        if st.button("Adicionar Retirada"): cfg['retiradas'].append({"mes": 1, "percentual": 10.0}); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("###### Fundos de Reserva (% sobre o lucro mensal)")
        for i, fundo in enumerate(cfg['fundos']):
            c1, c2, c3 = st.columns([1, 2, 1])
            cfg['fundos'][i]['mes'] = c1.number_input("Mês início", 1, cfg['years']*12, int(fundo['mes']), key=f"fun_mes_{i}")
            cfg['fundos'][i]['percentual'] = c2.number_input("% do lucro", 0.0, 100.0, float(fundo['percentual']), format="%.1f", key=f"fun_pct_{i}")
            if c3.button("Remover", key=f"fun_rem_{i}"): cfg['fundos'].pop(i); st.rerun()
        if st.button("Adicionar Fundo"): cfg['fundos'].append({"mes": 1, "percentual": 5.0}); st.rerun()
    
# PÁGINA DO DASHBOARD
if st.session_state.active_page == 'Dashboard':
    st.title("Dashboard Financeiro")
    st.markdown(f"<p class='subhead'>Visão geral do seu investimento ao longo de {st.session_state.config['years']} anos</p>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("👈 Vá para a página de 'Configurações' para definir os parâmetros e iniciar uma simulação.")
    else:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        
        st.subheader("Resultados Finais")
        with st.container(border=True):
            kpi_cols = st.columns(3)
            investimento_inicial = st.session_state.config['modules_init'] * st.session_state.config['cost_per_module']
            kpi_cols[0].markdown(f"<div class='kpi-colored' style='background-color:{KPI_INVESTIMENTO_COLOR};'><div class='small-muted'>Investimento Inicial</div><div class='kpi-value'>{fmt_brl(investimento_inicial)}</div></div>", unsafe_allow_html=True)
            kpi_cols[1].markdown(f"<div class='kpi-colored' style='background-color:{KPI_PATRIMONIO_COLOR};'><div class='small-muted'>Patrimônio Líquido Final</div><div class='kpi-value'>{fmt_brl(final['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)
            kpi_cols[2].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Módulos Finais</div><div class='kpi-value'>{int(final['Módulos Ativos'])}</div></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            kpi_cols2 = st.columns(3)
            kpi_cols2[0].markdown(f"<div class='kpi-colored' style='background-color:{CHART_RETIRADAS_COLOR};'><div class='small-muted'>Total de Retiradas</div><div class='kpi-value'>{fmt_brl(final['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
            kpi_cols2[1].markdown(f"<div class='kpi-colored' style='background-color:{CHART_FUNDO_COLOR};'><div class='small-muted'>Total em Fundo</div><div class='kpi-value'>{fmt_brl(final['Fundo Acumulado'])}</div></div>", unsafe_allow_html=True)
            kpi_cols2[2].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Caixa Final</div><div class='kpi-value'>{fmt_brl(final['Caixa (Final Mês)'])}</div></div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Análise Gráfica Detalhada")

        with st.container(border=True):
            st.markdown("###### Evolução do Patrimônio e Investimento Total")
            periodo_pat = st.slider("Período (meses)", 1, len(df), (1, len(df)), key="pat_slider")
            df_pat = df.loc[periodo_pat[0]-1:periodo_pat[1]-1]
            fig_pat = go.Figure()
            fig_pat.add_trace(go.Scatter(x=df_pat["Mês"], y=df_pat["Patrimônio Líquido"], name="Patrimônio Líquido", line=dict(color=KPI_PATRIMONIO_COLOR, width=2.5)))
            fig_pat.add_trace(go.Scatter(x=df_pat["Mês"], y=df_pat["Investimento Total Acumulado"], name="Investimento Total", line=dict(color=KPI_INVESTIMENTO_COLOR, width=1.5)))
            fig_pat.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='white', paper_bgcolor='white')
            st.plotly_chart(fig_pat, use_container_width=True)
        
        chart_cols = st.columns(2)
        with chart_cols[0]:
            with st.container(border=True):
                st.markdown("###### Crescimento dos Módulos")
                periodo_mod = st.slider("Período", 1, len(df), (1, len(df)), key="mod_slider")
                df_mod = df.loc[periodo_mod[0]-1:periodo_mod[1]-1]
                fig_mod = go.Figure(go.Scatter(x=df_mod["Mês"], y=df_mod["Módulos Ativos"], name="Módulos", line=dict(color=CHART_MODULOS_COLOR, width=2.5), fill='tozeroy'))
                fig_mod.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig_mod, use_container_width=True)
        with chart_cols[1]:
            with st.container(border=True):
                st.markdown("###### Distribuição Final dos Recursos")
                dist_data = {'Valores': [final['Retiradas Acumuladas'], final['Fundo Acumulado'], final['Caixa (Final Mês)']], 'Categorias': ['Retiradas', 'Fundo Total', 'Caixa Final']}
                fig_pie = px.pie(dist_data, values='Valores', names='Categorias', color_discrete_sequence=[CHART_RETIRADAS_COLOR, CHART_FUNDO_COLOR, CHART_CAIXA_COLOR])
                fig_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.1), paper_bgcolor='white')
                st.plotly_chart(fig_pie, use_container_width=True)

# PÁGINA DE PLANILHAS
if st.session_state.active_page == 'Planilhas':
    st.title("Planilhas Demonstrativas")
    st.markdown("<p class='subhead'>Relatórios detalhados e análise de dados da simulação</p>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("👈 Vá para a página de 'Configurações' para definir os parâmetros e iniciar uma simulação.")
    else:
        df = st.session_state.simulation_df
        with st.container(border=True):
            st.subheader("Análise por Ponto no Tempo")
            c1, c2 = st.columns(2)
            anos_disponiveis = df['Ano'].unique()
            selected_year = c1.selectbox("Selecione o ano", options=anos_disponiveis)
            months_in_year = df[df['Ano'] == selected_year]['Mês'].unique()
            month_labels = [((m-1)%12)+1 for m in months_in_year]
            selected_month_label = c2.selectbox("Selecione o mês", options=month_labels)
            selected_month_abs = df[(df['Ano'] == selected_year) & (((df['Mês']-1)%12)+1 == selected_month_label)]['Mês'].iloc[0]
            data_point = df[df["Mês"] == selected_month_abs].iloc[0]
            st.markdown("---")
            res_cols = st.columns(2)
            res_cols[0].metric("Módulos Ativos", f"{int(data_point['Módulos Ativos'])}")
            res_cols[0].metric("Caixa no Mês", fmt_brl(data_point['Caixa (Final Mês)']))
            res_cols[1].metric("Patrimônio Líquido", fmt_brl(data_point['Patrimônio Líquido']))
            res_cols[1].metric("Investimento Total", fmt_brl(data_point['Investimento Total Acumulado']))
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Tabela Completa da Simulação")
            # (Código da paginação e download permanece o mesmo)


