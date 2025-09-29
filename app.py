# app.py
# Simulador Modular — v4 com Correção Anual Unificada

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import re

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
        [data-testid="stSidebar"] .stMarkdown h1 {{
            padding-top: 1rem; color: {LIGHT_BACKGROUND};
        }}
        [data-testid="stSidebar"] .stMarkdown p {{
            color: rgba(236, 240, 241, 0.8);
        }}
        .stRadio > div {{ gap: 0.5rem; }}
        .stRadio > label > div {{
            font-size: 1.1rem !important;
            font-weight: 600 !important; padding: 0.75rem 1rem !important;
            border-radius: 8px !important; margin-bottom: 0.5rem; color: rgba(236, 240, 241, 0.8) !important;
            transition: all 0.2s; border-left: 3px solid transparent;
        }}
        .stRadio > div[role="radiogroup"] > label:has(div[data-baseweb="radio"][class*="e1y5xkzn3"]) > div {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: {CARD_COLOR} !important;
            border-left: 3px solid {PRIMARY_COLOR};
        }}
        .stApp {{ background-color: {LIGHT_BACKGROUND}; }}
        h1, h2, h3, h4, h5, h6, label, .st-emotion-cache-16idsys p {{ color: {TEXT_COLOR} !important; }}
        .subhead, .st-emotion-cache-1ghhuty p {{ color: {MUTED_TEXT_COLOR} !important; }}
        .stButton > button {{
            border-radius: 8px;
            border: 1px solid {PRIMARY_COLOR}; background-color: {PRIMARY_COLOR};
            color: white; padding: 10px 24px; font-weight: bold;
        }}
        .stButton > button:hover {{
            background-color: #005a8c;
            border-color: #005a8c;
        }}
        .stButton > button[kind="secondary"] {{
            background-color: transparent;
            color: {PRIMARY_COLOR};
        }}
        .stButton > button[kind="secondary"]:hover {{
            background-color: rgba(0, 114, 178, 0.1);
            color: {PRIMARY_COLOR};
        }}
        [data-testid="stMetricLabel"] p {{ color: {MUTED_TEXT_COLOR} !important; font-size: 0.9rem; }}
        [data-testid="stMetricValue"] div {{ color: {TEXT_COLOR} !important; }}
        .card {{
            background: {CARD_COLOR};
            border-radius: 8px; padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #D5DBDB; height: 100%;
        }}
        .kpi-card {{
            border-radius: 8px;
            padding: 1.25rem; color: white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1); height: 100%;
        }}
        .kpi-card-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; opacity: 0.9; }}
        .kpi-card-value {{ font-size: 2rem; font-weight: 700; }}
    </style>
""", unsafe_allow_html=True)


# --- FUNÇÕES HELPER ---
def fmt_brl(v):
    """Formata um valor numérico como uma string de moeda brasileira."""
    try:
        return f"R$ {v:,.2f}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def render_kpi_card(title, value, color):
    """Renderiza um cartão de KPI com título, valor e cor de fundo."""
    st.markdown(f"""
        <div class="kpi-card" style="background-color: {color};">
            <div class="kpi-card-title">{title}</div>
            <div class="kpi-card-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def df_to_excel_bytes(df: pd.DataFrame):
    """Converte um DataFrame para bytes de um arquivo Excel, formatando colunas."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Simulacao_Mensal')
        workbook  = writer.book
        worksheet = writer.sheets['Simulacao_Mensal']
        money_fmt = workbook.add_format({'num_format': 'R$ #,##0.00'})
        # Auto-ajuste da largura das colunas
        for i, col in enumerate(df.columns):
            width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, width)
            # Aplica formatação de moeda para colunas relevantes
            if any(k in col.lower() for k in ["receita", "custo", "valor", "manutenção", "aluguel", "parcela", "gasto", "aporte", "fundo", "retirada", "caixa", "investimento", "patrimônio"]):
                   worksheet.set_column(i, i, width, money_fmt)
    return output.getvalue()

def slug(s: str) -> str:
    """Converte uma string em um formato seguro para chaves e nomes de arquivo."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:60]

