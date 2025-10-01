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

# --- PALETA DE CORES (fiel à imagem) ---
PRIMARY_COLOR   = "#FF9234"      # Laranja vibrante do header
SECONDARY_COLOR = "#6C757D"      # Cinza escuro dos textos secundários
SUCCESS_COLOR   = "#28A745"      # Verde sucesso
DANGER_COLOR    = "#DC3545"      # Vermelho erro
WARNING_COLOR   = "#FFC107"      # Alerta amarelo
INFO_COLOR      = "#17A2B8"      # Informações azuis
APP_BG          = "#FFFFFF"      # Fundo branco da página
CARD_COLOR      = "#FFFFFF"      # Fundo branco dos cards
TEXT_COLOR      = "#212529"      # Texto escuro principal
MUTED_TEXT_COLOR= "#6C757D"      # Texto cinza secundário
COR_DA_BORDA_DA_TABELA = "#E9ECEF"
COR_DA_GRADE_DO_GRÁFICO = "#E9ECEF"

# --- COLUNAS PARA FORMATAÇÃO ---
COLEÇÕES_DE_DINHEIRO = {
    "Receita","Manutenção","Aluguel","Parcela Terreno Inicial","Parcelas Terrenos (Novos)","Gastos",
    "Aporte","Fundo (Mês)","Retirada (Mês)","Caixa (Final Mês)","Investimento Total Acumulado",
    "Fundo Acumulado","Retiradas Acumuladas","Patrimônio Líquido","Juros Terreno Inicial",
    "Amortização Terreno Inicial","Equity Terreno Inicial","Valor de Mercado Terreno",
    "Patrimônio Terreno","Juros Acumulados","Amortização Acumulada","Desembolso Total",
    "Aluguel Acumulado","Parcelas Novas Acumuladas"
}
COUNT_COLS = {"Mês","Ano","Módulos Ativos","Módulos Alugados","Módulos Próprios","Módulos Comprados no Ano"}

# ---------------------------
# Ajudantes
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

def calcular_métricas_de_resumo(df):
    resumo = {"roi_pct": 0, "break_even_month": "N/A", "total_investment": 0, "net_profit": 0}
    if df.empty:
        return resumo
    final = df.iloc[-1]
    total_investment = final['Investimento Total Acumulado']
    resumo["investimento_total"] = total_investment
    if total_investment > 0:
        net_profit = final['Patrimônio Líquido'] - total_investment
        resumo["roi_pct"] = (net_profit / total_investment) * 100
        resumo["lucro_líquido"] = net_profit
    break_even_df = df[df['Patrimônio Líquido'] >= df['Investimento Total Acumulado']]
    if not break_even_df.empty:
        resumo["break_even_month"] = int(break_even_df.iloc[0]['Mês'])
    return resumo

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Simulacao_Mensal")
        wb, ws = writer.book, writer.sheets["Simulacao_Mensal"]
        money_fmt = wb.add_format({"num_format": "R$ #,##0,00"})
        for i, col in enumerate(df.columns):
            width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            fmt = money_fmt if col in COLEÇÕES_DE_DINHEIRO else None
            ws.set_column(i, i, width, fmt)
    return output.getvalue()

def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:60]

def apply_plot_theme(fig, título=Nenhum, h=420):
    fig.update_layout(
        título=dict(texto=título or fig.layout.title.texto, x=0,5, xanchor='centro', fonte=dict(tamanho=16, cor=COR_DO_TEXTO)),
        altura=h, margem=dict(l=10, r=10, t=60, b=10),
        legenda=dict(orientação="h", yanchor="inferior", y=1,02, xanchor="direita", x=1,
                    bgcolor='rgba(255,255,255,0.85)', bordercolor=TABLE_BORDER_COLOR, borderwidth=1,
                    fonte=dict(cor=COR_DO_TEXTO)),
        plot_bgcolor=COR_DO_CARTÃO, paper_bgcolor=COR_DO_CARTÃO, font=dict(color=COR_DO_TEXTO),
        xaxis=dict(gridcolor=COR_DA_GRID_DO_GRÁFICO, cor_da_linha=COR_DA_BORDA_DA_TABELA, fonte_do_tiquetaque=dict(cor=COR_DO_TEXTO_MUDO)),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR))
    )
    return figo

