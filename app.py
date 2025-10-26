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

# --- ESTADO DA SESSÃO ---
if 'config' not in st.session_state:
    st.session_state.config = {
        'global': {
            'years': 10, 
            'general_correction_rate': 3.0, 
            'max_withdraw_value': 0.0, 
            'land_appreciation_rate': 3.0, 
            'contributions': [], 
            'withdrawals': [], 
            'reserve_funds': [], 
            'reinvestment_strategy': 'buy',
            'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0,
            'maintenance_per_module': 200.0,
            'modules_init': 1,
        },
        'rented': {
            'rent_value': 750.0,
            'rent_per_new_module': 950.0
        },
        'owned': {
            'land_total_value': 0.0, 
            'land_down_payment_pct': 0.0, 
            'land_installments': 1, 
            'land_interest_rate': 8.0,
            'monthly_land_plot_parcel': 0.0,
        },
        'strategy': {
            'land_strategy': 'owned'
        }
    }
if 'simulation_df' not in st.session_state:
    st.session_state.simulation_df = pd.DataFrame()
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = pd.DataFrame()
if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = 'buy'
if 'config_changed' not in st.session_state:
    st.session_state.config_changed = False

# --- PALETA DE CORES (fiel à imagem) ---
PRIMARY_COLOR   = "#FF9234"      # Laranja vibrante do header
SECONDARY_COLOR = "#6C757D"      # Cinza escuro dos textos secundários
SUCCESS_COLOR   = "#28A745"      # Verde sucesso
DANGER_COLOR    = "#DC3545"      # Vermelho erro
WARNING_COLOR   = "#FFC107"      # Alerta amarelo
INFO_COLOR      = "#17A2B8"      # Informações azuis
APP_BG          = "#FFFFFF"      # Fundo branco da página
CARD_COLOR      = "#FFFFFF"      # Fundo blanco dos cards
TEXT_COLOR      = "#212529"      # Texto escuro principal
MUTED_TEXT_COLOR= "#6C757D"      # Texto cinza secundário
TABLE_BORDER_COLOR = "#E9ECEF"
CHART_GRID_COLOR  = "#E9ECEF"

# --- COLUNAS PARA FORMATAÇÃO ---
MONEY_COLS = {
    "Receita","Manutenção","Aluguel","Parcela Terreno Inicial","Parcelas Terrenos (Novos)","Gastos",
    "Aporte","Fundo (Mês)","Retirada (Mês)","Caixa (Final Mês)","Investimento Total Acumulado",
    "Fundo Acumulado","Retiradas Acumuladas","Patrimônio Líquido","Juros Terreno Inicial",
    "Amortização Terreno Inicial","Equity Terreno Inicial","Valor de Mercado Terreno",
    "Patrimônio Terreno","Juros Acumulados","Amortização Acumulada","Desembolso Total",
    "Aluguel Acumulado","Parcelas Novas Acumuladas",
    # Novos KPIs
    "Dívida Futura Total", "Investimento em Terrenos", "Valor de Mercado Total"
}
COUNT_COLS = {"Mês","Ano","Módulos Ativos","Módulos Alugados","Módulos Próprios","Módulos Comprados no Ano", "Terrenos Adquiridos"}

# ---------------------------
# Helpers
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

