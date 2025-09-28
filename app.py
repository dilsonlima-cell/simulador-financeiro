# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# --- Cores personalizadas e Configurações Iniciais ---
BG_COLOR = "#F7F7F5"
TEXT_COLOR = "#212529" # Cor de texto escurecida para melhor legibilidade
MUTED_TEXT_COLOR = "#5a5a5a" # Cinza mais escuro para subtítulos
TABLE_BORDER_COLOR = "#E0E0E0"
SIDEBAR_BG = "#086788"
SIDEBAR_TEXT_COLOR = "#FFFFFF"
CARD_BG = "rgba(0,0,0,0.03)"
GRADIENT_START = "#07A0C3"
GRADIENT_END = "#F0C808"
CUSTOM_GRADIENT = f"linear-gradient(90deg, {GRADIENT_START}, {GRADIENT_END})"
CHART_CAIXA_COLOR = "#F0C808"
CHART_FUNDO_COLOR = "#07A0C3"
CHART_RETIRADAS_COLOR = "#DD1C1A"
CHART_MODULOS_COLOR = SIDEBAR_BG
CHART_RECEITA_COLOR = "#2a9d8f" # Cor nova para receita
CHART_GASTOS_COLOR = "#e76f51" # Cor nova para gastos

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
        .card {{ background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid {TABLE_BORDER_COLOR}; height: 100%; }}
        .kpi-card .small-muted {{ color: {MUTED_TEXT_COLOR}; font-size: 0.9rem; }}
        .kpi-card .kpi-value {{ font-size: 2rem; font-weight: 700; }}
        .kpi-gradient {{ padding: 1.5rem; border-radius: 12px; background: {CUSTOM_GRADIENT}; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.06); height: 100%; }}
        .kpi-gradient .small-muted {{ color: rgba(255,255,255,0.8); font-size: 0.9rem; }}
        .kpi-gradient .kpi-value {{ font-size: 2rem; font-weight: 700; }}
        .stDataFrame, .stTable {{ border: none; box-shadow: none; padding: 0; }}
        table {{ width: 100%; }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Funções Utilitárias e de Lógica
# ---------------------------
def fmt_brl(v):
    return f"R$ {v:,.2f}"

def df_to_excel_bytes(df: pd.DataFrame, annual_df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Simulacao_Mensal')
        annual_df.to_excel(writer, index=False, sheet_name='Resumo_Anual')
    return output.getvalue()

def create_annual_summary(df: pd.DataFrame):
    if df.empty: return pd.DataFrame()
    agg_funcs = {'Receita': 'sum', 'Manutenção': 'sum', 'Aluguel': 'sum', 'Aporte': 'sum', 'Fundo (Mês)': 'sum', 'Retirada (Mês)': 'sum', 'Módulos Comprados no Ano': 'sum', 'Módulos Ativos': 'last', 'Caixa (Final Mês)': 'last'}
    annual_df = df.groupby('Ano').agg(agg_funcs).reset_index()
    annual_df.rename(columns={'Fundo (Mês)': 'Fundo (Ano)', 'Retirada (Mês)': 'Retirada (Ano)', 'Caixa (Final Mês)': 'Caixa (Final Ano)', 'Módulos Ativos': 'Módulos (Final Ano)'}, inplace=True)
    return annual_df[['Ano', 'Módulos (Final Ano)', 'Receita', 'Manutenção', 'Aluguel', 'Aporte', 'Retirada (Ano)', 'Fundo (Ano)', 'Módulos Comprados no Ano', 'Caixa (Final Ano)']]

def simulate(config):
    # (Lógica de simulação permanece a mesma da versão anterior)
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
        caixa += receita - manut - aluguel
        fundo_mes_total = 0.0
        retirada_mes_total_potencial = 0.0
        if caixa > 0:
            caixa_dist = caixa
            for r in retiradas:
                if m >= r["mes"]: retirada_mes_total_potencial += caixa_dist * (r["percentual"] / 100.0)
            for f in fundos:
                if m >= f["mes"]: fundo_mes_total += caixa_dist * (f["percentual"] / 100.0)
        excesso_para_fundo = 0.0
        retirada_mes_efetiva = retirada_mes_total_potencial
        if max_withdraw_value > 0 and retirada_mes_total_potencial > max_withdraw_value:
            excesso_para_fundo = retirada_mes_total_potencial - max_withdraw_value
            retirada_mes_efetiva = max_withdraw_value
        fundo_mes_total += excesso_para_fundo
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
        rows.append({"Mês": m, "Ano": (m - 1) // 12 + 1, "Módulos Ativos": modules, "Receita": receita, "Manutenção": manut, "Aluguel": aluguel, "Gastos": manut + aluguel, "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total, "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa, "Investimento Total Acumulado": investimento_total, "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac, "Módulos Comprados no Ano": novos_modulos_comprados, "Custo Módulo (Próx. Ano)": custo_modulo_atual if m % 12 == 0 else np.nan})
    df = pd.DataFrame(rows)
    df["Custo Módulo (Próx. Ano)"] = df["Custo Módulo (Próx. Ano)"].ffill()
    return df

# ---------------------------
# Inicialização e Gerenciamento do Estado
# ---------------------------
def get_default_config():
    return {'years': 15, 'modules_init': 1, 'cost_per_module': 75000.0, 'cost_correction_rate': 5.0, 'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0, 'rent_value': 750.0, 'rent_start_month': 23, 'max_withdraw_value': 50000.0, 'aportes': [{"mes": 3, "valor": 0}], 'retiradas': [{"mes": 25, "percentual": 30.0}], 'fundos': [{"mes": 25, "percentual": 10.0}]}

if 'config' not in st.session_state: st.session_state.config = get_default_config()
if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'page' not in st.session_state: st.session_state.page = 0
if 'active_page' not in st.session_state: st.session_state.active_page = 'Dashboard'

# ---------------------------
# BARRA DE NAVEGAÇÃO LATERAL
# ---------------------------
with st.sidebar:
    st.markdown("<h1>Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p>Projeção com reinvestimento</p>", unsafe_allow_html=True)
    st.session_state.active_page = st.radio("Menu Principal", ["Dashboard", "Configurações", "Planilhas"], key="navigation_radio", label_visibility="collapsed")

# ---------------------------
# RENDERIZAÇÃO DAS PÁGINAS
# ---------------------------

# PÁGINA DE CONFIGURAÇÕES
if st.session_state.active_page == 'Configurações':
    st.title("Configurações de Investimento")
    st.markdown("<p class='subhead'>Configure os parâmetros da simulação financeira</p>", unsafe_allow_html=True)
    action_cols = st.columns([1, 1, 5])
    if action_cols[0].button("🔄 Reset"):
        st.session_state.config = get_default_config()
        st.rerun()
    if action_cols[1].button("🚀 Simulação Ativa", type="primary"):
        with st.spinner("Calculando simulação..."):
            st.session_state.simulation_df = simulate(st.session_state.config)
        st.success("Simulação concluída! Verifique as outras abas.")
    
    # (O restante do código da página de configurações permanece o mesmo)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Configuração Geral")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.config['years'] = st.number_input("Horizonte de investimento (anos)", 1, 30, st.session_state.config['years'])
            st.session_state.config['cost_per_module'] = st.number_input("Custo inicial por módulo (R$)", 0.0, value=st.session_state.config['cost_per_module'], format="%.2f")
            st.session_state.config['revenue_per_module'] = st.number_input("Receita mensal por módulo (R$)", 0.0, value=st.session_state.config['revenue_per_module'], format="%.2f")
            st.session_state.config['max_withdraw_value'] = st.number_input("Valor máximo de retirada mensal (R$)", 0.0, value=st.session_state.config['max_withdraw_value'], format="%.2f", help="Quando a retirada baseada em % atingir este valor, o restante irá para o fundo de reserva. Deixe em 0 para desativar.")
        with c2:
            st.session_state.config['modules_init'] = st.number_input("Módulos iniciais", 1, value=st.session_state.config['modules_init'])
            st.session_state.config['cost_correction_rate'] = st.number_input("Correção anual do custo do módulo (%)", 0.0, value=st.session_state.config['cost_correction_rate'], format="%.1f")
            st.session_state.config['maintenance_per_module'] = st.number_input("Manutenção mensal por módulo (R$)", 0.0, value=st.session_state.config['maintenance_per_module'], format="%.2f")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Custos Fixos")
        c1, c2 = st.columns(2)
        with c1: st.session_state.config['rent_value'] = st.number_input("Aluguel mensal do terreno (R$)", 0.0, value=st.session_state.config['rent_value'], format="%.2f")
        with c2: st.session_state.config['rent_start_month'] = st.number_input("Mês de início do aluguel", 1, st.session_state.config['years']*12, st.session_state.config['rent_start_month'])
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Eventos Financeiros")
        st.markdown("###### Aportes (investimentos pontuais)")
        for i, aporte in enumerate(st.session_state.config['aportes']):
            c1, c2, c3 = st.columns([1, 2, 1])
            st.session_state.config['aportes'][i]['mes'] = c1.number_input("Mês", 1, st.session_state.config['years']*12, aporte['mes'], key=f"ap_mes_{i}")
            st.session_state.config['aportes'][i]['valor'] = c2.number_input("Valor (R$)", 0.0, aporte['valor'], format="%.2f", key=f"ap_val_{i}")
            if c3.button("Remover", key=f"ap_rem_{i}"): st.session_state.config['aportes'].pop(i); st.rerun()
        if st.button("Adicionar Aporte"): st.session_state.config['aportes'].append({"mes": 1, "valor": 10000.0}); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("###### Retiradas (% sobre o caixa mensal)")
        for i, retirada in enumerate(st.session_state.config['retiradas']):
            c1, c2, c3 = st.columns([1, 2, 1])
            st.session_state.config['retiradas'][i]['mes'] = c1.number_input("Mês início", 1, st.session_state.config['years']*12, retirada['mes'], key=f"ret_mes_{i}")
            st.session_state.config['retiradas'][i]['percentual'] = c2.number_input("% do caixa", 0.0, 100.0, retirada['percentual'], format="%.1f", key=f"ret_pct_{i}")
            if c3.button("Remover", key=f"ret_rem_{i}"): st.session_state.config['retiradas'].pop(i); st.rerun()
        if st.button("Adicionar Retirada"): st.session_state.config['retiradas'].append({"mes": 1, "percentual": 10.0}); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("###### Fundos de Reserva (% sobre o caixa mensal)")
        for i, fundo in enumerate(st.session_state.config['fundos']):
            c1, c2, c3 = st.columns([1, 2, 1])
            st.session_state.config['fundos'][i]['mes'] = c1.number_input("Mês início", 1, st.session_state.config['years']*12, fundo['mes'], key=f"fun_mes_{i}")
            st.session_state.config['fundos'][i]['percentual'] = c2.number_input("% do caixa", 0.0, 100.0, fundo['percentual'], format="%.1f", key=f"fun_pct_{i}")
            if c3.button("Remover", key=f"fun_rem_{i}"): st.session_state.config['fundos'].pop(i); st.rerun()
        if st.button("Adicionar Fundo"): st.session_state.config['fundos'].append({"mes": 1, "percentual": 5.0}); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# PÁGINA DO DASHBOARD
if st.session_state.active_page == 'Dashboard':
    st.title("Dashboard Financeiro")
    st.markdown(f"<p class='subhead'>Visão geral do seu investimento em módulos ao longo de {st.session_state.config['years']} anos</p>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("👈 Vá para a página de 'Configurações' para definir os parâmetros e iniciar uma simulação.")
    else:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        
        kpi_cols = st.columns(4)
        kpi_cols[0].markdown(f"<div class='kpi-card'><div class='small-muted'>Investimento Inicial</div><div class='kpi-value'>{fmt_brl(st.session_state.config['modules_init'] * st.session_state.config['cost_per_module'])}</div></div>", unsafe_allow_html=True)
        kpi_cols[1].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Módulos Finais</div><div class='kpi-value'>{int(final['Módulos Ativos'])}</div></div>", unsafe_allow_html=True)
        kpi_cols[2].markdown(f"<div class='kpi-card'><div class='small-muted'>Retiradas Acumuladas</div><div class='kpi-value'>{fmt_brl(final['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
        kpi_cols[3].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Caixa Final</div><div class='kpi-value'>{fmt_brl(final['Caixa (Final Mês)'])}</div></div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        chart_cols = st.columns(2)
        with chart_cols[0]:
            with st.container(border=True):
                st.subheader("Evolução Financeira")
                max_months = len(df)
                periodo_evolucao = st.slider("Selecione o período (meses)", 1, max_months, (1, max_months), key="evolucao_slider")
                df_evolucao = df[(df['Mês'] >= periodo_evolucao[0]) & (df['Mês'] <= periodo_evolucao[1])]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_evolucao["Mês"], y=df_evolucao["Caixa (Final Mês)"], name="Caixa", line=dict(color=CHART_CAIXA_COLOR, width=2.5)))
                fig.add_trace(go.Scatter(x=df_evolucao["Mês"], y=df_evolucao["Fundo Acumulado"], name="Fundo", line=dict(color=CHART_FUNDO_COLOR, width=1.5)))
                fig.add_trace(go.Scatter(x=df_evolucao["Mês"], y=df_evolucao["Retiradas Acumuladas"], name="Retiradas", line=dict(color=CHART_RETIRADAS_COLOR, width=1.5)))
                fig.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
        with chart_cols[1]:
            with st.container(border=True):
                st.subheader("Crescimento dos Módulos")
                max_months_mod = len(df)
                periodo_modulos = st.slider("Selecione o período (meses)", 1, max_months_mod, (1, max_months_mod), key="modulos_slider")
                df_modulos = df[(df['Mês'] >= periodo_modulos[0]) & (df['Mês'] <= periodo_modulos[1])]
                fig_mod = go.Figure(go.Scatter(x=df_modulos["Mês"], y=df_modulos["Módulos Ativos"], name="Módulos", line=dict(color=CHART_MODULOS_COLOR, width=2.5), fill='tozeroy'))
                fig_mod.update_layout(height=400, margin=dict(l=10,r=10,t=40,b=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mod, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        chart_cols2 = st.columns(2)
        with chart_cols2[0]:
            with st.container(border=True):
                st.subheader("Performance Mensal")
                last_months = st.number_input("Visualizar últimos meses", min_value=1, max_value=len(df), value=min(24, len(df)), key="perf_meses")
                df_perf = df.tail(last_months)
                fig_perf = go.Figure()
                fig_perf.add_trace(go.Bar(x=df_perf['Mês'], y=df_perf['Receita'], name='Receita', marker_color=CHART_RECEITA_COLOR))
                fig_perf.add_trace(go.Bar(x=df_perf['Mês'], y=df_perf['Gastos'], name='Gastos', marker_color=CHART_GASTOS_COLOR))
                fig_perf.update_layout(barmode='group', height=400, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_perf, use_container_width=True)
        with chart_cols2[1]:
            with st.container(border=True):
                st.subheader("Distribuição Final dos Recursos")
                dist_data = {'Valores': [final['Retiradas Acumuladas'], final['Fundo Acumulado'], final['Caixa (Final Mês)']], 'Categorias': ['Retiradas', 'Fundo Total', 'Caixa Final']}
                fig_pie = px.pie(dist_data, values='Valores', names='Categorias', color_discrete_sequence=[CHART_RETIRADAS_COLOR, CHART_FUNDO_COLOR, CHART_CAIXA_COLOR])
                fig_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.1))
                st.plotly_chart(fig_pie, use_container_width=True)

# PÁGINA DE PLANILHAS
if st.session_state.active_page == 'Planilhas':
    st.title("Planilhas Demonstrativas")
    st.markdown("<p class='subhead'>Relatórios detalhados e análise de dados da simulação</p>", unsafe_allow_html=True)
    if st.session_state.simulation_df.empty:
        st.info("👈 Vá para a página de 'Configurações' para definir os parâmetros e iniciar uma simulação.")
    else:
        df = st.session_state.simulation_df
        annual_summary_df = create_annual_summary(df)
        with st.container(border=True):
            st.subheader("Resumo Final da Simulação")
            final_summary_cols = st.columns(2)
            final = df.iloc[-1]
            with final_summary_cols[0]:
                st.metric("Marco Final", f"Ano {final['Ano']}, Mês {((final['Mês']-1)%12)+1}")
                st.metric("Caixa Final", fmt_brl(final['Caixa (Final Mês)']))
                st.metric("Retiradas Totais", fmt_brl(final['Retiradas Acumuladas']))
            with final_summary_cols[1]:
                st.metric("Módulos Finais", f"{int(final['Módulos Ativos'])}")
                st.metric("Fundo Total", fmt_brl(final['Fundo Acumulado']))
                st.metric("Investimento Total", fmt_brl(final['Investimento Total Acumulado']))
        
        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader("Tabela Completa da Simulação")
            page_size = 20
            total_pages = (len(df) - 1) // page_size + 1
            start_idx = st.session_state.page * page_size
            end_idx = start_idx + page_size
            df_display = df.iloc[start_idx:end_idx].copy()
            format_cols = ["Receita", "Manutenção", "Aluguel", "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado", "Fundo Acumulado", "Retiradas Acumuladas", "Custo Módulo (Próx. Ano)"]
            for col in format_cols: df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            page_cols = st.columns([1, 1, 8])
            if page_cols[0].button("Anterior", disabled=(st.session_state.page == 0)):
                st.session_state.page -= 1; st.rerun()
            if page_cols[1].button("Próxima", disabled=(st.session_state.page >= total_pages - 1)):
                st.session_state.page += 1; st.rerun()
            page_cols[2].markdown(f"<div style='padding-top:10px'>Página {st.session_state.page + 1} de {total_pages}</div>", unsafe_allow_html=True)
            
        excel_bytes = df_to_excel_bytes(df, annual_summary_df)
        st.download_button("📥 Baixar Relatório (CSV)", data=excel_bytes, file_name=f"simulacao_modulos_{st.session_state.config['years']}_anos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