def compute_cache_key(cfg: dict) -> str:
    payload = json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()

def computa_total_de_investimento_inicial(cfg):
    r = cfg['alugado']; o = cfg['possuído']
    total = r['modules_init'] * r['custo_por_módulo'] + o['modules_init'] * o['custo_por_módulo']
    if o.get('land_total_value', 0) > 0:
        total += o['valor_total_do_terreno'] * (o.get('valor_inicial_do_terreno', 0) / 100,0)
    retorno total

# ---------------------------
# Config da página + CSS (fiel à imagem)
# ---------------------------
st.set_page_config(page_title="Simulador Financeiro de Investimentos", layout="wide", initial_sidebar_state="collapsed")

st.markdown(f"""
    <estilo>
        .main .block-container {{ preenchimento: 0 1,25rem 2rem; largura máxima: 1400px; }}
        .stApp {{ fundo: {APP_BG}; }}
        h1, h2, h3, h4, h5, h6 {{ cor: {COR_DO_TEXTO}; espessura da fonte: 700; }}
        /* Cabeçalho */
        .cabeçalho {{
            fundo: gradiente linear(90 graus, #FF9234 0%, #FFC107 100%);
            cor: branco; preenchimento: 1,5 rem 1,2 rem; alinhamento de texto: centralizado;
            caixa-sombra: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .título-cabeçalho {{
            tamanho da fonte: 2rem; espessura da fonte: 800; margem: 0;
            sombra de texto: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .cabeçalho-sub {{
            tamanho da fonte: 1rem; opacidade: .95; margem superior: .35rem;
        }}
        /* Ambos */
        .stTabs [data-baseweb="lista-de-guias"] {{
            lacuna: 0;
            cor de fundo: #F8F9FA;
            raio da borda: 8px;
            preenchimento: 0,5rem;
            margem inferior: 1rem;
            borda: 1px sólido {TABLE_BORDER_COLOR};
        }}
        .stTabs [data-baseweb="guia"] {{
            cor de fundo: #FFFFFF;
            borda: 1px sólido {TABLE_BORDER_COLOR};
            raio da borda: 6px;
            preenchimento: 0,5rem 1rem;
            margem: 0;
            espessura da fonte: 600;
            transição: todos os 0,2s de facilidade;
        }}
        .stTabs [data-baseweb="tab"]:passe o mouse {{
            cor de fundo: #E9ECEF;
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            cor de fundo: {COR_PRINCIPAL};
            cor: branco;
            cor da borda: {COR_PRINCIPAL};
        }}
        /* Cartões */
        .cartão {{
            fundo: {COR_DO_CARTAO}; raio da borda: 8px; preenchimento: 1,25 rem; borda: 1px sólido {COR_DA_BORDA_DA_TABELA}; margem inferior: 1 rem;
            caixa-sombra: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .título-da-seção {{
            espessura da fonte: 800; margem: .25rem 0 .75rem; cor: {COR_DO_TEXTO}; tamanho da fonte: 1,1rem;
        }}
        /* Campos de entrada */
        .stTextInput entrada, .stNumberInput entrada {{
            fundo: {COR_DO_CARTÃO} !importante; cor: {COR_DO_TEXTO} !importante; borda: 1px sólido {COR_DA_BORDA_DA_TABELA} !importante;
            raio da borda: 6px;
        }}
        /* Botões */
        .stButton > botão {{
            raio da borda: 6px; borda: 1px sólido {COR_PRINCIPAL};
            cor de fundo: {PRIMARY_COLOR}; cor: branco;
            preenchimento: 8px 16px; espessura da fonte: 700; transição: todos 0,2s de facilidade;
        }}
        .stButton > botão:hover {{
            cor de fundo: #FF7B00; cor da borda: #FF7B00;
        }}
        .investir-tira {{
            fundo: gradiente linear(90 graus, #FF9234, #FFC107);
            cor: branco; raio da borda: 8px; preenchimento: .6rem 1rem; espessura da fonte: 800; exibição: flex; justificar-conteúdo: espaço-entre; alinhar-itens: centro;
            margem inferior: 1rem;
        }}
        /* Tabela */
        [data-testid="stDataFrame"] th {{
            cor de fundo: #F8F9FA !importante; cor: {COR_DO_TEXTO} !importante; espessura da fonte: 600;
        }}
        [data-testid="stDataFrame"] td {{
            cor: {COR_DO_TEXTO};
        }}
    </estilo>
""", unsafe_allow_html=Verdadeiro)