def render_kpi_card(title, value, bg_color=PRIMARY_COLOR, icon=None, subtitle=None, dark_text=False):
    icon_html = f"<div style='font-size: 2rem; margin-bottom: 0.5rem;'>{icon}</div>" if icon else ""
    subtitle_html = f"<div class='kpi-card-subtitle'>{subtitle}</div>" if subtitle else ""
    txt_color = "#0F172A" if dark_text else "#FFFFFF"
    st.markdown(f"""
        <div class="kpi-card-modern" style="background:{bg_color}; color:{txt_color};">
            {icon_html}
            <div class="kpi-card-value-modern">{value}</div>
            <div class="kpi-card-title-modern">{title}</div>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)

def render_report_metric(title, value):
    """Função auxiliar para o cartão de métricas de relatório"""
    if isinstance(value, (int, np.integer)):
        formatted_value = f"{value:,}"
    else:
        formatted_value = fmt_brl(value)
    st.markdown(f"""
        <div class="report-metric-card">
            <div class="report-metric-title">{title}</div>
            <div class="report-metric-value">{formatted_value}</div>
        </div>
    """, unsafe_allow_html=True)

def calculate_summary_metrics(df):
    summary = {"roi_pct": 0, "break_even_month": "N/A", "total_investment": 0, "net_profit": 0}
    if df.empty:
        return summary
    final = df.iloc[-1]
    total_investment = final['Investimento Total Acumulado']
    summary["total_investment"] = total_investment
    if total_investment > 0:
        # Patrimônio Líquido Final deve ser a soma do tatal investido em módulos com o total investido em terrenos.
        # PL = Ativos (Módulos + Caixa + Fundo + Valor de Mercado Total) - Passivos (Dívida Futura Total)
        net_profit = final['Patrimônio Líquido'] - total_investment
        summary["roi_pct"] = (net_profit / total_investment) * 100
        summary["net_profit"] = net_profit
    break_even_df = df[df['Patrimônio Líquido'] >= df['Investimento Total Acumulado']]
    if not break_even_df.empty:
        break_even_month = int(break_even_df.iloc[0]['Mês'])
        summary["break_even_month"] = f"Mês {break_even_month}"
    return summary

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Simulacao_Mensal")
        wb, ws = writer.book, writer.sheets["Simulacao_Mensal"]
        money_fmt = wb.add_format({"num_format": "R$ #,##0.00"})
        for i, col in enumerate(df.columns):
            width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            fmt = money_fmt if col in MONEY_COLS else None
            ws.set_column(i, i, width, fmt)
    return output.getvalue()

def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:60]

def apply_plot_theme(fig, title=None, h=420):
    fig.update_layout(
        title=dict(text=title or fig.layout.title.text, x=0.5, xanchor='center', font=dict(size=16, color=TEXT_COLOR)),
        height=h, margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor='rgba(255,255,255,0.85)', bordercolor=TABLE_BORDER_COLOR, borderwidth=1,
                    font=dict(color=TEXT_COLOR)),
        plot_bgcolor=CARD_COLOR, paper_bgcolor=CARD_COLOR, font=dict(color=TEXT_COLOR),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR)),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=TABLE_BORDER_COLOR, tickfont=dict(color=MUTED_TEXT_COLOR))
    )
    return fig

def compute_cache_key(cfg: dict) -> str:
    payload = json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()

def compute_initial_investment_total(cfg):
    g = cfg['global']; o = cfg['owned']
    # Investimento inicial = (Modulos iniciais * Custo por modulo) + Entrada do terreno para TODOS os modulos iniciais (se comprado)
    total = g['modules_init'] * g['cost_per_module']
    if cfg['strategy']['land_strategy'] in ['owned', 'alternate'] and o.get('land_total_value', 0) > 0:
        # Valor total do terreno para TODOS os modulos iniciais
        valor_total_terreno = o['land_total_value'] * g['modules_init']
        total += valor_total_terreno * (o.get('land_down_payment_pct', 0) / 100.0)
    return total

# ---------------------------
# Funções de Simulação
# ---------------------------
@st.cache_data(show_spinner="Calculando simulação...", max_entries=10, ttl=3600)
def run_simulation(cfg: dict):
    cfg_global = cfg['global']
    cfg_owned = cfg['owned']
    cfg_rented = cfg['rented']
    cfg_strategy = cfg['strategy']

    # Parâmetros Globais
    months = cfg_global['years'] * 12
    correction_rate_pct = cfg_global['general_correction_rate'] / 100.0
    land_appreciation_rate_pct = cfg_global['land_appreciation_rate'] / 100.0
    reinvestment_strategy = cfg_global['reinvestment_strategy']
    
    # Valores por Módulo (Globais)
    custo_modulo_atual = cfg_global['cost_per_module']
    receita_p_mod = cfg_global['revenue_per_module']
    manut_p_mod = cfg_global['maintenance_per_module']
    
    # Parâmetros de Terreno Alugado
    aluguel_p_mod = cfg_rented['rent_value']
    aluguel_p_novo_mod = cfg_rented['rent_per_new_module']
    
    # Parâmetros de Terreno Comprado
    valor_compra_terreno = cfg_owned.get('land_total_value', 0.0)
    parcela_p_novo_terreno = cfg_owned.get('monthly_land_plot_parcel', 0.0)
    taxa_juros_anual = cfg_owned.get('land_interest_rate', 8.0) / 100.0
    taxa_juros_mensal = taxa_juros_anual / 12
    
    # Estado Inicial
    modules_init = cfg_global['modules_init']
    
    # Inicialização de variáveis
    modules_owned = 0
    modules_rented = 0
    
    # Variáveis para Terrenos Adquiridos (Novos KPIs)
    terrenos_adquiridos = 0 # Contagem total de terrenos (inicial + novos)
    investimento_em_terrenos = 0.0 # Soma das entradas + amortização
    
    # Lista para gerenciar os financiamentos de terrenos (inicial + novos)
    # Cada item é um dicionário: {'valor_total', 'saldo_devedor', 'parcelas_restantes', 'parcela_mensal', 'taxa_juros_mensal', 'amortizacao_mensal', 'mes_aquisicao', 'valor_original_terreno'}
    financiamentos_ativos = []
    
    # Distribuição inicial dos módulos baseada na estratégia
    land_strategy = cfg_strategy['land_strategy']
    if land_strategy == 'owned':
        modules_owned = modules_init
    elif land_strategy == 'rented':
        modules_rented = modules_init
    elif land_strategy == 'alternate':
        if valor_compra_terreno > 0:
            modules_owned = modules_init
        else:
            modules_rented = modules_init
    
    # A quantidade de terrenos deve ser igual à quantidade de módulos próprios
    terrenos_adquiridos = modules_owned
    
    caixa = 0.0
    investimento_total = 0.0
    historical_value_owned = modules_owned * custo_modulo_atual
    historical_value_rented = modules_rented * custo_modulo_atual
    
    investimento_total += historical_value_owned + historical_value_rented
    
    # Financiamento Terreno Inicial (apenas se a estratégia inicial for 'owned' ou 'alternate' e houver valor de terreno)
    juros_acumulados = 0.0
    amortizacao_acumulada = 0.0
    aluguel_acumulado = 0.0
    parcelas_novas_acumuladas = 0.0
    
    aluguel_mensal_corrente = modules_rented * aluguel_p_mod
    
    # A parcela por módulo próprio é a parcela calculada na interface
    parcelas_terrenos_novos_mensal_corrente = modules_owned * parcela_p_novo_terreno

    if land_strategy in ['owned', 'alternate'] and valor_compra_terreno > 0:
        # Valor total do terreno para TODOS os módulos iniciais
        valor_total_terreno_inicial = valor_compra_terreno * modules_init
        valor_entrada_terreno = valor_total_terreno_inicial * (cfg_owned.get('land_down_payment_pct', 0.0) / 100.0)
        valor_financiado = valor_total_terreno_inicial - valor_entrada_terreno
        
        amortizacao_mensal = 0.0
        
        if cfg_owned['land_installments'] > 0:
            amortizacao_mensal = valor_financiado / cfg_owned['land_installments']
            
            # Adiciona UM ÚNICO financiamento para todos os módulos iniciais
            financiamentos_ativos.append({
                'valor_total': valor_total_terreno_inicial,
                'saldo_devedor': valor_financiado,
                'parcelas_restantes': cfg_owned['land_installments'],
                'parcela_mensal': amortizacao_mensal + (valor_financiado * taxa_juros_mensal), # Parcela inicial (Amortização + Juros)
                'taxa_juros_mensal': taxa_juros_mensal,
                'amortizacao_mensal': amortizacao_mensal,
                'mes_aquisicao': 0, # Mês 0 para o inicial
                'valor_original_terreno': valor_total_terreno_inicial,
                'quantidade_modulos': modules_init  # Rastreia quantos módulos estão associados a este financiamento
            })
            
        investimento_total += valor_entrada_terreno
        investimento_em_terrenos += valor_entrada_terreno
    
    fundo_ac = 0.0
    retiradas_ac = 0.0
    rows = []
    
    # Variáveis anuais para correção
    custo_modulo_atual_corrigido = custo_modulo_atual
    receita_p_mod_corrigida = receita_p_mod
    manut_p_mod_corrigida = manut_p_mod
    aluguel_p_mod_corrigido = aluguel_p_mod
    aluguel_p_novo_mod_corrigido = aluguel_p_novo_mod
    parcela_p_novo_terreno_corrigido = parcela_p_novo_terreno
    
    # Variável para acumular o lucro anual para o reinvestimento
    lucro_acumulado_anual = 0.0

    for m in range(1, months + 1):
        # Receita e Manutenção usam os valores corrigidos e são aplicados a TODOS os módulos
        receita = (modules_owned + modules_rented) * receita_p_mod_corrigida
        manut   = (modules_owned + modules_rented) * manut_p_mod_corrigida
        novos_modulos_comprados = 0
        
        # Aportes
        aporte_mes = sum(a.get('valor', 0.0) for a in cfg_global['contributions'] if a.get('mes') == m)
        caixa += aporte_mes
        investimento_total += aporte_mes
        
        # --- Pagamento dos Financiamentos Ativos ---
        parcela_terreno_mensal_total = 0.0
        juros_terreno_mensal_total = 0.0
        amortizacao_terreno_mensal_total = 0.0
        
        # Gastos Operacionais (Aluguel + Parcelas de Terrenos Novos)
        # parcelas_terrenos_novos_mensal_corrente representa o custo do terreno para os módulos próprios (owned)
        gastos_operacionais = aluguel_mensal_corrente + parcelas_terrenos_novos_mensal_corrente
        lucro_operacional = receita - manut - gastos_operacionais
        
        # Processa todos os financiamentos ativos
        for fin in financiamentos_ativos:
            if fin['saldo_devedor'] > 0 and fin['parcelas_restantes'] > 0:
                juros_terreno_mes = fin['saldo_devedor'] * fin['taxa_juros_mensal']
                amortizacao_terreno_mes = fin['amortizacao_mensal']
                parcela_terreno_mes = juros_terreno_mes + amortizacao_terreno_mes
                
                # Acumula os totais do mês
                parcela_terreno_mensal_total += parcela_terreno_mes
                juros_terreno_mensal_total += juros_terreno_mes
                amortizacao_terreno_mensal_total += amortizacao_terreno_mes
                
                # Atualiza o saldo e parcelas
                fin['saldo_devedor'] -= amortizacao_terreno_mes
                fin['parcelas_restantes'] -= 1
                
                # Acumuladores globais
                juros_acumulados += juros_terreno_mes
                amortizacao_acumulada += amortizacao_terreno_mes
                
                # Investimento em terrenos (apenas a amortização)
                investimento_em_terrenos += amortizacao_terreno_mes
        
        # O equity do terreno inicial é a amortização acumulada
        equity_terreno_inicial = amortizacao_acumulada
        
        # Remove os financiamentos quitados (não é necessário, mas é bom para limpeza)
        financiamentos_ativos = [fin for fin in financiamentos_ativos if fin['saldo_devedor'] > 0 and fin['parcelas_restantes'] > 0]

        caixa += lucro_operacional
        
        # O pagamento das parcelas do terreno é um gasto, já subtraído do caixa
        caixa -= parcela_terreno_mensal_total
        
        # Distribuição (Retiradas + Fundo) limitada ao lucro e ao caixa
        fundo_mes_total = 0.0
        retirada_mes_efetiva = 0.0
        
        # 1. Calcular a base de lucro para distribuição (Lucro Operacional - Parcela Terreno Total)
        lucro_distribuivel = lucro_operacional - parcela_terreno_mensal_total
        lucro_acumulado_anual += lucro_distribuivel # Acumula o lucro para o reinvestimento anual
        
        if lucro_distribuivel > 0:
            base = lucro_distribuivel
            
            # Calcular retiradas e fundo potenciais
            retirada_potencial = sum(base * (r['percentual'] / 100.0) for r in cfg_global['withdrawals'] if m >= r['mes'])
            fundo_potencial    = sum(base * (f['percentual'] / 100.0) for f in cfg_global['reserve_funds'] if m >= r['mes'])
            
            # Aplicar limite máximo de retirada
            if cfg_global['max_withdraw_value'] > 0 and retirada_potencial > cfg_global['max_withdraw_value']:
                retirada_mes_efetiva = cfg_global['max_withdraw_value']
                fundo_mes_total = fundo_potencial
            else:
                retirada_mes_efetiva = retirada_potencial
                fundo_mes_total = fundo_potencial
            
            total_distrib = retirada_mes_efetiva + fundo_mes_total
            
            # 2. Limitar a distribuição ao caixa disponível (após todas as entradas e saídas)
            caixa_apos_operacional = caixa 
            
            if total_distrib > caixa_apos_operacional:
                if caixa_apos_operacional > 0:
                    proporcao = caixa_apos_operacional / total_distrib
                    retirada_mes_efetiva *= proporcao
                    fundo_mes_total *= proporcao
                else:
                    retirada_mes_efetiva = 0.0
                    fundo_mes_total = 0.0
        
        # 3. Atualizar o caixa e acumuladores
        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac += fundo_mes_total
        
        # Acumuladores de desembolso corrente
        aluguel_acumulado += aluguel_mensal_corrente
        parcelas_novas_acumuladas += parcelas_terrenos_novos_mensal_corrente
        
        # Reinvestimento anual (baseado no lucro acumulado anual)
        if m % 12 == 0:
            
            caixa_para_reinvestir = lucro_acumulado_anual
            lucro_acumulado_anual = 0.0 # Reseta o lucro acumulado
            
            alvo = land_strategy
            if land_strategy == 'alternate':
                alvo = 'owned' if ((m // 12) % 2 == 0) else 'rented'
                
            custo_modulo = custo_modulo_atual_corrigido
            
            # Custo total para comprar 1 módulo + 1 terreno (entrada)
            custo_total_owned_unitario = custo_modulo + (valor_compra_terreno * (cfg_owned.get('land_down_payment_pct', 0.0) / 100.0) / modules_init)
            
            if alvo == 'owned' and custo_total_owned_unitario > 0:
                # Quantidade de módulos que podem ser comprados
                novos_modulos_comprados = int(caixa_para_reinvestir // custo_total_owned_unitario)
            elif alvo == 'rented' and custo_modulo > 0:
                novos_modulos_comprados = int(caixa_para_reinvestir // custo_modulo)
            else:
                novos_modulos_comprados = 0
            
            if novos_modulos_comprados > 0:
                
                if alvo == 'owned':
                    custo_da_compra = novos_modulos_comprados * custo_total_owned_unitario
                    
                    # Custo do módulo
                    custo_modulos = novos_modulos_comprados * custo_modulo
                    historical_value_owned += custo_modulos
                    modules_owned += novos_modulos_comprados
                    
                    # Custo da entrada do terreno
                    valor_entrada_novo_terreno = novos_modulos_comprados * (valor_compra_terreno * (cfg_owned.get('land_down_payment_pct', 0.0) / 100.0) / modules_init)
                    
                    # O reinvestimento é feito com o lucro, o caixa é ajustado
                    caixa -= custo_da_compra
                    investimento_total += custo_da_compra
                    investimento_em_terrenos += valor_entrada_novo_terreno
                    
                    # Adiciona a parcela mensal do terreno para os novos módulos comprados
                    parcelas_terrenos_novos_mensal_corrente += novos_modulos_comprados * parcela_p_novo_terreno_corrigido
                    
                    # Adiciona os novos financiamentos à lista (1 financiamento por módulo/terreno)
                    valor_unitario_terreno = valor_compra_terreno / modules_init
                    valor_unitario_financiado = valor_unitario_terreno * (1 - (cfg_owned.get('land_down_payment_pct', 0.0) / 100.0))
                    
                    if cfg_owned['land_installments'] > 0 and valor_unitario_financiado > 0:
                        amortizacao_mensal_novo = valor_unitario_financiado / cfg_owned['land_installments']
                        
                        for _ in range(novos_modulos_comprados):
                            financiamentos_ativos.append({
                                'valor_total': valor_unitario_terreno,
                                'saldo_devedor': valor_unitario_financiado,
                                'parcelas_restantes': cfg_owned['land_installments'],
                                'parcela_mensal': amortizacao_mensal_novo + (valor_unitario_financiado * taxa_juros_mensal),
                                'taxa_juros_mensal': taxa_juros_mensal,
                                'amortizacao_mensal': amortizacao_mensal_novo,
                                'mes_aquisicao': m,
                                'valor_original_terreno': valor_unitario_terreno
                            })
                        terrenos_adquiridos += novos_modulos_comprados
                        
                else: # 'rented'
                    custo_da_compra = novos_modulos_comprados * custo_modulo
                    historical_value_rented += custo_da_compra
                    modules_rented += novos_modulos_comprados
                    
                    caixa -= custo_da_compra
                    investimento_total += custo_da_compra
                    
                    # Adiciona o aluguel mensal para os novos módulos alugados
                    aluguel_mensal_corrente += novos_modulos_comprados * aluguel_p_novo_mod_corrigido
            
            # Correção anual
            correction_factor = 1 + correction_rate_pct
            custo_modulo_atual_corrigido  *= correction_factor
            receita_p_mod_corrigida       *= correction_factor
            manut_p_mod_corrigida         *= correction_factor
            aluguel_mensal_corrente       *= correction_factor
            parcelas_terrenos_novos_mensal_corrente *= correction_factor
            aluguel_p_mod_corrigido       *= correction_factor
            aluguel_p_novo_mod_corrigido  *= correction_factor
            parcela_p_novo_terreno_corrigido *= correction_factor
            
            # Corrige o valor total de cada financiamento ativo
            for fin in financiamentos_ativos:
                # O valor total (original) do terreno é corrigido
                fin['valor_total'] *= (1 + land_appreciation_rate_pct)
                # A taxa de juros não é corrigida anualmente, apenas o valor do terreno
                
        # --- Cálculo dos Novos KPIs ---
        divida_futura_total = 0.0
        valor_mercado_total = 0.0
        
        for fin in financiamentos_ativos:
            # Valor de Mercado Total (apreciação mensal)
            valor_mercado_total += fin['valor_total'] * ((1 + land_appreciation_rate_pct) ** (1/12))
            
            # Dívida Futura Total (Saldo Devedor + Juros Futuros)
            saldo_devedor_atual = fin['saldo_devedor']
            
            if saldo_devedor_atual > 0:
                # Juros futuros: (Parcelas Restantes * Parcela Mensal) - Saldo Devedor
                # Usando a fórmula simplificada: saldo_devedor * taxa_mensal * parcelas_restantes
                # Simplificação: Dívida Futura = Saldo Devedor + Juros sobre o Saldo Devedor (para o restante das parcelas)
                # O cálculo da dívida futura já considera os juros futuros
                divida_futura_total += saldo_devedor_atual + (saldo_devedor_atual * fin['taxa_juros_mensal'] * fin['parcelas_restantes'])
        
        # Patrimônio
            # Patrimonio Líquido = Ativos (Módulos + Caixa + Fundo + Valor de Mercado Total) - Passivos (Dívida Futura Total)
            ativos  = historical_value_owned + historical_value_rented + caixa + fundo_ac + valor_mercado_total
            passivos= divida_futura_total
            patrimonio_liquido = ativos - passivos
        
        # O Investimento Total Acumulado é a soma dos custos de aquisição (módulos e entradas de terreno)
        desembolso_total = investimento_total + juros_acumulados + aluguel_acumulado + parcelas_novas_acumuladas
        gastos_totais = manut + aluguel_mensal_corrente + juros_terreno_mensal_total + parcelas_terrenos_novos_mensal_corrente
        
        # A quantidade de terrenos é igual à quantidade de módulos próprios
        terrenos_adquiridos = modules_owned
        
        rows.append({
            "Mês": m,
            "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules_owned + modules_rented,
            "Módulos Alugados": modules_rented,
            "Módulos Próprios": modules_owned,
            "Receita": receita,
            "Manutenção": manut,
            "Aluguel": aluguel_mensal_corrente,
            "Juros Terreno Inicial": juros_terreno_mensal_total,
            "Amortização Terreno Inicial": amortizacao_terreno_mensal_total,
            "Parcela Terreno Inicial": parcela_terreno_mensal_total,
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
            "Valor de Mercado Terreno": valor_mercado_total,
            "Patrimônio Terreno": valor_mercado_total - divida_futura_total,
            "Juros Acumulados": juros_acumulados,
            "Amortização Acumulada": amortizacao_acumulada,
            "Aluguel Acumulado": aluguel_acumulado,
            "Parcelas Novas Acumuladas": parcelas_novas_acumuladas,
            "Desembolso Total": desembolso_total,
            # Novos KPIs
            "Dívida Futura Total": divida_futura_total,
            "Investimento em Terrenos": investimento_em_terrenos,
            "Terrenos Adquiridos": terrenos_adquiridos,
            "Valor de Mercado Total": valor_mercado_total
        })
    
    return pd.DataFrame(rows)

# ---------------------------
# Config da página + CSS (fiel à imagem)
# ---------------------------
st.set_page_config(page_title="Simulador Financeiro de Investimentos", layout="wide", initial_sidebar_state="collapsed")
st.markdown(f"""
    <style>
        .main .block-container {{ padding: 0 1.25rem 2rem; max-width: 1400px; }}
        .stApp {{ background: {APP_BG}; }}
        h1, h2, h3, h4, h5, h6 {{ color: {TEXT_COLOR}; font-weight: 700; }}
        /* Header */
        .header {{
            background: linear-gradient(90deg, #FF9234 0%, #FFC107 100%);
            color: white; padding: 1.5rem 1.2rem; text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header-title {{
            font-size: 2rem; font-weight: 800; margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .header-sub {{
            font-size: 1rem; opacity: .95; margin-top: .35rem;
        }}
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0;
            background-color: #F8F9FA;
            border-radius: 8px;
            padding: 0.5rem;
            margin-bottom: 1rem;
            border: 1px solid {TABLE_BORDER_COLOR};
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: #FFFFFF;
            border: 1px solid {TABLE_BORDER_COLOR};
            border-radius: 6px;
            padding: 0.5rem 1rem;
            margin: 0;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background-color: #E9ECEF;
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border-color: {PRIMARY_COLOR};
        }}
        /* Cards */
        .card {{
            background: {CARD_COLOR}; border-radius: 8px; padding: 1.25rem; border: 1px solid {TABLE_BORDER_COLOR}; margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .section-title {{
            font-weight: 800; margin: .25rem 0 .75rem; color: {TEXT_COLOR}; font-size: 1.1rem;
        }}
        /* Input fields */
        .stTextInput input, .stNumberInput input {{
            background: {CARD_COLOR} !important; color: {TEXT_COLOR} !important; border: 1px solid {TABLE_BORDER_COLOR} !important;
            border-radius: 6px;
        }}
        /* Buttons */
        .stButton > button {{
            border-radius: 6px; border: 1px solid {PRIMARY_COLOR};
            background-color: {PRIMARY_COLOR}; color: white;
            padding: 8px 16px; font-weight: 700; transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            background-color: #FF7B00; border-color: #FF7B00;
        }}
        .invest-strip {{
            background: linear-gradient(90deg, #FF9234, #FFC107);
            color: white; border-radius: 8px; padding: .6rem 1rem; font-weight: 800; display:flex; justify-content:space-between; align-items:center;
            margin-bottom: 1rem;
        }}
        /* Table */
        [data-testid="stDataFrame"] th {{
            background-color: #F8F9FA !important; color: {TEXT_COLOR} !important; font-weight: 600;
        }}
        [data-testid="stDataFrame"] td {{
            color: {TEXT_COLOR};
        }}
        /* KPI Cards Modern */
        .kpi-card-modern {{
            border-radius: 18px; padding: 1.2rem 1.1rem; height: 100%; text-align: center;
            transition: transform .25s ease;
        }}
        .kpi-card-modern:hover {{ transform: translateY(-4px); }}
        .kpi-card-title-modern {{ font-size: 0.8rem; opacity: 0.8; font-weight: 600; margin-top: 0.2rem; }}
        .kpi-card-value-modern {{ font-size: 1.5rem; font-weight: 800; line-height: 1.2; }}
        /* Report Metric Card */
        .report-metric-card {{
            background: #F8F9FA; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;
            border-left: 4px solid {PRIMARY_COLOR};
        }}
        .report-metric-title {{ font-size: 0.8rem; color: {MUTED_TEXT_COLOR}; font-weight: 600; }}
        .report-metric-value {{ font-size: 1.1rem; color: {TEXT_COLOR}; font-weight: 700; }}
        /* Custom list style for contributions/withdrawals */
        .list-item {{
            background: #F8F9FA; border-radius: 4px; padding: 0.5rem; margin-bottom: 0.5rem;
            display: flex; justify-content: space-between; align-items: center;
            font-size: 0.9rem;
        }}
        .list-item-value {{ font-weight: 700; color: {PRIMARY_COLOR}; }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Estado Inicial
# ---------------------------
def get_default_config():
    # Retorna a configuração padrão com os novos campos globais
    return {
        'global': {
            'years': 10, 
            'general_correction_rate': 3.0, 
            'max_withdraw_value': 0.0, 
            'land_appreciation_rate': 3.0, 
            'contributions': [], 
            'withdrawals': [], 
            'reserve_funds': [], 
            'reinvestment_strategy': 'buy',
            'cost_per_module': 75000.0,
            'revenue_per_module': 4500.0,
            'maintenance_per_module': 200.0,
            'modules_init': 1,
        },
        'rented': {
            'rent_value': 750.0,
            'rent_per_new_module': 950.0
        },
        'owned': {
            'land_total_value': 100000.0, 
            'land_down_payment_pct': 20.0, 
            'land_installments': 120, 
            'land_interest_rate': 8.0,
            'monthly_land_plot_parcel': 0.0, # Será calculado na interface
        },
        'strategy': {
            'land_strategy': 'owned'
        }
    }

# ---------------------------
# Estrutura do Aplicativo Streamlit
# ---------------------------
st.markdown("<div class='header'><div class='header-title'>Simulador Financeiro de Investimentos</div><div class='header-sub'>Análise de Viabilidade de Projetos de Geração de Energia</div></div>", unsafe_allow_html=True)

# Barra de Investimento Inicial no topo (conforme solicitado)
if not st.session_state.simulation_df.empty:
    total_invest = st.session_state.simulation_df.iloc[-1]['Investimento Total Acumulado']
else:
    total_invest = compute_initial_investment_total(st.session_state.config)

st.markdown(f"""
    <div class="invest-strip">
        <span>💰 Investimento Inicial Total:</span>
        <span>{fmt_brl(total_invest)}</span>
    </div>
""", unsafe_allow_html=True)

# Tabs
tab_config, tab_simul, tab_data = st.tabs(["⚙️ Configurações", "📈 Simulação", "📋 Dados"])

# ---------------------------
# CONFIGURAÇÕES (aba)
# ---------------------------
with tab_config:
    st.markdown("<h3 class='section-title'>Parâmetros de Simulação</h3>", unsafe_allow_html=True)
    
    # --- CARD 1: Parâmetros Globais + Valores por Módulo ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🌍 Parâmetros Globais e Valores do Módulo")
    
    cfg_g = st.session_state.config['global']
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        cfg_g['years'] = st.number_input("Duração da Simulação (Anos)", min_value=1, max_value=30, value=cfg_g['years'], step=1, key="cfg_years")
        cfg_g['general_correction_rate'] = st.number_input("Taxa de Correção Geral Anual (%)", min_value=0.0, value=cfg_g['general_correction_rate'], step=0.1, format="%.2f", key="cfg_correction_rate")
        cfg_g['modules_init'] = st.number_input("Módulos Iniciais (Total)", min_value=1, value=cfg_g['modules_init'], step=1, key="cfg_modules_init")
        
    with c2:
        cfg_g['cost_per_module'] = st.number_input("Custo por Módulo (R$)", min_value=0.0, value=cfg_g['cost_per_module'], step=100.0, format="%.2f", key="cfg_cost_per_module")
        cfg_g['revenue_per_module'] = st.number_input("Receita Mensal/Módulo (R$)", min_value=0.0, value=cfg_g['revenue_per_module'], step=10.0, format="%.2f", key="cfg_revenue_per_module")
        cfg_g['maintenance_per_module'] = st.number_input("Manutenção Mensal/Módulo (R$)", min_value=0.0, value=cfg_g['maintenance_per_module'], step=1.0, format="%.2f", key="cfg_maintenance_per_module")

    with c3:
        cfg_g['land_appreciation_rate'] = st.number_input("Taxa de Valorização do Terreno Anual (%)", min_value=0.0, value=cfg_g['land_appreciation_rate'], step=0.1, format="%.2f", key="cfg_land_appreciation_rate")
        cfg_g['max_withdraw_value'] = st.number_input("Limite Máximo de Retirada Mensal (R$)", min_value=0.0, value=cfg_g['max_withdraw_value'], step=100.0, format="%.2f", key="cfg_max_withdraw_value")
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- CARD 2: Estratégia de Terreno e Reinvestimento ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🏡 Estratégia de Terreno e Reinvestimento")
    
    cfg_s = st.session_state.config['strategy']
    cfg_o = st.session_state.config['owned']
    cfg_r = st.session_state.config['rented']
    
    # Seleção da Estratégia de Terreno
    land_options = {
        'owned': 'Terreno Comprado (Financiado ou à Vista)',
        'rented': 'Terreno Alugado',
        'alternate': 'Intercalado (Alugado e Comprado)'
    }
    cfg_s['land_strategy'] = st.selectbox("Estratégia de Terreno", options=list(land_options.keys()), format_func=lambda x: land_options[x], key="cfg_land_strategy")
    
    # Parâmetros de Reinvestimento
    st.markdown("---")
    st.markdown("##### Estratégia de Reinvestimento do Lucro")
    reinvest_options = {
        'buy': 'Comprar Módulos (com Terreno Comprado)',
        'rent': 'Comprar Módulos (com Terreno Alugado)',
        'alternate': 'Alternar entre Comprado e Alugado'
    }
    cfg_g['reinvestment_strategy'] = st.selectbox("Estratégia para Novos Módulos", options=list(reinvest_options.keys()), format_func=lambda x: reinvest_options[x], key="cfg_reinvestment_strategy")

    # Campos Específicos para Terreno Alugado (sempre visíveis para 'rented' e 'alternate')
    if cfg_s['land_strategy'] in ['rented', 'alternate']:
        st.markdown("---")
        st.markdown("##### Parâmetros de Terreno Alugado")
        c4, c5 = st.columns(2)
        with c4:
            cfg_r['rent_value'] = st.number_input("Aluguel Mensal por Módulo (R$) - Inicial", min_value=0.0, value=cfg_r['rent_value'], step=10.0, format="%.2f", key="cfg_rent_value")
        with c5:
            cfg_r['rent_per_new_module'] = st.number_input("Aluguel Mensal por Módulo (R$) - Novos", min_value=0.0, value=cfg_r['rent_per_new_module'], step=10.0, format="%.2f", key="cfg_rent_per_new_module")
    
    # Campos Específicos para Terreno Comprado (sempre visíveis para 'owned' e 'alternate')
    if cfg_s['land_strategy'] in ['owned', 'alternate']:
        st.markdown("---")
        st.markdown("##### Parâmetros de Terreno Comprado")
        
        # Campo de Valor Total do Terreno
        cfg_o['land_total_value'] = st.number_input("Valor Total do Terreno (R$)", min_value=0.0, value=cfg_o['land_total_value'], step=1000.0, format="%.2f", key="cfg_land_total_value")
        
        if cfg_o['land_total_value'] > 0:
            c6, c7 = st.columns(2)
            with c6:
                cfg_o['land_down_payment_pct'] = st.number_input("Percentual de Entrada (%)", min_value=0.0, max_value=100.0, value=cfg_o['land_down_payment_pct'], step=1.0, format="%.2f", key="cfg_land_down_payment_pct")
                cfg_o['land_interest_rate'] = st.number_input("Taxa de Juros Anual (%)", min_value=0.0, value=cfg_o['land_interest_rate'], step=0.1, format="%.2f", key="cfg_land_interest_rate")
            with c7:
                # Campo de Número de Parcelas
                cfg_o['land_installments'] = st.number_input("Número de Parcelas (Meses)", min_value=1, value=cfg_o['land_installments'], step=1, key="cfg_land_installments")
                
                # CÁLCULO AUTOMÁTICO DA PARCELA MENSAL PARA NOVOS MÓDULOS
                valor_a_financiar = cfg_o['land_total_value'] * (1 - (cfg_o['land_down_payment_pct'] / 100.0))
                num_parcelas = max(1, cfg_o['land_installments'])
                
                # Cálculo da Parcela (Amortização Simples)
                if num_parcelas > 0:
                    parcela_calculada = valor_a_financiar / num_parcelas
                else:
                    parcela_calculada = 0.0
                
                # Atualiza o valor no estado da sessão (será usado na simulação)
                cfg_o['monthly_land_plot_parcel'] = parcela_calculada
                
                # Exibe o valor calculado
                st.markdown(f"**Parcela Mensal por Terreno (R$) - Novos Módulos**")
                st.markdown(f"**{fmt_brl(parcela_calculada)}**")
                
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- CARD 3: Aportes, Retiradas e Fundo de Reserva ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 💸 Fluxo de Caixa Adicional")
    
    # Aportes
    st.markdown("##### Aportes Programados")
    c8, c9 = st.columns(2)
    new_contribution_month = c8.number_input("Mês do Aporte", min_value=1, max_value=cfg_g['years']*12, value=1, step=1, key="new_contribution_month")
    new_contribution_value = c9.number_input("Valor do Aporte (R$)", min_value=0.0, value=0.0, step=100.0, format="%.2f", key="new_contribution_value")
    
    if st.button("Adicionar Aporte", key="add_contribution_btn"):
        if new_contribution_value > 0:
            cfg_g['contributions'].append({'mes': new_contribution_month, 'valor': new_contribution_value})
            st.session_state.config_changed = True
            st.rerun()
    
    # Lógica de remoção de aportes (simplificada)
    temp_contributions = []
    for i, c in enumerate(cfg_g['contributions']):
        col_list, col_remove = st.columns([0.8, 0.2])
        col_list.markdown(f"""
            <div class="list-item">
                <span>Mês {c['mes']}:</span>
                <span class="list-item-value">{fmt_brl(c['valor'])}</span>
            </div>
        """, unsafe_allow_html=True)
        if col_remove.button("Remover", key=f"remove_contribution_{i}"):
            st.session_state.config_changed = True
        else:
            temp_contributions.append(c)
            
    if len(temp_contributions) != len(cfg_g['contributions']):
        cfg_g['contributions'] = temp_contributions
        st.rerun()
            
    # Retiradas
    st.markdown("---")
    st.markdown("##### Retiradas (Percentual do Lucro Distribuível)")
    c10, c11 = st.columns(2)
    new_withdrawal_month = c10.number_input("Mês de Início da Retirada", min_value=1, max_value=cfg_g['years']*12, value=1, step=1, key="new_withdrawal_month")
    new_withdrawal_pct = c11.number_input("Percentual de Retirada (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.2f", key="new_withdrawal_pct")
    
    if st.button("Adicionar Retirada", key="add_withdrawal_btn"):
        if new_withdrawal_pct > 0:
            cfg_g['withdrawals'].append({'mes': new_withdrawal_month, 'percentual': new_withdrawal_pct})
            st.session_state.config_changed = True
            st.rerun()

    # Lógica de remoção de retiradas (simplificada)
    temp_withdrawals = []
    for i, w in enumerate(cfg_g['withdrawals']):
        col_list, col_remove = st.columns([0.8, 0.2])
        col_list.markdown(f"""
            <div class="list-item">
                <span>A partir do Mês {w['mes']}:</span>
                <span class="list-item-value">{w['percentual']:.2f}%</span>
            </div>
        """, unsafe_allow_html=True)
        if col_remove.button("Remover", key=f"remove_withdrawal_{i}"):
            st.session_state.config_changed = True
        else:
            temp_withdrawals.append(w)
            
    if len(temp_withdrawals) != len(cfg_g['withdrawals']):
        cfg_g['withdrawals'] = temp_withdrawals
        st.rerun()

    # Fundo de Reserva
    st.markdown("---")
    st.markdown("##### Fundo de Reserva (Percentual do Lucro Distribuível)")
    c12, c13 = st.columns(2)
    new_reserve_month = c12.number_input("Mês de Início do Fundo", min_value=1, max_value=cfg_g['years']*12, value=1, step=1, key="new_reserve_month")
    new_reserve_pct = c13.number_input("Percentual do Fundo (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.2f", key="new_reserve_pct")
    
    if st.button("Adicionar Fundo", key="add_reserve_btn"):
        if new_reserve_pct > 0:
            cfg_g['reserve_funds'].append({'mes': new_reserve_month, 'percentual': new_reserve_pct})
            st.session_state.config_changed = True
            st.rerun()
            
    # Lógica de remoção de fundos (simplificada)
    temp_reserves = []
    for i, r in enumerate(cfg_g['reserve_funds']):
        col_list, col_remove = st.columns([0.8, 0.2])
        col_list.markdown(f"""
            <div class="list-item">
                <span>A partir do Mês {r['mes']}:</span>
                <span class="list-item-value">{r['percentual']:.2f}%</span>
            </div>
        """, unsafe_allow_html=True)
        if col_remove.button("Remover", key=f"remove_reserve_{i}"):
            st.session_state.config_changed = True
        else:
            temp_reserves.append(r)
            
    if len(temp_reserves) != len(cfg_g['reserve_funds']):
        cfg_g['reserve_funds'] = temp_reserves
        st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Botão de Simulação
    st.markdown("---")
    if st.button("▶️ Executar Simulação", use_container_width=True, key="run_simulation_btn"):
        st.session_state.simulation_df = run_simulation(st.session_state.config)
        st.session_state.config_changed = False
        st.success("Simulação concluída com sucesso!")
        st.rerun()

    # Botão de Comparativo
    if st.button("🔄 Adicionar ao Comparativo", use_container_width=True, key="add_comparison_btn"):
        if st.session_state.simulation_df.empty:
            st.warning("Execute a simulação primeiro.")
        else:
            strategy_name = st.text_input("Nome da Estratégia para Comparação", value=f"Estratégia {len(st.session_state.comparison_df.get('Estratégia', []).unique()) + 1}", key="comparison_name")
            
            # Adiciona a coluna de estratégia
            df_comp = st.session_state.simulation_df.copy()
            df_comp['Estratégia'] = strategy_name
            
            if st.session_state.comparison_df.empty:
                st.session_state.comparison_df = df_comp
            else:
                # Evita duplicatas se o nome for o mesmo
                existing_strategies = st.session_state.comparison_df['Estratégia'].unique()
                if strategy_name in existing_strategies:
                    st.session_state.comparison_df = st.session_state.comparison_df[st.session_state.comparison_df['Estratégia'] != strategy_name]
                
                st.session_state.comparison_df = pd.concat([st.session_state.comparison_df, df_comp], ignore_index=True)
            
            st.success(f"Estratégia '{strategy_name}' adicionada ao comparativo!")
            st.rerun()

    if not st.session_state.comparison_df.empty:
        st.markdown("---")
        st.markdown("##### Gerenciar Comparativo")
        st.dataframe(st.session_state.comparison_df[['Estratégia']].drop_duplicates(), use_container_width=True, hide_index=True)
        if st.button("🗑️ Limpar Comparativo", use_container_width=True, key="clear_comparison_btn"):
            st.session_state.comparison_df = pd.DataFrame()
            st.success("Comparativo limpo!")
            st.rerun()

# ---------------------------
# SIMULAÇÃO (aba)
# ---------------------------
with tab_simul:
    st.markdown("<h3 class='section-title'>Resultados da Simulação</h3>", unsafe_allow_html=True)
    
    if not st.session_state.comparison_df.empty:
        st.markdown("#### 📊 Comparativo de Estratégias")
        
        dfc = st.session_state.comparison_df
        
        # Resumo do comparativo
        summary_rows = []
        for strategy in dfc['Estratégia'].unique():
            df_strat = dfc[dfc['Estratégia'] == strategy]
            summary = calculate_summary_metrics(df_strat)
            final = df_strat.iloc[-1]
            summary_rows.append({
                "Estratégia": strategy,
                "Patrimônio Líquido Final": fmt_brl(final['Patrimônio Líquido']),
                "Investimento Total": fmt_brl(final['Investimento Total Acumulado']),
                "ROI Total": f"{summary['roi_pct']:.1f}%",
                "Ponto de Equilíbrio": summary['break_even_month']
            })
        
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        
        # Gráfico de Comparativo
        metric_options = {
            "Patrimônio Líquido": "Patrimônio Líquido",
            "Investimento Total Acumulado": "Investimento Total Acumulado",
            "Caixa (Final Mês)": "Caixa (Final Mês)",
            "Receita": "Receita",
            "Gastos": "Gastos"
        }
        selected_metric = st.selectbox("Métrica para Comparação", options=list(metric_options.keys()), format_func=lambda x: metric_options[x], key="comp_metric_select")
        
        fig_comp = px.line(
            dfc, x="Mês", y=selected_metric, color='Estratégia',
            color_discrete_map={'Comprado': PRIMARY_COLOR, 'Alugado': INFO_COLOR, 'Intercalado': WARNING_COLOR}
        )
        apply_plot_theme(fig_comp, f"Comparativo de {selected_metric}", h=450)
        st.plotly_chart(fig_comp, use_container_width=True)
    
    elif not st.session_state.simulation_df.empty:
        df = st.session_state.simulation_df
        final = df.iloc[-1]
        summary = calculate_summary_metrics(df)
        
        st.markdown("### 📊 Indicadores Principais")
        k = st.columns(4)
        with k[0]: 
            render_kpi_card("Patrimônio Líquido Final", fmt_brl(final['Patrimônio Líquido']), SUCCESS_COLOR, "💰")
        with k[1]: 
            render_kpi_card("Investimento Total", fmt_brl(final['Investimento Total Acumulado']), SECONDARY_COLOR, "💼")
        with k[2]: 
            render_kpi_card("ROI Total", f"{summary['roi_pct']:.1f}%", INFO_COLOR, "📈")
            
        # Tratamento para Ponto de Equilíbrio
        break_even_display = summary['break_even_month'] if summary['break_even_month'] != 'N/A' else 'N/A'
        with k[3]: 
            render_kpi_card("Ponto de Equilíbrio", break_even_display, WARNING_COLOR, "⚖️")
        
        # Novos KPIs
        st.markdown("### 🏡 Análise de Terrenos e Dívidas")
        c = st.columns(4)
        with c[0]: 
            render_kpi_card("Terrenos Adquiridos", int(final['Terrenos Adquiridos']), INFO_COLOR, "🏠")
        with c[1]: 
            render_kpi_card("Investimento em Terrenos", fmt_brl(final['Investimento em Terrenos']), SUCCESS_COLOR, "💰")
        with c[2]: 
            render_kpi_card("Valor de Mercado Total", fmt_brl(final['Valor de Mercado Total']), WARNING_COLOR, "📊")
        with c[3]: 
            # Dívida Futura Total deve ser mostrada em valor negativo
            divida_negativa = -final['Dívida Futura Total']
            render_kpi_card("Dívida Futura Total", fmt_brl(divida_negativa), DANGER_COLOR, "💸")
            
        # KPI de Módulos Adquiridos
        st.markdown("### ⚡ Módulos Adquiridos")
        st.markdown(f"""
            <div class="kpi-card-modern" style="background:{PRIMARY_COLOR}; color:white; width: 25%;">
                <div class="kpi-card-value-modern">{int(final['Módulos Ativos'])}</div>
                <div class="kpi-card-title-modern">Módulos Ativos (Total)</div>
            </div>
        """, unsafe_allow_html=True)

        # Gráficos (mantidos)
        g1, g2 = st.columns(2)
        with g1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Patrimônio Líquido'], mode='lines', name='Patrimônio Líquido', line=dict(color=SUCCESS_COLOR, width=3)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Investimento Total Acumulado'], mode='lines', name='Investimento Total', line=dict(color=SECONDARY_COLOR, width=2, dash='dash')))
            st.plotly_chart(apply_plot_theme(fig, "Evolução do Investimento"), use_container_width=True)
        
        with g2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Receita'], mode='lines', name='Receita', line=dict(color=SUCCESS_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=df['Mês'], y=df['Gastos'], mode='lines', name='Gastos', line=dict(color=DANGER_COLOR, width=2)))
            st.plotly_chart(apply_plot_theme(fig, "Receita vs Gastos"), use_container_width=True)
        
        # Módulos por ano (barras)
        gp = df.groupby('Ano', as_index=False).agg({
            'Módulos Próprios':'last',
            'Módulos Alugados':'last',
            'Módulos Ativos':'last'
        })
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=gp['Ano'], y=gp['Módulos Ativos'], name='Módulos Ativos', marker_color=PRIMARY_COLOR))
        st.plotly_chart(apply_plot_theme(fig_bar, "Evolução de Módulos por Ano", h=380), use_container_width=True)
        
        # Fluxo de Caixa Mensal (área empilhada)
        flow = df[['Mês','Aporte','Fundo (Mês)','Retirada (Mês)']].copy()
        flow['Retirada (Mês)'] = -flow['Retirada (Mês)']  # saída como negativo p/ visual
        flow_melt = flow.melt(id_vars='Mês', var_name='Tipo', value_name='Valor')
        fig_area = px.area(flow_melt, x='Mês', y='Valor', color='Tipo',
                           color_discrete_map={"Aporte":SECONDARY_COLOR,"Fundo (Mês)":WARNING_COLOR,"Retirada (Mês)":"#9333EA"})
        st.plotly_chart(apply_plot_theme(fig_area, "Fluxo de Caixa Mensal", h=380), use_container_width=True)
        
        # Performance (ROI% + Investimento/ Caixa)
        perf = df.copy()
        perf['ROI %'] = np.where(perf['Investimento Total Acumulado']>0,
                                 (perf['Patrimônio Líquido']-perf['Investimento Total Acumulado'])/perf['Investimento Total Acumulado']*100, 0)
        fig_perf = go.Figure()
        fig_perf.add_trace(go.Scatter(x=perf['Mês'], y=perf['Investimento Total Acumulado'], name='Investimento Total', line=dict(color=SECONDARY_COLOR)))
        fig_perf.add_trace(go.Scatter(x=perf['Mês'], y=perf['Caixa (Final Mês)'], name='Caixa', line=dict(color=PRIMARY_COLOR)))
        fig_perf.add_trace(go.Scatter(x=perf['Mês'], y=perf['ROI %'], name='ROI %', yaxis='y2', line=dict(color=INFO_COLOR, width=3)))
        fig_perf.update_layout(
            yaxis=dict(title='Valores (R$)'),
            yaxis2=dict(title='ROI (%)', overlaying='y', side='right', showgrid=False)
        )
        st.plotly_chart(apply_plot_theme(fig_perf, "Performance do Investimento", h=420), use_container_width=True)
    
    else:
        st.info("💡 Configure os parâmetros na aba 'Configurações' e execute a simulação para ver os resultados.")

# ---------------------------
# RELATÓRIOS / PLANILHA (aba)
# ---------------------------
with tab_data:
    st.markdown("<h3 class='section-title'>📋 Relatórios e Dados</h3>", unsafe_allow_html=True)
    
    df_to_show = pd.DataFrame()
    if not st.session_state.comparison_df.empty:
        df_to_show = st.session_state.comparison_df
    elif not st.session_state.simulation_df.empty:
        df_to_show = st.session_state.simulation_df
    
    if df_to_show.empty:
        st.info("💡 Execute uma simulação primeiro para ver os relatórios.")
    else:
        base = df_to_show
        selected_strategy = None
        
        if 'Estratégia' in base.columns:
            selected_strategy = st.selectbox("Estratégia para análise", base['Estratégia'].unique(), key="relat_strategy_select")
            df_analysis = base[base['Estratégia']==selected_strategy].copy()
        else:
            df_analysis = base.copy()
        
        # Análise por ponto no tempo
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📅 Análise por Ponto no Tempo")
        c1, c2 = st.columns(2)
        anos = sorted(df_analysis['Ano'].unique())
        sel_year = c1.selectbox("Ano", options=anos, key="relat_ano_select")
        
        # Filtrar pelo ano selecionado
        subset = df_analysis[df_analysis['Ano']==sel_year].copy()
        if not subset.empty:
            # Obter meses disponíveis para o ano selecionado
            available_months = sorted(subset['Mês'].unique())
            sel_m = c2.selectbox("Mês", options=available_months, key="relat_mes_select")
            
            # Filtrar pelo mês específico
            filtered = subset[subset['Mês'] == sel_m]
            if not filtered.empty:
                p = filtered.iloc[0] # Pegar a primeira linha (deve ser apenas uma)
                
                # Usando colunas nomeadas individualmente
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_report_metric("Módulos Ativos", int(p['Módulos Ativos']))
                    render_report_metric("Patrimônio Líquido", p['Patrimônio Líquido'])
                with col2:
                    render_report_metric("Caixa no Mês", p['Caixa (Final Mês)'])
                    render_report_metric("Investimento Total", p['Investimento Total Acumulado'])
                with col3:
                    render_report_metric("Fundo (Mês)", p['Fundo (Mês)'])
                    render_report_metric("Fundo Acumulado", p['Fundo Acumulado'])
                with col4:
                    render_report_metric("Retirada (Mês)", p['Retirada (Mês)'])
                    render_report_metric("Retiradas Acumuladas", p['Retiradas Acumuladas'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Tabela completa selecionável + download
        with st.expander("Clique para ver a Tabela Completa da Simulação"):
            all_cols = df_analysis.columns.tolist()
            state_key = f"col_vis_{slug(selected_strategy or 'default')}"
            
            if state_key not in st.session_state:
                default_cols = ['Mês','Ano','Módulos Ativos','Receita','Gastos','Caixa (Final Mês)','Patrimônio Líquido','Investimento Total Acumulado']
                st.session_state[state_key] = {c: (c in default_cols) for c in all_cols}
            
            st.markdown("Selecione as colunas para exibir:")
            cols_to_show = []
            grid = st.columns(3)
            
            for idx, c in enumerate(all_cols):
                with grid[idx % 3]:
                    tkey = f"toggle_{slug(c)}_{state_key}"
                    # Usa um nome de chave único para cada toggle
                    st.session_state[state_key][c] = st.toggle(c, value=st.session_state[state_key].get(c, False), key=tkey)
                    if st.session_state[state_key][c]:
                        cols_to_show.append(c)
            
            if not cols_to_show:
                st.warning("Selecione ao menos uma coluna.")
            else:
                df_disp = df_analysis.copy()
                for col in (MONEY_COLS & set(df_disp.columns)):
                    df_disp[col] = df_disp[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
                st.dataframe(df_disp[cols_to_show], use_container_width=True, hide_index=True)
            
            excel_bytes = df_to_excel_bytes(df_analysis)
            st.download_button(
                "📥 Baixar Relatório Completo (Excel)",
                data=excel_bytes,
                file_name=f"relatorio_simulacao_{slug(selected_strategy or 'geral')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