# ---------------------------
# Motor de Simulação (Atualizado)
# ---------------------------
@st.cache_data
def simulate(_config, reinvestment_strategy):
    # Desempacota a configuração para facilitar o acesso
    cfg_rented = _config['rented']
    cfg_owned = _config['owned']
    cfg_global = _config['global']

    months = cfg_global['years'] * 12
    rows = []

    # --- INICIALIZAÇÃO DE VARIÁVEIS DE ESTADO E FINANCEIRAS ---
    # Variáveis de estado da simulação
    modules_rented = cfg_rented['modules_init']
    modules_owned = cfg_owned['modules_init']
    caixa = 0.0
    investimento_total = (modules_rented * cfg_rented['cost_per_module']) + (modules_owned * cfg_owned['cost_per_module'])
    fundo_ac = 0.0
    retiradas_ac = 0.0
    valor_terrenos_adicionais = 0.0
    compra_intercalada_counter = 0

    # VARIÁVEIS LOCAIS PARA CORREÇÃO ANUAL (INFLAÇÃO)
    # Estas variáveis serão atualizadas anualmente com base na taxa geral
    correction_rate_pct = cfg_global.get('general_correction_rate', 0.0) / 100.0
    
    # Custos de aquisição de novos módulos
    custo_modulo_atual_rented = cfg_rented['cost_per_module']
    custo_modulo_atual_owned = cfg_owned['cost_per_module']

    # Valores "por módulo" ou "por nova unidade"
    receita_p_mod_rented = cfg_rented['revenue_per_module']
    receita_p_mod_owned = cfg_owned['revenue_per_module']
    manut_p_mod_rented = cfg_rented['maintenance_per_module']
    manut_p_mod_owned = cfg_owned['maintenance_per_module']
    aluguel_p_novo_mod = cfg_rented['rent_per_new_module']
    parcela_p_novo_terreno = cfg_owned['monthly_land_plot_parcel']

    # Custos mensais correntes (que acumulam com o tempo)
    aluguel_mensal_corrente = cfg_rented['rent_value']
    parcelas_terrenos_novos_mensal_corrente = 0.0

    # Lógica de financiamento do terreno inicial
    valor_entrada_terreno = 0.0
    parcela_terreno_inicial_atual = 0.0
    if cfg_owned['land_total_value'] > 0:
        valor_entrada_terreno = cfg_owned['land_total_value'] * (cfg_owned['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_owned['land_total_value'] - valor_entrada_terreno
        if cfg_owned['land_installments'] > 0:
            parcela_terreno_inicial_atual = valor_financiado / cfg_owned['land_installments']
        investimento_total += valor_entrada_terreno

    # Loop principal da simulação mês a mês
    for m in range(1, months + 1):
        # ATUALIZAÇÃO: Cálculos usam variáveis locais que são corrigidas anualmente
        receita = (modules_rented * receita_p_mod_rented) + (modules_owned * receita_p_mod_owned)
        manut = (modules_rented * manut_p_mod_rented) + (modules_owned * manut_p_mod_owned)
        novos_modulos_comprados = 0

        # Aportes
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes

        lucro_operacional_mes = receita - manut - aluguel_mensal_corrente - parcelas_terrenos_novos_mensal_corrente

        # Pagamento da parcela do terreno inicial
        parcela_terreno_inicial_mes = 0.0
        if cfg_owned['land_total_value'] > 0 and m <= cfg_owned['land_installments']:
            # ATUALIZAÇÃO: Usa a variável corrigida anualmente
            parcela_terreno_inicial_mes = parcela_terreno_inicial_atual
            investimento_total += parcela_terreno_inicial_mes
        if m == 1:
            caixa -= valor_entrada_terreno # Pagamento da entrada

        caixa += lucro_operacional_mes
        caixa -= parcela_terreno_inicial_mes

        # Lógica de Retiradas e Fundos
        fundo_mes_total, retirada_mes_efetiva = 0.0, 0.0
        if lucro_operacional_mes > 0:
            base_distribuicao = lucro_operacional_mes
            retirada_potencial = sum(base_distribuicao * (r['percentual'] / 100.0) for r in cfg_global['retiradas'] if m >= r['mes'])
            fundo_mes_total = sum(base_distribuicao * (f['percentual'] / 100.0) for f in cfg_global['fundos'] if m >= f['mes'])

            # Aplica o teto de retirada
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

        # Lógica de Reinvestimento (ocorre ao final de cada ano)
        if m % 12 == 0:
            custo_expansao = 0.0
            if reinvestment_strategy == 'buy':
                custo_expansao = custo_modulo_atual_owned
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
            elif reinvestment_strategy == 'alternate':
                custo_expansao = custo_modulo_atual_owned if compra_intercalada_counter % 2 == 0 else custo_modulo_atual_rented

            if custo_expansao > 0 and caixa >= custo_expansao:
                novos_modulos_comprados = int(caixa // custo_expansao)
                if novos_modulos_comprados > 0:
                    custo_da_compra = novos_modulos_comprados * custo_expansao
                    caixa -= custo_da_compra
                    investimento_total += custo_da_compra

                    if reinvestment_strategy == 'buy':
                        modules_owned += novos_modulos_comprados
                        parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
                        valor_terrenos_adicionais += novos_modulos_comprados * cfg_owned['land_value_per_module']
                    elif reinvestment_strategy == 'rent':
                        modules_rented += novos_modulos_comprados
                        aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
                    elif reinvestment_strategy == 'alternate':
                        for _ in range(novos_modulos_comprados):
                            if compra_intercalada_counter % 2 == 0:
                                modules_owned += 1
                                parcelas_terrenos_novos_mensal_corrente += parcela_p_novo_terreno
                                valor_terrenos_adicionais += cfg_owned['land_value_per_module']
                            else:
                                modules_rented += 1
                                aluguel_mensal_corrente += aluguel_p_novo_mod
                            compra_intercalada_counter += 1

            # --- NOVA LÓGICA DE CORREÇÃO ANUAL GERAL ---
            # Aplica a correção a todos os valores financeiros relevantes para o ano seguinte
            correction_factor = 1 + correction_rate_pct
            
            # Custos de aquisição futuros
            custo_modulo_atual_owned *= correction_factor
            custo_modulo_atual_rented *= correction_factor

            # Receitas e manutenções por módulo futuras
            receita_p_mod_rented *= correction_factor
            receita_p_mod_owned *= correction_factor
            manut_p_mod_rented *= correction_factor
            manut_p_mod_owned *= correction_factor

            # Custos mensais correntes (acumulados)
            aluguel_mensal_corrente *= correction_factor
            parcelas_terrenos_novos_mensal_corrente *= correction_factor
            parcela_terreno_inicial_atual *= correction_factor
            
            # Custos base para novas unidades futuras
            aluguel_p_novo_mod *= correction_factor
            parcela_p_novo_terreno *= correction_factor

        # Cálculo do patrimônio líquido
        patrimonio_liquido = (modules_owned * custo_modulo_atual_owned) + (modules_rented * custo_modulo_atual_rented) + caixa + fundo_ac + cfg_owned['land_total_value'] + valor_terrenos_adicionais

        rows.append({
            "Mês": m, "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules_owned + modules_rented,
            "Módulos Alugados": modules_rented, "Módulos Próprios": modules_owned,
            "Receita": receita, "Manutenção": manut, "Aluguel": aluguel_mensal_corrente,
            "Parcela Terreno Inicial": parcela_terreno_inicial_mes,
            "Parcelas Terrenos (Novos)": parcelas_terrenos_novos_mensal_corrente,
            "Gastos": manut + aluguel_mensal_corrente + parcela_terreno_inicial_mes + parcelas_terrenos_novos_mensal_corrente,
            "Aporte": aporte_mes, "Fundo (Mês)": fundo_mes_total,
            "Retirada (Mês)": retirada_mes_efetiva, "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac, "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Patrimônio Líquido": patrimonio_liquido
        })
    return pd.DataFrame(rows)


# ---------------------------
# Inicialização e Gerenciamento do Estado (Atualizado)
# ---------------------------
def get_default_config():
    """Retorna a configuração padrão do simulador."""
    return {
        'rented': {
            'modules_init': 1, 'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0,
            'rent_value': 750.0,
            'rent_per_new_module': 950.0 # Soma de maintenance (200) + rent_value (750)
        },
        'owned': {
            'modules_init': 0, 'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0, 'maintenance_per_module': 200.0,
            'monthly_land_plot_parcel': 0.0,
            'land_value_per_module': 200.0, # Soma de parcel (0) + maintenance (200)
            'land_total_value': 0.0, 'land_down_payment_pct': 20.0, 'land_installments': 120
        },
        'global': {
            'years': 15, 'max_withdraw_value': 50000.0,
            # NOVO: Taxa de correção unificada para inflação
            'general_correction_rate': 5.0,
            'aportes': [], 'retiradas': [], 'fundos': []
        }
    }

if 'config' not in st.session_state:
    st.session_state.config = get_default_config()

# Inicializa os dataframes e a página ativa
if 'simulation_df' not in st.session_state: st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state: st.session_state.comparison_df = pd.DataFrame()
if 'active_page' not in st.session_state: st.session_state.active_page = 'Dashboard'


# ---------------------------
# BARRA DE NAVEGAÇÃO LATERAL
# ---------------------------
with st.sidebar:
    st.markdown("<h1>Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p>Projeção com reinvestimento</p>", unsafe_allow_html=True)
    st.session_state.active_page = st.radio(
        "Menu Principal", ["Dashboard", "Relatórios e Dados", "Configurações"],
        key="navigation_radio", label_visibility="collapsed"
    )

# ---------------------------
# PÁGINA DE CONFIGURAÇÕES (Atualizada)
# ---------------------------
if st.session_state.active_page == 'Configurações':
    st.title("Configurações de Investimento")
    st.markdown("<p class='subhead'>Ajuste os parâmetros da simulação financeira e adicione eventos.</p>", unsafe_allow_html=True)

    if st.button("🔄 Resetar Configurações", type="secondary"):
        st.session_state.config = get_default_config()
        st.rerun()

    # Card: Terreno Alugado
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Investimento com Terreno Alugado")
    c1, c2 = st.columns(2)
    cfg_r = st.session_state.config['rented']
    cfg_r['modules_init'] = c1.number_input("Módulos iniciais (alugados)", 0, value=cfg_r['modules_init'], key="rent_mod_init")
    cfg_r['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_r['cost_per_module'], format="%.2f", key="rent_cost_mod")
    cfg_r['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_r['revenue_per_module'], format="%.2f", key="rent_rev_mod")
    cfg_r['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_r['maintenance_per_module'], format="%.2f", key="rent_maint_mod")
    cfg_r['rent_value'] = c2.number_input("Aluguel mensal fixo (R$)", 0.0, value=cfg_r['rent_value'], format="%.2f", key="rent_base_rent")
    
    # Cálculo automático do custo de aluguel por novo módulo
    cfg_r['rent_per_new_module'] = cfg_r['maintenance_per_module'] + cfg_r['rent_value']
    c1.number_input(
        "Custo de aluguel por novo módulo (R$)", 0.0,
        value=cfg_r['rent_per_new_module'], format="%.2f",
        key="rent_new_rent", disabled=True,
        help="Preenchido automaticamente (Manutenção + Aluguel Fixo)."
    )
    st.markdown('</div><br>', unsafe_allow_html=True)

    # Card: Terreno Comprado
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Investimento com Terreno Próprio")
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
    
    st.markdown("---")
    st.markdown("###### Parâmetros do Módulo Próprio")
    c1, c2 = st.columns(2)
    cfg_o['modules_init'] = c1.number_input("Módulos iniciais (próprios)", 0, value=cfg_o['modules_init'], key="own_mod_init")
    cfg_o['cost_per_module'] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_o['cost_per_module'], format="%.2f", key="own_cost_mod")
    cfg_o['revenue_per_module'] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o['revenue_per_module'], format="%.2f", key="own_rev_mod")
    cfg_o['maintenance_per_module'] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o['maintenance_per_module'], format="%.2f", key="own_maint_mod")
    
    cfg_o['monthly_land_plot_parcel'] = c2.number_input(
        "Parcela mensal por novo terreno (R$)", 0.0, 
        value=cfg_o.get('monthly_land_plot_parcel', 0.0), 
        format="%.2f", key="own_land_parcel", 
        disabled=(cfg_o['land_total_value'] > 0), 
        help="Este valor é preenchido automaticamente se um financiamento de terreno inicial for configurado."
    )
    
    # Cálculo automático do valor do terreno por novo módulo
    cfg_o['land_value_per_module'] = cfg_o['monthly_land_plot_parcel'] + cfg_o['maintenance_per_module']
    c1.number_input(
        "Valor do terreno por novo módulo (R$)", 0.0,
        value=cfg_o['land_value_per_module'], format="%.2f",
        key="own_land_value_per_module", disabled=True,
        help="Preenchido automaticamente (Parcela do Terreno + Manutenção)."
    )
    st.markdown('</div><br>', unsafe_allow_html=True)

    # Card: Parâmetros Globais
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Parâmetros Globais")
    cfg_g = st.session_state.config['global']
    c1, c2 = st.columns(2)
    cfg_g['years'] = c1.number_input("Horizonte de investimento (anos)", 1, 50, value=cfg_g['years'])
    # NOVO INPUT: Taxa de correção unificada
    cfg_g['general_correction_rate'] = c1.number_input(
        "Correção Anual Geral (Inflação %)", 0.0, 100.0,
        value=cfg_g.get('general_correction_rate', 5.0), format="%.1f",
        key="global_corr_rate",
        help="Taxa anual que corrige receitas, manutenções, aluguéis e parcelas."
    )
    cfg_g['max_withdraw_value'] = c2.number_input("Valor máximo de retirada mensal (R$)", 0.0, value=cfg_g['max_withdraw_value'], format="%.2f", help="Teto para retiradas baseadas em % do lucro.")
    st.markdown('</div><br>', unsafe_allow_html=True)

    # Card: Eventos Financeiros
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Eventos Financeiros")
    # Aportes
    st.markdown("<h6>Aportes (investimentos pontuais)</h6>", unsafe_allow_html=True)
    for i, aporte in enumerate(st.session_state.config['global']['aportes']):
        cols = st.columns([2, 3, 1])
        aporte['mes'] = cols[0].number_input("Mês", 1, None, aporte['mes'], key=f"aporte_mes_{i}")
        aporte['valor'] = cols[1].number_input("Valor (R$)", 0.0, None, aporte['valor'], format="%.2f", key=f"aporte_valor_{i}")
        if cols[2].button("Remover", key=f"aporte_remover_{i}", type="secondary"):
            st.session_state.config['global']['aportes'].pop(i)
            st.rerun()
    if st.button("Adicionar Aporte"):
        st.session_state.config['global']['aportes'].append({"mes": 1, "valor": 10000.0})
        st.rerun()
    st.markdown("---")
    # Retiradas
    st.markdown("<h6>Retiradas (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, retirada in enumerate(st.session_state.config['global']['retiradas']):
        cols = st.columns([2, 3, 1])
        retirada['mes'] = cols[0].number_input("Mês início", 1, None, retirada['mes'], key=f"retirada_mes_{i}")
        retirada['percentual'] = cols[1].number_input("% do lucro", 0.0, 100.0, retirada['percentual'], format="%.1f", key=f"retirada_pct_{i}")
        if cols[2].button("Remover", key=f"retirada_remover_{i}", type="secondary"):
            st.session_state.config['global']['retiradas'].pop(i)
            st.rerun()
    if st.button("Adicionar Retirada"):
        st.session_state.config['global']['retiradas'].append({"mes": 1, "percentual": 30.0})
        st.rerun()
    st.markdown("---")
    # Fundos
    st.markdown("<h6>Fundos de Reserva (% sobre o lucro mensal)</h6>", unsafe_allow_html=True)
    for i, fundo in enumerate(st.session_state.config['global']['fundos']):
        cols = st.columns([2, 3, 1])
        fundo['mes'] = cols[0].number_input("Mês início", 1, None, fundo['mes'], key=f"fundo_mes_{i}")
        fundo['percentual'] = cols[1].number_input("% do lucro", 0.0, 100.0, fundo['percentual'], format="%.1f", key=f"fundo_pct_{i}")
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
# (O código para as páginas 'Dashboard' e 'Relatórios e Dados' permanece o mesmo)
if st.session_state.active_page == 'Dashboard':
    st.title("Dashboard Estratégico")
    st.markdown("<p class='subhead'>Simule uma estratégia de reinvestimento ou compare todas.</p>", unsafe_allow_html=True)

    with st.container(border=True):
        strat_cols = st.columns(3)
        if strat_cols[0].button("📈 Simular: Comprar Novos", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'buy')
                st.session_state.comparison_df = pd.DataFrame() # Limpa comparação
        if strat_cols[1].button("📈 Simular: Alugar Novos", use_container_width=True, type="secondary"):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, 'rent')
                st.session_state.comparison_df = pd.DataFrame()
        if strat_cols[2].button("📈 Simular: Intercalar Novos", use_container_width=True, type="secondary"):
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
                st.session_state.simulation_df = pd.DataFrame() # Limpa simulação única

    # --- Bloco de Visualização de Comparação ---
    if not st.session_state.comparison_df.empty:
        st.subheader("Análise Comparativa de Estratégias")
        df_comp = st.session_state.comparison_df
        final_buy = df_comp[df_comp['Estratégia'] == 'Comprar'].iloc[-1]
        final_rent = df_comp[df_comp['Estratégia'] == 'Alugar'].iloc[-1]
        final_alt = df_comp[df_comp['Estratégia'] == 'Intercalar'].iloc[-1]
        st.markdown("##### Resultados Finais")
        kpi_cols = st.columns(4)
        with kpi_cols[0]: render_kpi_card("Patrimônio (Comprar)", fmt_brl(final_buy['Patrimônio Líquido']), PRIMARY_COLOR)
        with kpi_cols[1]: render_kpi_card("Patrimônio (Alugar)", fmt_brl(final_rent['Patrimônio Líquido']), MUTED_TEXT_COLOR)
        with kpi_cols[2]: render_kpi_card("Patrimônio (Intercalar)", fmt_brl(final_alt['Patrimônio Líquido']), WARNING_COLOR)
        with kpi_cols[3]:
            best_strategy = pd.Series({'Comprar': final_buy['Patrimônio Líquido'], 'Alugar': final_rent['Patrimônio Líquido'], 'Intercalar': final_alt['Patrimônio Líquido']}).idxmax()
            render_kpi_card("Melhor Estratégia", best_strategy, SUCCESS_COLOR)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            metric_options = ["Patrimônio Líquido", "Módulos Ativos", "Retiradas Acumuladas", "Fundo Acumulado", "Caixa (Final Mês)"]
            selected_metric = st.selectbox("Selecione uma métrica para comparar:", options=metric_options)
            fig_comp = px.line(df_comp, x="Mês", y=selected_metric, color='Estratégia', title=f'Comparativo de {selected_metric}',
                                color_discrete_map={'Comprar': PRIMARY_COLOR, 'Alugar': MUTED_TEXT_COLOR, 'Intercalar': WARNING_COLOR })
            fig_comp.update_layout(height=450, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR)
            st.plotly_chart(fig_comp, use_container_width=True)

    # --- Bloco de Visualização de Simulação Única ---
    elif not st.session_state.simulation_df.empty:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        st.subheader("Resultados da Simulação")
        kpi_cols = st.columns(4)
        with kpi_cols[0]: render_kpi_card("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']), PRIMARY_COLOR)
        with kpi_cols[1]: render_kpi_card("Retiradas Acumuladas", fmt_brl(final['Retiradas Acumuladas']), DANGER_COLOR)
        with kpi_cols[2]: render_kpi_card("Fundo Acumulado", fmt_brl(final['Fundo Acumulado']), INFO_COLOR)
        with kpi_cols[3]: render_kpi_card("Módulos Ativos Finais", f"{int(final['Módulos Ativos'])}", MUTED_TEXT_COLOR)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Análise Gráfica Detalhada")
        c1, c2 = st.columns(2)
        with c1, st.container(border=True):
            fig_pat = go.Figure()
            fig_pat.add_trace(go.Scatter(x=df["Mês"], y=df["Patrimônio Líquido"], name="Patrimônio", line=dict(color=PRIMARY_COLOR, width=2.5)))
            fig_pat.add_trace(go.Scatter(x=df["Mês"], y=df["Investimento Total Acumulado"], name="Investimento", line=dict(color=MUTED_TEXT_COLOR, width=1.5)))
            fig_pat.update_layout(title="Patrimônio vs. Investimento", height=400, margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR)
            st.plotly_chart(fig_pat, use_container_width=True)
        with c2, st.container(border=True):
            dist_data = { 'Valores': [final['Retiradas Acumuladas'], final['Fundo Acumulado'], final['Caixa (Final Mês)']], 'Categorias': ['Retiradas', 'Fundo Total', 'Caixa Final'] }
            fig_pie = px.pie(dist_data, values='Valores', names='Categorias',
                                color_discrete_sequence=[DANGER_COLOR, INFO_COLOR, WARNING_COLOR], hole=0.4)
            fig_pie.update_layout(title="Distribuição Final dos Recursos", height=400, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.1), paper_bgcolor=CARD_COLOR)
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("👆 Escolha uma estratégia ou compare todas para iniciar a simulação.")


# ---------------------------
# PÁGINA DE RELATÓRIOS E DADOS
# ---------------------------
if st.session_state.active_page == 'Relatórios e Dados':
    st.title("Relatórios e Dados")
    st.markdown("<p class='subhead'>Explore os dados detalhados da simulação mês a mês.</p>", unsafe_allow_html=True)
    
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty:
        df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty:
        df_to_show = st.session_state.simulation_df

    if df_to_show.empty:
        st.info("👈 Vá para a página 'Dashboard' para executar uma simulação primeiro.")
    else:
        df_analysis_base = df_to_show
        selected_strategy = None
        # Seletor de estratégia se estiver no modo de comparação
        if 'Estratégia' in df_analysis_base.columns:
            selected_strategy = st.selectbox(
                "Selecione a estratégia para análise:",
                 df_analysis_base['Estratégia'].unique(),
                 key="relat_strategy_select"
            )
            df_analysis = df_analysis_base[df_analysis_base['Estratégia'] == selected_strategy].copy()
        else:
            df_analysis = df_analysis_base.copy()

        # --- ANÁLISE POR PONTO NO TEMPO ---
        main_cols = st.columns([6, 4])
        with main_cols[0], st.container(border=True):
            st.subheader("Análise por Ponto no Tempo")
            c1, c2 = st.columns(2)
            anos_disponiveis = sorted(df_analysis['Ano'].unique())
            selected_year = c1.selectbox("Selecione o ano", options=anos_disponiveis)
            
            months_in_year = df_analysis[df_analysis['Ano'] == selected_year]['Mês'].unique()
            month_labels = sorted([((m - 1) % 12) + 1 for m in months_in_year])
            selected_month_label = c2.selectbox("Selecione o mês", options=month_labels)
            
            selected_month_abs = df_analysis[(df_analysis['Ano'] == selected_year) & (((df_analysis['Mês'] - 1) % 12) + 1 == selected_month_label)]['Mês'].iloc[0]
            data_point = df_analysis.loc[df_analysis["Mês"] == selected_month_abs].iloc[0]
            
            st.markdown("---")
            res_cols = st.columns(4)
            res_cols[0].metric("Total de Módulos", f"{int(data_point['Módulos Ativos'])}")
            res_cols[0].metric("Patrimônio Líquido", fmt_brl(data_point['Patrimônio Líquido']))
            res_cols[1].metric("Caixa no Mês", fmt_brl(data_point['Caixa (Final Mês)']))
            res_cols[1].metric("Investimento Total", fmt_brl(data_point['Investimento Total Acumulado']))
            res_cols[2].metric("Fundo (Mês)", fmt_brl(data_point['Fundo (Mês)']))
            res_cols[2].metric("Fundo Acumulado", fmt_brl(data_point['Fundo Acumulado']))
            res_cols[3].metric("Retirada (Mês)", fmt_brl(data_point['Retirada (Mês)']))
            res_cols[3].metric("Retiradas Acumuladas", fmt_brl(data_point['Retiradas Acumuladas']))

        with main_cols[1], st.container(border=True):
            st.subheader("Resumo Gráfico do Mês")
            
            chart_data = pd.DataFrame({
                "Categoria": ["Receita", "Gastos", "Retirada", "Fundo"],
                "Valor": [
                    data_point['Receita'],
                    data_point['Gastos'],
                    data_point['Retirada (Mês)'],
                    data_point['Fundo (Mês)']
                ]
            })
            fig_monthly = px.bar(chart_data, x="Categoria", y="Valor", text_auto='.2s', title=f"Fluxo Financeiro - Mês {selected_month_abs}",
                                 color="Categoria",
                                 color_discrete_map={
                                     "Receita": SUCCESS_COLOR,
                                     "Gastos": WARNING_COLOR,
                                     "Retirada": DANGER_COLOR,
                                     "Fundo": INFO_COLOR
                                 })
            fig_monthly.update_layout(showlegend=False, height=450, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor=CARD_COLOR, plot_bgcolor=CARD_COLOR)
            st.plotly_chart(fig_monthly, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        # --- TABELA COMPLETA COM SELETOR DE COLUNAS ---
        with st.container(border=True):
            st.subheader("Tabela Completa da Simulação")
            
            all_columns = df_analysis.columns.tolist()
            state_key = f"column_visibility_{slug(selected_strategy or 'default')}"

            if state_key not in st.session_state or set(st.session_state[state_key].keys()) != set(all_columns):
                default_cols = ['Mês', 'Ano', 'Módulos Ativos', 'Receita', 'Gastos', 'Caixa (Final Mês)', 'Patrimônio Líquido']
                st.session_state[state_key] = {c: (c in default_cols) for c in all_columns}
            
            with st.expander("Exibir/Ocultar Colunas da Tabela"):
                vis_map = st.session_state[state_key]
                grid_cols = st.columns(5)
                for i, col_name in enumerate(all_columns):
                    with grid_cols[i % 5]:
                        new_on = st.toggle(col_name, value=vis_map.get(col_name, False), key=f"tg_{slug(selected_strategy or 'default')}_{slug(col_name)}")
                        if new_on != vis_map.get(col_name):
                            vis_map[col_name] = new_on
                            st.session_state[state_key] = vis_map
                            st.rerun()

            cols_to_show = [c for c, v in st.session_state[state_key].items() if v]

            if not cols_to_show:
                st.warning("Selecione ao menos uma coluna para visualizar a tabela.")
            else:
                # Paginação
                page_size = 12
                total_pages = (len(df_analysis) - 1) // page_size + 1
                if 'page' not in st.session_state: st.session_state.page = 0
                
                if st.session_state.page >= total_pages:
                    st.session_state.page = 0

                start_idx = st.session_state.page * page_size
                end_idx = start_idx + page_size
                df_display = df_analysis.iloc[start_idx:end_idx].copy()

                # Formatação de moeda
                format_cols = [col for col in df_display.columns if df_display[col].dtype in ['float64', 'int64'] and col not in ['Mês', 'Ano']]
                for col in format_cols:
                    if col in df_display.columns:
                        df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
                
                st.dataframe( df_display[cols_to_show], use_container_width=True, hide_index=True )

                # Controles de Paginação
                page_cols = st.columns([1, 1, 8])
                if page_cols[0].button("Anterior", disabled=(st.session_state.page == 0), type="secondary"):
                    st.session_state.page -= 1
                    st.rerun()
                if page_cols[1].button("Próxima", disabled=(st.session_state.page >= total_pages - 1), type="secondary"):
                    st.session_state.page += 1
                    st.rerun()
                page_cols[2].markdown(f"<div style='padding-top:10px; color:{MUTED_TEXT_COLOR}'>Página {st.session_state.page + 1} de {total_pages}</div>", unsafe_allow_html=True)

            # Botão de Download
            excel_bytes = df_to_excel_bytes(df_analysis) # Baixa a tabela completa da estratégia selecionada
            st.download_button(
                "📥 Baixar Relatório Completo (Excel)",
                data=excel_bytes,
                file_name=f"relatorio_simulacao_{slug(selected_strategy or 'geral')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