# ---------------------------
# Motor de Simulação (v12) - COMPLETAMENTE REESCRITO E VERIFICADO
# ---------------------------
@st.cache_data(show_spinner=Falso)
def simular(_config, estratégia_de_reinvestimento, chave_de_cache: str):
    """
    Função principal de simulação, reescrita para garantir precisão e clareza.
    """
    # Extrair configurações
    cfg_rented = _config['alugado']
    cfg_owned  = _config['propriedade']
    cfg_global = _config['global']

    # Inicializar variáveis
    meses = cfg_global['anos'] * 12
    linhas = []
    módulos_alugados = cfg_rented['módulos_init']
    módulos_possuídos = cfg_owned['módulos_init']
    caixa = 0.0
    investimento_total = (
        módulos_alugados * cfg_rented['custo_por_módulo'] +
        módulos_possuídos * cfg_owned['custo_por_módulo']
    )
    valor_historico_alugado = módulos_alugado * cfg_alugado['custo_por_módulo']
    valor_historico_possuído = módulos_possuídos * cfg_possuído['custo_por_módulo']
    fundo_ac = 0.0
    retiradas_ac = 0.0
    compra_intercalada_counter = 0
    taxa_de_correção_pct = cfg_global.get('taxa_de_correção_geral', 0.0) / 100.0
    taxa_de_apreciação_da_terra_pct = cfg_global.get('taxa_de_apreciação_da_terra', 3.0) / 100.0

    # Preços atuais (serão atualizados anualmente)
    custo_modulo_atual_rented = cfg_rented['custo_por_módulo']
    custo_modulo_atual_owned  = cfg_owned['custo_por_módulo']
    receita_p_mod_rented = cfg_rented['receita_por_módulo']
    receita_p_mod_owned = cfg_owned['receita_por_módulo']
    manut_p_mod_rented = cfg_rented['manutenção_por_módulo']
    manut_p_mod_owned = cfg_owned['manutenção_por_módulo']
    aluguel_p_novo_mod        = cfg_rented['aluguel_por_novo_módulo']
    parcela_p_novo_terreno = cfg_owned['monthly_land_plot_parcel']

    # Calcula o aluguel mensal inicial e das parcelas novas
    aluguel_mensal_corrente = cfg_rented['valor_do_aluguel'] + (cfg_rented['modules_init'] * cfg_rented['aluguel_por_novo_módulo'])
    parcelas_terrenos_novos_mensal_corrente = 0.0

    # Inicializa variáveis de financiamento do terreno
    parcela_terreno_inicial_atual = 0.0
    saldo_financiamento_terreno = 0.0
    equity_terreno_inicial = 0.0
    juros_acumulados = 0.0
    amortizacao_acumulada = 0.0
    valor_compra_terreno = 0.0
    taxa_juros_mensal = 0.0
    amortizacao_mensal = 0.0

    # Se há terreno próprio, inicializa o financiamento
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

    # Loop principal de simulação
    for m in range(1, meses + 1):
        # Calcular Receita e Manutenção
        receita = (módulos_alugados * receita_p_mod_rented) + (módulos_possuídos * receita_p_mod_owned)
        manut   = (módulos_alugados * manut_p_mod_rented)   + (módulos_possuídos * manut_p_mod_owned)
        novos_modulos_comprados = 0

        # Adicionar Aportes
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['aportes'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes

        # Calcular Gastos Operacionais
        gastos_operacionais = aluguel_mensal_corrente + parcelas_terrenos_novos_mensal_corrente
        lucro_operacional = receita - manut - gastos_operacionais

        # Calcular Parcela do Terreno Inicial
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

        # Atualizar Caixa
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
            if estratégia_de_reinvestimento == 'comprar':
                custo = custo_modulo_atual_owned
                if caixa >= custo > 0:
                    novos_modulos_comprados = int(caixa // custo)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        valor_historico_possuído += custo_da_compra
                        módulos_possuídos += novos_modulos_comprados
                        parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
            elif estratégia_de_reinvestimento == 'alugar':
                custo = custo_modulo_atual_rented
                if caixa >= custo > 0:
                    novos_modulos_comprados = int(caixa // custo)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        valor_historico_alugado += custo_da_compra
                        módulos_alugados += novos_modulos_comprados
                        aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod
            elif estratégia_de_reinvestimento == 'alternativo':
                alvo = 'comprar' if ((módulos_possuídos + módulos_alugados) % 2 == 0) else 'alugar'
                custo = custo_modulo_atual_owned if alvo == 'comprar' else custo_modulo_atual_rented
                if caixa >= custo > 0:
                    novos_modulos_comprados = int(caixa // custo)
                    if novos_modulos_comprados > 0:
                        custo_da_compra = novos_modulos_comprados * custo
                        caixa -= custo_da_compra
                        investimento_total += custo_da_compra
                        if alvo == 'comprar':
                            valor_historico_possuído += custo_da_compra
                            módulos_possuídos += novos_modulos_comprados
                            parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno
                        else:
                            valor_historico_alugado += custo_da_compra
                            módulos_alugados += novos_modulos_comprados
                            aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod

            # Aplicar correção anual nos preços
            correction_factor = 1 + taxa_de_correção_pct
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

        # Calcular Patrimônio
        valor_mercado_terreno = valor_compra_terreno * ((1 + taxa_de_apreciação_da_terra_pct) ** (m / 12))
        patrimonio_terreno = valor_mercado_terreno - saldo_financiamento_terreno
        ativos  = valor_historico_possuído + valor_historico_alugado + caixa + fundo_ac + patrimonio_terreno
        passivos= saldo_financiamento_terreno
        patrimonio_liquido = ativos - passivos
        desembolso_total = investimento_total + juros_acumulados + aluguel_acumulado + parcelas_novas_acumuladas
        gastos_totais = manut + aluguel_mensal_corrente + juros_terreno_mes + parcelas_terrenos_novos_mensal_corrente

        # Adicionar linha ao DataFrame
        linhas.append({
            "Mês": m,
            "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": módulos_possuídos + módulos_alugados,
            "Módulos Alugados": módulos_alugados,
            "Módulos Próprios": módulos_possuídos,
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

    return pd.DataFrame(linhas)

# ---------------------------
# Estado Inicial
# ---------------------------
def get_default_config():
    return {
        'alugado': {
            'módulos_init': 1,
            'custo_por_módulo': 75000.0,
            'receita_por_módulo': 4500.0,
            'manutenção_por_módulo': 200.0,
            'valor_do_aluguel': 750.0,
            'aluguel_por_novo_módulo': 950.0
        },
        'propriedade': {
            'módulos_init': 0,
            'custo_por_módulo': 75000.0,
            'receita_por_módulo': 4500.0,
            'manutenção_por_módulo': 200.0,
            'monthly_land_plot_parcel': 200.0,
            'land_total_value': 0.0,
            'land_down_payment_pct': 20.0,
            'land_installments': 120,
            'land_interest_rate': 8.0,
            'land_appreciation_rate': 3.0
        },
        'global': {
            'anos': 15,
            'max_withdraw_value': 50000.0,
            'taxa_de_correção_geral': 5.0,
            'taxa_de_apreciação_da_terra': 3.0,
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
    st.session_state.selected_strategy = 'comprar'

# ---------------------------
# Header (fiel à imagem)
# ---------------------------
with st.container():
    st.markdown("""
        <div class="cabeçalho">
            <h1 class="header-title">📊 Simulador Financeiro de Investimentos</h1>
            <p class="header-sub">Simule cenários de crescimento e otimize seus investimentos em módulos</p>
        </div>
    """, unsafe_allow_html=Verdadeiro)

# ---------------------------
# Abas (fiel à imagem: Configuração, Transações, Resultados, Dados)
# ---------------------------
tab_config, tab_transactions, tab_results, tab_data = st.tabs([
    "⚙️ Configuração",
    "💰 Transações",
    "📈 Resultados",
    "📋 Dados"
])

# ---------------------------
# CONFIGURAÇÕES (aba)
# ---------------------------
with tab_config:
    cfg = st.session_state.config
    st.markdown("<h3 class='section-title'>⚙️ Configuração Inicial</h3>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        cfg['alugado']['modules_init'] = st.number_input(
            "Número inicial de módulos", 0, 1000, valor=int(cfg['rented']['modules_init']),
            chave="config_modules_init"
        )
    with c2:
        cfg['alugado']['custo_por_módulo'] = st.number_input(
            "Valor por Módulo (R$)", 0,0, 1000000,0, valor=cfg['rented']['cost_per_module'],
            formato="%.2f", chave="config_cost_per_module"
        )

    # Cartão de Investimento Inicial Total (laranja)
    invest_inicial = computa_total_de_investimento_inicial(cfg)
    st.markdown(f"""
        <div class="invest-strip">
            <span>Investimento Inicial Total:</span>
            <span>{fmt_brl(invest_inicial)}</span>
        </div>
    """, unsafe_allow_html=Verdadeiro)

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        cfg['alugado']['receita_por_módulo'] = st.number_input(
            "Receita Mensal por Módulo (R$)", 0.0, 100000.0, valor=cfg['rented']['revenue_per_module'],
            formato="%.2f", chave="config_revenue_per_module"
        )
    with c2:
        cfg['alugado']['manutenção_por_módulo'] = st.number_input(
            "Custo Manutenção Mensal por Módulo (R$)", 0.0, 10000.0, valor=cfg['rented']['maintenance_per_module'],
            formato="%.2f", chave="config_maintenance_per_module"
        )

    c1, c2 = st.columns(2)
    with c1:
        cfg['alugado']['valor_do_aluguel'] = st.number_input(
            "Aluguel Mensal Terreno (R$)", 0.0, 100000.0, valor=cfg['rented']['rent_value'],
            formato="%.2f", chave="config_rent_value"
        )
    with c2:
        cfg['alugado']['aluguel_por_novo_módulo'] = st.number_input(
            "Mês de Início do Aluguel", 0, 1000, valor=int(cfg['rented']['rent_per_new_module']),
            chave="config_rent_start_month"
        )

    st.markdown("<h3 class='section-title'>🏡 Financiamento de Terreno Próprio</h3>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        cfg['propriedade']['valor_total_do_terreno'] = st.number_input(
            "Valor Total do Terreno (R$)", 0.0, 10000000.0, valor=cfg['owned']['land_total_value'],
            formato="%.2f", chave="config_land_total_value"
        )
    with c2:
        cfg['propriedade']['land_down_payment_pct'] = st.number_input(
            "Entrada (%)", 0.0, 100.0, valor=cfg['owned']['land_down_payment_pct'],
            formato="%.1f", chave="config_land_down_payment_pct"
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        cfg['propriedade']['land_installments'] = st.number_input(
            "Número de Parcelas", 1, 480, valor=int(cfg['owned']['land_installments']),
            chave="config_land_installments"
        )
    with c2:
        cfg['propriedade']['land_interest_rate'] = st.number_input(
            "Taxa de Juros Anual (%)", 0.0, 50.0, valor=cfg['owned']['land_interest_rate'],
            formato="%.1f", chave="config_land_interest_rate"
        )
    with c3:
        cfg['propriedade']['land_appreciation_rate'] = st.number_input(
            "Valorização Anual do Terreno (%)", 0.0, 50.0, valor=cfg['owned']['land_appreciation_rate'],
            formato="%.1f", chave="config_land_appreciation_rate"
        )

    # Resumo do financiamento
    if cfg['owned']['land_total_value'] > 0:
        valor_entrada = cfg['owned']['land_total_value'] * (cfg['owned']['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg['owned']['land_total_value'] - valor_entrada
        st.markdown(f"""
            <div class="cartão" estilo="preenchimento: 0,75rem;">
                <div style="display: flex; justify-content: espaço-entre; margem-inferior: 0,25rem;">
                    <span>Valor da Entrada:</span>
                    <span>{fmt_brl(valor_entrada)}</span>
                </div>
                <div style="display: flex; justify-content: espaço-entre;">
                    <span>Valor Financiado:</span>
                    <span>{fmt_brl(valor_financiado)}</span>
                </div>
            </div>
        """, unsafe_allow_html=Verdadeiro)

    # Botão de simular
    if st.button("🚀 Executar Simulação", type="primary", use_container_width=True):
        with st.spinner("Calculando projeção..."):
            cache_key = chave_de_cache_de_computação(st.session_state.config)
            st.session_state.simulation_df = simular(st.session_state.config, 'comprar', cache_key)
        st.success("Simulação concluída!")

# ---------------------------
# TRANSAÇÕES (aba)
# ---------------------------
with tab_transactions:
    st.markdown("<h3 class='section-title'>💰 Gerenciador de Transações</h3>", unsafe_allow_html=True)
    cfg = st.session_state.config
    g = cfg['global']

    st.markdown("#### 💸 Contribuições de Investimento")
    colA, colB = st.columns([1,2])
    with colA:
        ap_mes = st.number_input("Mês", 1, g['anos']*12, 1, key="trans_aporte_mes")
    with colB:
        ap_val = st.number_input("Valor (R$)", 0.0, key="trans_aporte_valor")
    if st.button("➕ Adicionar Aporte", key="btn_trans_add_aporte"):
        g['aportes'].append({"mes": ap_mes, "valor": ap_val})
        st.rerun()
    if g['aportes']:
        st.markdown("**Aportes agendados:**")
        for i, a in enumerate(g['aportes']):
            cA, cB, cC = st.colunas([3,2,1])
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
        g['retiradas'].append({"mes": r_mes, "porcentagem": r_pct})
        st.rerun()
    if g['retiradas']:
        st.markdown("**Regras ativas:**")
        for i, r_ in enumerate(g['retiradas']):
            cA, cB, cC = st.colunas([3,2,1])
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
        g['fundos'].append({"mês": f_mes, "porcentagem": f_pct})
        st.rerun()
    if g['fundos']:
        st.markdown("**Regras ativas:**")
        for i, f in enumerate(g['fundos']):
            cA, cB, cC = st.colunas([3,2,1])
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
        resumo = calcular_métricas_de_resumo(df)

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
            fig = go.Figura()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Patrimônio Líquido'], mode='lines', name='Patrimônio Líquido', line=dict(color=SUCCESS_COLOR, width=3)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Investimento Total Acumulado'], mode='lines', name='Investimento Total', line=dict(color=SECONDARY_COLOR, width=2, dash='dash')))
            st.plotly_chart(apply_plot_theme(fig, "Evolução do Investimento"), use_container_width=True)
        with g2:
            fig = go.Figura()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Receita'], mode='lines', name='Receita', line=dict(color=SUCCESS_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Gastos'], modo='linhas', nome='Gastos', linha=dict(cor=COLOR_DO_PERIGO, largura=2)))
            st.plotly_chart(apply_plot_theme(fig, "Receita vs Gastos"), use_container_width=True)

        # Módulos por ano
        gp = df.groupby('Ano', as_index=False).agg({
            'Módulos Próprios':'last',
            'Módulos Alugados':'last',
            'Módulos Ativos':'last'
        })
        fig_bar = go.Figura()
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
            st.session_state[state_key] = {c: (c em default_cols) para c em all_cols}

        st.markdown("Selecione as colunas para exibir:")
        cols_to_show = []
        grade = st.columns(3)
        para idx, c em enumerate(all_cols):
            com grade[idx % 3]:
                tkey = f"toggle_{slug(c)}_{state_key}"
                st.session_state[chave_de_estado][c] = st.toggle(c, valor=st.session_state[chave_de_estado][c], chave=tkey)
                se st.session_state[chave_de_estado][c]:
                    cols_to_show.append(c)

        se não cols_to_show:
            st.warning("Selecione ao menos uma coluna.")
        outro:
            df_disp = df.copy()
            para coluna em (MONEY_COLS & set(df_disp.columns)):
                df_disp[col] = df_disp[col].apply(lambda x: fmt_brl(x) se pd.notna(x) senão "-")
            st.dataframe(df_disp[cols_to_show], use_container_width=True, hide_index=True)

        excel_bytes = df_para_excel_bytes(df)
        st.botão_de_download(
            "📥 Baixar Relatório Completo (Excel)",
            dados=bytes_excel,
            nome_do_arquivo="relatorio_simulacao.xlsx",
            mime="aplicativo/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
