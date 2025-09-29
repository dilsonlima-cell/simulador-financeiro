# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# ================================
# Paleta de alta acessibilidade
# ================================
BG_COLOR = "#FAFAFB"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#0E1116"
MUTED_TEXT_COLOR = "#4B5563"
BORDER_COLOR = "#E5E7EB"

# Sidebar
SIDEBAR_BG = "#0B1F2A"
SIDEBAR_TEXT = "#FFFFFF"
SIDEBAR_ACCENT = "#00B8D9"

# Cores de KPI (alto contraste)
C_PRIMARY = "#0052CC"
C_SUCCESS = "#2E7D32"
C_WARNING = "#F9A825"
C_DANGER  = "#D32F2F"
C_INFO    = "#0288D1"
C_NEUTRAL = "#37474F"
C_PURPLE  = "#6A1B9A"
C_TEAL    = "#00897B"

# Cores de gráficos
CHART_CAIXA_COLOR = "#F9A825"
CHART_FUNDO_COLOR = "#0288D1"
CHART_RETIRADAS_COLOR = "#D32F2F"
CHART_MOD_PROPRIOS = "#0B1F2A"
CHART_MOD_ALUGADOS = "#6C757D"
CHART_PATRIMONIO = "#111827"
CHART_INVEST = "#6C757D"

# ================================
# Configuração da página e CSS
# ================================
st.set_page_config(
    page_title="Simulador Modular",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
<style>
  .stApp {{ background-color: {BG_COLOR}; }}
  .main .block-container {{ padding: 2rem 2.5rem; }}

  [data-testid="stSidebar"] {{
    background: {SIDEBAR_BG};
    color: {SIDEBAR_TEXT};
  }}
  [data-testid="stSidebar"] h1, 
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] p, 
  [data-testid="stSidebar"] span {{
    color: {SIDEBAR_TEXT} !important;
  }}

  /* Botões de navegação da sidebar */
  .nav-btn {{
    border: 1px solid rgba(255,255,255,0.18);
    color: {SIDEBAR_TEXT};
    background: rgba(255,255,255,0.06);
    border-radius: 10px;
    font-weight: 600;
  }}
  .nav-btn:hover {{ background: rgba(255,255,255,0.12); }}
  .nav-btn-active {{
    background: linear-gradient(90deg, {SIDEBAR_ACCENT}, #36CFC9);
    color: #001219 !important;
    border: 1px solid rgba(0,0,0,0.12);
    font-weight: 700;
  }}

  /* Tipografia principal */
  h1, h2, h3, h4, h5, h6, label, .stMarkdown p {{
    color: {TEXT_COLOR};
  }}
  .subhead {{ color: {MUTED_TEXT_COLOR}; }}

  /* Cartões */
  .card {{
    background: {CARD_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
    padding: 1.25rem 1.25rem;
  }}

  /* KPI cheio (colorido) */
  .kpi {{
    border-radius: 14px;
    color: #fff;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 6px 16px rgba(0,0,0,0.08);
    min-height: 100px;
  }}
  .kpi .label {{ font-size: .9rem; opacity: .9; }}
  .kpi .value {{ font-size: 1.6rem; font-weight: 800; line-height: 1.2; }}

  /* Tabela */
  .stDataFrame, .stTable {{ border: none; }}
</style>
""", unsafe_allow_html=True)

# ================================
# Utilitários
# ================================
def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Simulacao")
    return output.getvalue()

# ================================
# Lógica de simulação
# ================================
def simulate(config, reinvestment_strategy):
    cfg_rented = config['rented']
    cfg_owned = config['owned']
    cfg_global = config['global']

    months = cfg_global['years'] * 12
    rows = []

    modules_rented = cfg_rented['modules_init']
    modules_owned  = cfg_owned['modules_init']

    caixa = 0.0
    investimento_total = (modules_rented * cfg_rented['cost_per_module']) + (modules_owned * cfg_owned['cost_per_module'])
    fundo_ac = 0.0
    retiradas_ac = 0.0
    custo_modulo_atual_rented = cfg_rented['cost_per_module']
    custo_modulo_atual_owned  = cfg_owned['cost_per_module']

    aportes_map = {a["mes"]: a.get("valor", 0.0) for a in cfg_global['aportes']}

    # Financiamento terreno inicial (opcional)
    valor_entrada_terreno = 0.0
    valor_parcela_terreno = 0.0
    if cfg_owned['land_total_value'] > 0:
        valor_entrada_terreno = cfg_owned['land_total_value'] * (cfg_owned['land_down_payment_pct'] / 100.0)
        valor_financiado = cfg_owned['land_total_value'] - valor_entrada_terreno
        valor_parcela_terreno = valor_financiado / cfg_owned['land_installments'] if cfg_owned['land_installments'] > 0 else 0
        investimento_total += valor_entrada_terreno  # conta no investimento total

    aluguel_mensal_corrente = cfg_rented['rent_value']
    compra_intercalada_counter = 0

    for m in range(1, months + 1):
        # Receita e custos operacionais
        receita = (modules_rented * cfg_rented['revenue_per_module']) + (modules_owned * cfg_owned['revenue_per_module'])
        manut   = (modules_rented * cfg_rented['maintenance_per_module']) + (modules_owned * cfg_owned['maintenance_per_module'])
        gastos  = manut + aluguel_mensal_corrente

        aporte_mes = aportes_map.get(m, 0.0)
        caixa += aporte_mes
        investimento_mes = aporte_mes  # vamos somar outros itens ao longo do mês

        # Parcela do terreno (se houver)
        parcela_terreno_mes = 0.0
        if cfg_owned['land_total_value'] > 0 and m <= cfg_owned['land_installments']:
            parcela_terreno_mes = valor_parcela_terreno
            investimento_total += parcela_terreno_mes
            investimento_mes    += parcela_terreno_mes

        # Entrada do terreno (apenas no primeiro mês)
        entrada_terreno_mes = 0.0
        if m == 1 and valor_entrada_terreno > 0:
            entrada_terreno_mes = valor_entrada_terreno
            caixa -= entrada_terreno_mes  # saída de caixa no m1
            # investimento_total já somado acima

        # Lucro operacional do mês (antes de retiradas/fundo)
        lucro_operacional_mes = receita - gastos

        # Atualiza caixa com lucro operacional e parcela do terreno
        caixa += lucro_operacional_mes
        caixa -= parcela_terreno_mes

        # Regras de retiradas e fundo (sobre lucro)
        fundo_mes_total = 0.0
        retirada_mes_efetiva = 0.0
        if lucro_operacional_mes > 0:
            base = lucro_operacional_mes
            retirada_potencial = sum(base * (r['percentual'] / 100.0) for r in cfg_global['retiradas'] if m >= r['mes'])
            fundo_mes_total = sum(base * (f['percentual'] / 100.0) for f in cfg_global['fundos'] if m >= f['mes'])

            excesso = 0.0
            if cfg_global['max_withdraw_value'] > 0 and retirada_potencial > cfg_global['max_withdraw_value']:
                excesso = retirada_potencial - cfg_global['max_withdraw_value']
                retirada_mes_efetiva = cfg_global['max_withdraw_value']
            else:
                retirada_mes_efetiva = retirada_potencial

            fundo_mes_total += excesso

        caixa -= (retirada_mes_efetiva + fundo_mes_total)
        retiradas_ac += retirada_mes_efetiva
        fundo_ac     += fundo_mes_total

        # Expansão anual no fim de cada ano
        novos_modulos_comprados = 0
        custo_da_compra = 0.0
        if m % 12 == 0:
            custo_expansao = 0.0
            if reinvestment_strategy == 'buy':
                custo_expansao = custo_modulo_atual_owned + cfg_owned['cost_per_land_plot']
            elif reinvestment_strategy == 'rent':
                custo_expansao = custo_modulo_atual_rented
            elif reinvestment_strategy == 'alternate':
                if compra_intercalada_counter % 2 == 0:
                    custo_expansao = custo_modulo_atual_owned + cfg_owned['cost_per_land_plot']
                else:
                    custo_expansao = custo_modulo_atual_rented

            if custo_expansao > 0 and caixa >= custo_expansao:
                novos_modulos_comprados = int(caixa // custo_expansao)
                custo_da_compra = novos_modulos_comprados * custo_expansao
                if novos_modulos_comprados > 0:
                    caixa -= custo_da_compra
                    investimento_total += custo_da_compra
                    investimento_mes    += custo_da_compra

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

            # Correção anual dos custos
            custo_modulo_atual_owned  *= (1 + cfg_owned['cost_correction_rate'] / 100.0)
            custo_modulo_atual_rented *= (1 + cfg_rented['cost_correction_rate'] / 100.0)

        modules_total = modules_rented + modules_owned

        # Patrimônio: valor dos módulos próprios + caixa + fundo + valor do terreno (estimado)
        patrimonio_liquido = (modules_total * custo_modulo_atual_owned) + caixa + fundo_ac + cfg_owned['land_total_value']

        rows.append({
            "Mês": m,
            "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules_total,
            "Módulos Alugados": modules_rented,
            "Módulos Próprios": modules_owned,
            "Receita": receita,
            "Manutenção": manut,
            "Aluguel": aluguel_mensal_corrente,
            "Gastos": gastos,
            "Lucro Operacional (Mês)": lucro_operacional_mes,
            "Aporte": aporte_mes,
            "Entrada Terreno (Mês)": entrada_terreno_mes,
            "Parcela Terreno (Mês)": parcela_terreno_mes,
            "Fundo (Mês)": fundo_mes_total,
            "Retirada (Mês)": retirada_mes_efetiva,
            "Investimento no Mês": investimento_mes,
            "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac,
            "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Custo Compras no Ano": custo_da_compra,
            "Patrimônio Líquido": patrimonio_liquido
        })

    return pd.DataFrame(rows)

# ================================
# Estado padrão
# ================================
def get_default_config():
    return {
        "rented": {
            "modules_init": 1,
            "cost_per_module": 75000.0,
            "cost_correction_rate": 5.0,
            "revenue_per_module": 4500.0,
            "maintenance_per_module": 200.0,
            "rent_value": 750.0,
            "rent_per_new_module": 750.0
        },
        "owned": {
            "modules_init": 0,
            "cost_per_module": 75000.0,
            "cost_correction_rate": 5.0,
            "revenue_per_module": 4500.0,
            "maintenance_per_module": 200.0,
            "land_total_value": 0.0,
            "land_down_payment_pct": 20.0,
            "land_installments": 120,
            "cost_per_land_plot": 50000.0
        },
        "global": {
            "years": 15,
            "max_withdraw_value": 50000.0,
            "aportes": [{"mes": 3, "valor": 0.0}],
            "retiradas": [{"mes": 25, "percentual": 30.0}],
            "fundos": [{"mes": 25, "percentual": 10.0}]
        }
    }

if "config" not in st.session_state:
    st.session_state.config = get_default_config()
if "simulation_df" not in st.session_state:
    st.session_state.simulation_df = pd.DataFrame()
if "active_page" not in st.session_state:
    st.session_state.active_page = "Configurações"

# ================================
# Sidebar (nav com botões)
# ================================
with st.sidebar:
    st.markdown("<h1>Simulador Modular</h1>", unsafe_allow_html=True)
    st.markdown("<p>Projeção com reinvestimento</p>", unsafe_allow_html=True)
    st.markdown("---")

    def nav_button(label, page_key, icon=""):
        is_active = st.session_state.active_page == page_key
        btn = st.button(
            f"{icon} {label}",
            type="primary" if is_active else "secondary",
            use_container_width=True
        )
        # Acabamento visual via CSS class (opcional)
        st.markdown(
            f"<div class='{'nav-btn-active' if is_active else 'nav-btn'}' style='height:6px;border-radius:8px;margin-top:-14px;margin-bottom:10px;'></div>",
            unsafe_allow_html=True
        )
        if btn and not is_active:
            st.session_state.active_page = page_key
            st.rerun()

    nav_button("Configurações", "Configurações", "🛠️")
    nav_button("Dashboard", "Dashboard", "📊")
    nav_button("Relatórios e Dados", "Relatórios e Dados", "📑")

# ================================
# Páginas
# ================================
# --------- CONFIGURAÇÕES ---------
if st.session_state.active_page == "Configurações":
    st.title("Configurações de Investimento")
    st.markdown("<p class='subhead'>Defina parâmetros iniciais e eventos financeiros</p>", unsafe_allow_html=True)

    if st.button("🔄 Resetar para padrão", help="Restaura todos os parâmetros"):
        st.session_state.config = get_default_config()
        st.rerun()

    # Alugados
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Investimento com Terreno Alugado")
    c1, c2 = st.columns(2)
    cfg_r = st.session_state.config["rented"]
    cfg_r["modules_init"] = c1.number_input("Módulos iniciais (alugados)", 0, value=cfg_r["modules_init"])
    cfg_r["cost_per_module"] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_r["cost_per_module"], format="%.2f")
    cfg_r["revenue_per_module"] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_r["revenue_per_module"], format="%.2f")
    cfg_r["maintenance_per_module"] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_r["maintenance_per_module"], format="%.2f")
    cfg_r["cost_correction_rate"] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg_r["cost_correction_rate"], format="%.1f")
    cfg_r["rent_value"] = c2.number_input("Aluguel mensal fixo (R$)", 0.0, value=cfg_r["rent_value"], format="%.2f")
    cfg_r["rent_per_new_module"] = c1.number_input("Aluguel por novo módulo (R$)", 0.0, value=cfg_r["rent_per_new_module"], format="%.2f")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Próprios
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Investimento com Terreno Comprado")
    c1, c2 = st.columns(2)
    cfg_o = st.session_state.config["owned"]
    cfg_o["modules_init"] = c1.number_input("Módulos iniciais (próprios)", 0, value=cfg_o["modules_init"])
    cfg_o["cost_per_module"] = c1.number_input("Custo por módulo (R$)", 0.0, value=cfg_o["cost_per_module"], format="%.2f")
    cfg_o["revenue_per_module"] = c1.number_input("Receita mensal/módulo (R$)", 0.0, value=cfg_o["revenue_per_module"], format="%.2f")
    cfg_o["maintenance_per_module"] = c2.number_input("Manutenção mensal/módulo (R$)", 0.0, value=cfg_o["maintenance_per_module"], format="%.2f")
    cfg_o["cost_correction_rate"] = c2.number_input("Correção anual do custo (%)", 0.0, value=cfg_o["cost_correction_rate"], format="%.1f")
    cfg_o["cost_per_land_plot"] = c2.number_input("Custo por terreno para novo módulo (R$)", 0.0, value=cfg_o["cost_per_land_plot"], format="%.2f")

    st.markdown("---")
    st.markdown("###### Financiamento do Terreno Inicial (Opcional)")
    cfg_o["land_total_value"] = st.number_input("Valor total do terreno inicial (R$)", 0.0, value=cfg_o["land_total_value"], format="%.2f")
    if cfg_o["land_total_value"] > 0:
        c1_fin, c2_fin = st.columns(2)
        cfg_o["land_down_payment_pct"] = c1_fin.number_input("Entrada (%)", 0.0, 100.0, value=cfg_o["land_down_payment_pct"], format="%.1f")
        cfg_o["land_installments"] = c1_fin.number_input("Quantidade de parcelas", 1, 480, value=cfg_o["land_installments"])
        valor_entrada = cfg_o["land_total_value"] * (cfg_o["land_down_payment_pct"] / 100.0)
        valor_financiado = cfg_o["land_total_value"] - valor_entrada
        valor_parcela = valor_financiado / cfg_o["land_installments"] if cfg_o["land_installments"] > 0 else 0
        c2_fin.metric("Valor da Entrada", fmt_brl(valor_entrada))
        c2_fin.metric("Valor da Parcela", fmt_brl(valor_parcela))
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Globais
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Parâmetros Globais e Eventos Financeiros")
    cfg_g = st.session_state.config["global"]
    c1, c2 = st.columns(2)
    cfg_g["years"] = c1.number_input("Horizonte de investimento (anos)", 1, 50, cfg_g["years"])
    cfg_g["max_withdraw_value"] = c2.number_input("Teto de retirada mensal (R$)", 0.0, value=cfg_g["max_withdraw_value"], format="%.2f", help="Limite aplicado sobre o % do lucro.")
    st.caption("Eventos financeiros (aportes, retiradas e fundos) permanecem com a mesma lógica; ajuste no código, se necessário.")
    st.markdown("</div>", unsafe_allow_html=True)

# --------- DASHBOARD ---------
if st.session_state.active_page == "Dashboard":
    st.title("Dashboard Estratégico")
    st.markdown("<p class='subhead'>Escolha a estratégia de reinvestimento e visualize os resultados</p>", unsafe_allow_html=True)

    with st.container():
        c = st.columns(3)
        if c[0].button("📈 Simular: Comprar Terreno", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, "buy")
        if c[1].button("📈 Simular: Alugar Terreno", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, "rent")
        if c[2].button("📈 Simular: Intercalar", type="primary", use_container_width=True):
            with st.spinner("Calculando simulação..."):
                st.session_state.simulation_df = simulate(st.session_state.config, "alternate")

    if st.session_state.simulation_df.empty:
        st.info("👆 Selecione uma estratégia para iniciar a simulação.")
    else:
        df = st.session_state.simulation_df
        final = df.iloc[-1]

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Resultados Finais")
        k1, k2, k3, k4 = st.columns(4)
        cfg_r = st.session_state.config["rented"]
        cfg_o = st.session_state.config["owned"]
        investimento_inicial = (cfg_r["modules_init"] * cfg_r["cost_per_module"]) + (cfg_o["modules_init"] * cfg_o["cost_per_module"])
        if cfg_o["land_total_value"] > 0:
            investimento_inicial += cfg_o["land_total_value"] * (cfg_o["land_down_payment_pct"] / 100.0)

        k1.markdown(f"<div class='kpi' style='background:{C_NEUTRAL}'><div class='label'>Investimento Inicial</div><div class='value'>{fmt_brl(investimento_inicial)}</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='kpi' style='background:{C_PRIMARY}'><div class='label'>Patrimônio Líquido</div><div class='value'>{fmt_brl(final['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)
        k3.markdown(f"<div class='kpi' style='background:{C_DANGER}'><div class='label'>Retiradas Acumuladas</div><div class='value'>{fmt_brl(final['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
        k4.markdown(f"<div class='kpi' style='background:{C_INFO}'><div class='label'>Fundo Acumulado</div><div class='value'>{fmt_brl(final['Fundo Acumulado'])}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Análises Gráficas")

        # Patrimônio vs Investimento
        with st.container():
            st.markdown("###### Evolução do Patrimônio vs. Investimento")
            periodo = st.slider("Período (meses)", 1, len(df), (1, len(df)), key="pat_slider")
            dfp = df.loc[periodo[0]-1:periodo[1]-1]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dfp["Mês"], y=dfp["Patrimônio Líquido"], name="Patrimônio Líquido",
                                     line=dict(color=CHART_PATRIMONIO, width=2.6)))
            fig.add_trace(go.Scatter(x=dfp["Mês"], y=dfp["Investimento Total Acumulado"], name="Investimento Total",
                                     line=dict(color=CHART_INVEST, width=1.8)))
            fig.update_layout(template="plotly_white", height=420, margin=dict(l=8,r=8,t=40,b=8),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

        # Composição de módulos e distribuição
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("###### Composição dos Módulos")
            periodo2 = st.slider("Período (meses)", 1, len(df), (1, len(df)), key="comp_slider")
            dfx = df.loc[periodo2[0]-1:periodo2[1]-1]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=dfx["Mês"], y=dfx["Módulos Próprios"], name="Próprios", stackgroup="one",
                                      line=dict(color=CHART_MOD_PROPRIOS)))
            fig2.add_trace(go.Scatter(x=dfx["Mês"], y=dfx["Módulos Alugados"], name="Alugados", stackgroup="one",
                                      line=dict(color=CHART_MOD_ALUGADOS)))
            fig2.update_layout(template="plotly_white", height=420, margin=dict(l=8,r=8,t=40,b=8),
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig2, use_container_width=True)
        with c2:
            st.markdown("###### Distribuição Final dos Recursos")
            dist_data = {
                "Valores": [final["Retiradas Acumuladas"], final["Fundo Acumulado"], final["Caixa (Final Mês)"]],
                "Categorias": ["Retiradas", "Fundo Total", "Caixa Final"]
            }
            fig3 = px.pie(dist_data, values="Valores", names="Categorias",
                          color_discrete_sequence=[CHART_RETIRADAS_COLOR, CHART_FUNDO_COLOR, CHART_CAIXA_COLOR])
            fig3.update_layout(template="plotly_white", height=420, margin=dict(l=8,r=8,t=40,b=8),
                               legend=dict(orientation="h", yanchor="bottom", y=-0.1))
            st.plotly_chart(fig3, use_container_width=True)

# --------- RELATÓRIOS E DADOS ---------
if st.session_state.active_page == "Relatórios e Dados":
    st.title("Relatórios e Dados")
    st.markdown("<p class='subhead'>Explore dados detalhados por mês, com cartões de resultados e tabela completa</p>", unsafe_allow_html=True)

    if st.session_state.simulation_df.empty:
        st.info("👈 Execute uma simulação no Dashboard para habilitar os relatórios.")
    else:
        df = st.session_state.simulation_df

        with st.container():
            st.subheader("Análise por Ponto no Tempo")
            c1, c2 = st.columns(2)
            anos = df["Ano"].unique()
            selected_year = c1.selectbox("Selecione o ano", options=anos)
            meses_ano = df[df["Ano"] == selected_year]["Mês"].unique()
            month_labels = [((m-1) % 12) + 1 for m in meses_ano]
            selected_month_label = c2.selectbox("Selecione o mês", options=month_labels)
            selected_month_abs = df[(df["Ano"] == selected_year) & (((df["Mês"]-1)%12 + 1) == selected_month_label)]["Mês"].iloc[0]
            data = df[df["Mês"] == selected_month_abs].iloc[0]
            prev = df[df["Mês"] == max(1, selected_month_abs - 1)].iloc[0] if selected_month_abs > 1 else None

        st.markdown("<br>", unsafe_allow_html=True)
        # Painel de cartões coloridos — visão do mês
        st.subheader("Resumo do Mês Selecionado")
        g1 = st.columns(4)
        g1[0].markdown(f"<div class='kpi' style='background:{C_SUCCESS}'><div class='label'>Receita</div><div class='value'>{fmt_brl(data['Receita'])}</div></div>", unsafe_allow_html=True)
        g1[1].markdown(f"<div class='kpi' style='background:{C_WARNING}'><div class='label'>Gastos</div><div class='value'>{fmt_brl(data['Gastos'])}</div></div>", unsafe_allow_html=True)
        g1[2].markdown(f"<div class='kpi' style='background:{C_DANGER}'><div class='label'>Retirada (Mês)</div><div class='value'>{fmt_brl(data['Retirada (Mês)'])}</div></div>", unsafe_allow_html=True)
        g1[3].markdown(f"<div class='kpi' style='background:{C_INFO}'><div class='label'>Fundo (Mês)</div><div class='value'>{fmt_brl(data['Fundo (Mês)'])}</div></div>", unsafe_allow_html=True)

        g2 = st.columns(4)
        g2[0].markdown(f"<div class='kpi' style='background:{C_NEUTRAL}'><div class='label'>Caixa (Final Mês)</div><div class='value'>{fmt_brl(data['Caixa (Final Mês)'])}</div></div>", unsafe_allow_html=True)
        inv_mes = data["Investimento no Mês"]
        if prev is not None:
            # alternativa: delta do acumulado
            inv_mes = data["Investimento Total Acumulado"] - prev["Investimento Total Acumulado"]
        g2[1].markdown(f"<div class='kpi' style='background:{C_PRIMARY}'><div class='label'>Investimento no Mês</div><div class='value'>{fmt_brl(inv_mes)}</div></div>", unsafe_allow_html=True)
        g2[2].markdown(f"<div class='kpi' style='background:{C_PURPLE}'><div class='label'>Parcela Terreno (Mês)</div><div class='value'>{fmt_brl(data['Parcela Terreno (Mês)'])}</div></div>", unsafe_allow_html=True)
        g2[3].markdown(f"<div class='kpi' style='background:{C_TEAL}'><div class='label'>Lucro Operacional (Mês)</div><div class='value'>{fmt_brl(data['Lucro Operacional (Mês)'])}</div></div>", unsafe_allow_html=True)

        g3 = st.columns(4)
        g3[0].markdown(f"<div class='kpi' style='background:{C_NEUTRAL}'><div class='label'>Investimento Total</div><div class='value'>{fmt_brl(data['Investimento Total Acumulado'])}</div></div>", unsafe_allow_html=True)
        g3[1].markdown(f"<div class='kpi' style='background:{C_INFO}'><div class='label'>Fundo Acumulado</div><div class='value'>{fmt_brl(data['Fundo Acumulado'])}</div></div>", unsafe_allow_html=True)
        g3[2].markdown(f"<div class='kpi' style='background:{C_DANGER}'><div class='label'>Retiradas Acumuladas</div><div class='value'>{fmt_brl(data['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
        g3[3].markdown(f"<div class='kpi' style='background:{C_PRIMARY}'><div class='label'>Patrimônio Líquido</div><div class='value'>{fmt_brl(data['Patrimônio Líquido'])}</div></div>", unsafe_allow_html=True)

        g4 = st.columns(3)
        g4[0].markdown(f"<div class='kpi' style='background:{CHART_MOD_PROPRIOS}'><div class='label'>Módulos Ativos</div><div class='value'>{int(data['Módulos Ativos'])}</div></div>", unsafe_allow_html=True)
        g4[1].markdown(f"<div class='kpi' style='background:{CHART_MOD_ALUGADOS}'><div class='label'>Módulos Alugados</div><div class='value'>{int(data['Módulos Alugados'])}</div></div>", unsafe_allow_html=True)
        g4[2].markdown(f"<div class='kpi' style='background:{C_SUCCESS}'><div class='label'>Módulos Próprios</div><div class='value'>{int(data['Módulos Próprios'])}</div></div>", unsafe_allow_html=True)

        # Gráfico mensal resumido
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Resumo Gráfico do Mês")
        metricas = ["Receita", "Gastos", "Retirada (Mês)", "Fundo (Mês)"]
        valores = [data["Receita"], data["Gastos"], data["Retirada (Mês)"], data["Fundo (Mês)"]]
        cores = [C_SUCCESS, C_WARNING, C_DANGER, C_INFO]
        figm = go.Figure(data=[go.Bar(x=metricas, y=valores, marker_color=cores)])
        figm.update_layout(template="plotly_white", height=420, margin=dict(l=8,r=8,t=30,b=8))
        st.plotly_chart(figm, use_container_width=True)

        # Tabela completa com seleção de colunas
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Tabela Completa da Simulação")

        all_cols = [
            "Mês","Ano","Módulos Ativos","Módulos Alugados","Módulos Próprios",
            "Receita","Manutenção","Aluguel","Gastos","Lucro Operacional (Mês)",
            "Aporte","Entrada Terreno (Mês)","Parcela Terreno (Mês)","Fundo (Mês)","Retirada (Mês)",
            "Investimento no Mês","Caixa (Final Mês)","Investimento Total Acumulado",
            "Fundo Acumulado","Retiradas Acumuladas","Módulos Comprados no Ano",
            "Custo Compras no Ano","Patrimônio Líquido"
        ]
        default_cols = ["Mês","Ano","Módulos Ativos","Módulos Alugados","Módulos Próprios",
                        "Receita","Gastos","Caixa (Final Mês)","Investimento Total Acumulado","Patrimônio Líquido"]
        show_cols = st.multiselect("Escolha as colunas para exibição", options=all_cols, default=default_cols)

        # Formatações monetárias
        df_display = df.copy()
        money_cols = [
            "Receita","Manutenção","Aluguel","Gastos","Lucro Operacional (Mês)","Aporte",
            "Entrada Terreno (Mês)","Parcela Terreno (Mês)","Fundo (Mês)","Retirada (Mês)",
            "Investimento no Mês","Caixa (Final Mês)","Investimento Total Acumulado",
            "Fundo Acumulado","Retiradas Acumuladas","Custo Compras no Ano","Patrimônio Líquido"
        ]
        for col in money_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")

        st.dataframe(df_display[show_cols], use_container_width=True, hide_index=True)

        # Download Excel
        st.markdown("<br>", unsafe_allow_html=True)
        excel_bytes = df_to_excel_bytes(st.session_state.simulation_df)
        st.download_button(
            "📥 Baixar Relatório (Excel)",
            data=excel_bytes,
            file_name=f"simulacao_modular_{st.session_state.config['global']['years']}_anos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
