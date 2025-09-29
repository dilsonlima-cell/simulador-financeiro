# app.py
# Simulador Modular — UI suave + correções
# Execução: streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import re

# --------------------------------------------------------------------------------------
# Configuração geral
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulador Modular",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------------------
# Estilos (cores suaves, KPIs discretos, cartões ON/OFF, botões claros)
# --------------------------------------------------------------------------------------
st.markdown("""
<style>
:root{
  --bg:#F7F9FC;
  --card:#FFFFFF;
  --text:#1F2937;      /* Gray-800 */
  --muted:#6B7280;     /* Gray-500 */
  --border:#E5E7EB;    /* Gray-200 */
  --grid:#EEF2F7;
  --brand:#3B82F6;     /* Blue-500 suave */
  --brand-50:#F5F9FF;  /* Fundo sutil */
  --green:#22C55E;
  --teal:#14B8A6;
  --orange:#F59E0B;
  --red:#EF4444;
}

body, .stApp{ background:var(--bg)!important; color:var(--text); }
.main .block-container{ padding:1.25rem 1.5rem; }

/* Sidebar title */
section[data-testid="stSidebar"] .css-1wvskkq, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2{
  color:#e6eefc !important;
}

/* Botões padrão claros */
.stButton button{
  background: var(--card);
  color: var(--brand);
  border: 1px solid var(--brand);
  border-radius: 10px;
  font-weight: 600;
}
.stButton button:hover{
  background: var(--brand-50);
}

/* Segmento de Estratégias (botões mais “pílula”) */
.strategy .stButton button{
  background: var(--card);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  font-weight: 700;
}
.strategy .stButton button:hover{ background:#FAFAFB; }
.strategy .stButton button[kind="secondary"]{ border-color: var(--brand); color: var(--brand); }

/* KPI suave (cartão) */
.kpi-soft{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 14px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04);
  position: relative;
  height: 100%;
}
.kpi-soft:before{
  content:"";
  position:absolute; left:0; top:0; bottom:0; width:6px;
  background: var(--accent, var(--brand)); border-top-left-radius:12px; border-bottom-left-radius:12px;
}
.kpi-soft .label{ font-size:.85rem; color:var(--muted); font-weight:600; margin-bottom:.35rem; }
.kpi-soft .value{ font-size:1.6rem; font-weight:700; color:var(--text); }

/* Cartões de seleção com botão estilo ON/OFF */
.switch-card{
  display:flex; align-items:center; justify-content:space-between;
  gap:.75rem; padding:.65rem .8rem; background:var(--card);
  border:1px solid var(--border); border-radius:12px; cursor:pointer;
  transition: background .15s, border .15s;
  height: 100%;
}
.switch-card:hover{ background:#FAFAFB; }
.switch-card .name{ font-weight:600; color:var(--text); font-size:.92rem; }

/* Pílula ON/OFF (é aplicada a st.toggle via container) */
.switch-pill{
  width:46px; height:26px; border-radius:999px;
  background:#E5E7EB; position:relative; transition:all .2s ease;
  border:1px solid #D1D5DB;
}
.switch-pill .knob{
  width:22px; height:22px; border-radius:999px; background:linear-gradient(145deg,#F3F4F6,#FFFFFF);
  position:absolute; top:50%; left:2px; transform:translateY(-50%);
  box-shadow:0 1px 2px rgba(0,0,0,.15);
  transition:left .2s ease;
}
.switch-card.on .switch-pill{ background:#BBDEFB; border-color:#93C5FD; }
.switch-card.on .switch-pill .knob{ left:22px; }
.switch-card.on .name{ color:var(--brand); }

/* Info box mais clean */
[data-testid="stInfo"]{ background:#ECF5FF; border:1px solid #D6E4FF; color:#1F2937; }

/* Dataframe borda suave */
div[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def fmt_brl(x):
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def light_layout(fig: go.Figure):
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, Calibri, system-ui, sans-serif", color="#1F2937"),
        xaxis=dict(gridcolor="#EEF2F7", zerolinecolor="#EEF2F7"),
        yaxis=dict(gridcolor="#EEF2F7", zerolinecolor="#EEF2F7"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def render_kpi_soft(title, value, accent="#3B82F6"):
    st.markdown(
        f"""
        <div class="kpi-soft" style="--accent:{accent};">
          <div class="label">{title}</div>
          <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def to_excel_download(df: pd.DataFrame, filename: str = "relatorio.xlsx"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados")
        workbook  = writer.book
        worksheet = writer.sheets["Dados"]
        money_fmt = workbook.add_format({"num_format": "R$ #,##0.00"})
        # tentativa de formatar colunas financeiras por nome
        for col_idx, col_name in enumerate(df.columns):
            width = max(12, int(df[col_name].astype(str).str.len().quantile(0.9)))
            worksheet.set_column(col_idx, col_idx, width)
            if any(k in col_name.lower() for k in ["receita","gasto","caixa","patrimônio","invest","custo","aporte","total"]):
                worksheet.set_column(col_idx, col_idx, width, money_fmt)
    st.download_button(
        "Baixar Excel",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"dl_{filename}_{len(df)}_{df.columns[0]}"
    )

def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:60]

# --------------------------------------------------------------------------------------
# Estado inicial (configurações padrão)
# --------------------------------------------------------------------------------------
def init_state():
    if "cfg" not in st.session_state:
        st.session_state.cfg = dict(
            meses=120,
            investimento_inicial=75000.0,
            aporte_mensal=4500.0,
            # módulos
            mod_inicial=1,
            custo_modulo=7500.0,
            receita_por_modulo=280.0,
            taxa_ocupacao=0.95,        # 95%
            gasto_por_modulo=150.0,
            incremento_modulos=1,
            intervalo_incremento=6,    # a cada 6 meses
            # terreno
            custo_terreno=120000.0,
            aluguel_terreno_mensal=2500.0,
            imposto_terreno_mensal=150.0,
            # intercalar
            mes_compra_intercalar=36,
            # avaliação (revenda)
            fator_revenda=0.60
        )
    if "selected_strategy" not in st.session_state:
        st.session_state.selected_strategy = "Comprar"

init_state()

# --------------------------------------------------------------------------------------
# Motor de simulação
# --------------------------------------------------------------------------------------
def simulate(strategy: str, cfg: dict) -> pd.DataFrame:
    meses = int(cfg["meses"])
    # Copia de parâmetros
    aporte_mensal = float(cfg["aporte_mensal"])
    investimento_inicial = float(cfg["investimento_inicial"])
    mod = int(cfg["mod_inicial"])
    custo_modulo = float(cfg["custo_modulo"])
    receita_mod = float(cfg["receita_por_modulo"])
    ocup = float(cfg["taxa_ocupacao"])
    gasto_mod = float(cfg["gasto_por_modulo"])
    inc_mod = int(cfg["incremento_modulos"])
    int_inc = int(cfg["intervalo_incremento"])
    custo_terreno = float(cfg["custo_terreno"])
    aluguel_terreno_mensal = float(cfg["aluguel_terreno_mensal"])
    imposto_terreno_mensal = float(cfg["imposto_terreno_mensal"])
    mes_compra_intercalar = int(cfg["mes_compra_intercalar"])
    fator_revenda = float(cfg["fator_revenda"])

    anos_base = datetime.now().year
    rows = []
    caixa = investimento_inicial
    receitas_acum = 0.0
    gastos_acum = 0.0
    investimento_total = investimento_inicial
    possui_terreno = False

    # Compra de terreno no mês 0 (Comprar)
    if strategy == "Comprar":
        caixa -= custo_terreno
        investimento_total += custo_terreno
        possui_terreno = True

    # Intercalar: compra no mês definido
    # Alugar: nunca compra; paga aluguel
    for m in range(meses):
        ano = anos_base + (m // 12)
        mes = (m % 12) + 1

        # Compra do terreno no intercalar
        if strategy == "Intercalar" and (m == mes_compra_intercalar) and (not possui_terreno):
            caixa -= custo_terreno
            investimento_total += custo_terreno
            possui_terreno = True

        # Incremento de módulos (capex)
        novos = inc_mod if (m > 0 and (m % int_inc == 0)) else 0
        if novos > 0:
            custo_novos = novos * custo_modulo
            caixa -= custo_novos
            investimento_total += custo_novos
            mod += novos

        # Aporte mensal
        caixa += aporte_mensal
        investimento_total += aporte_mensal

        # Receitas e gastos operacionais
        receita = mod * receita_mod * ocup
        gastos_var = mod * gasto_mod

        # Terreno: aluguel ou imposto
        aluguel = aluguel_terreno_mensal if (strategy == "Alugar" or (strategy == "Intercalar" and not possui_terreno)) else 0.0
        imposto = imposto_terreno_mensal if possui_terreno else 0.0

        caixa += receita
        caixa -= (gastos_var + aluguel + imposto)

        receitas_acum += receita
        gastos_acum += (gastos_var + aluguel + imposto)

        patrimonio_liquido = caixa + (mod * custo_modulo * fator_revenda) + (custo_terreno * (1.00 if possui_terreno else 0.0))

        rows.append(dict(
            Estratégia=strategy,
            Mês=m+1,
            Ano=ano,
            Módulos_Ativos=mod,
            Receita=round(receita,2),
            Gastos=round(gastos_var + aluguel + imposto,2),
            Aporte=round(aporte_mensal,2),
            Caixa_Final=round(caixa,2),
            Receitas_Acumuladas=round(receitas_acum,2),
            Gastos_Acumulados=round(gastos_acum,2),
            Investimento_Total=round(investimento_total,2),
            Patrimônio_Líquido=round(patrimonio_liquido,2),
        ))

    df = pd.DataFrame(rows)
    return df

# --------------------------------------------------------------------------------------
# Sidebar (navegação)
# --------------------------------------------------------------------------------------
st.sidebar.title("Simulador Modular")
st.sidebar.caption("Projeto com reinvestimento")
page = st.sidebar.radio(
    "Navegação",
    options=["Configurações", "Dashboard", "Relatórios e Dados"],
    index=["Configurações", "Dashboard", "Relatórios e Dados"].index("Configurações"),
    key="nav_radio_unique"
)

# --------------------------------------------------------------------------------------
# Página: Configurações
# --------------------------------------------------------------------------------------
if page == "Configurações":
    st.subheader("Defina parâmetros iniciais e eventos financeiros")

    cfg = st.session_state.cfg

    # Bloco 1 — Horizonte e valores base
    with st.container():
        c1, c2, c3, c4 = st.columns([1,1,1,1])
        cfg["meses"] = c1.number_input("Meses de simulação", min_value=12, step=12,
                                       value=int(cfg["meses"]), key="cfg_meses")
        cfg["investimento_inicial"] = c2.number_input("Investimento inicial (R$)", min_value=0.0, step=1000.0,
                                        value=float(cfg["investimento_inicial"]), format="%.2f", key="cfg_inv_ini")
        cfg["aporte_mensal"] = c3.number_input("Aporte mensal (R$)", min_value=0.0, step=100.0,
                                        value=float(cfg["aporte_mensal"]), format="%.2f", key="cfg_aporte")
        cfg["taxa_ocupacao"] = c4.number_input("Taxa de ocupação (%)", min_value=0.0, max_value=1.0, step=0.01,
                                        value=float(cfg["taxa_ocupacao"]), format="%.2f", key="cfg_ocup")

    st.markdown("---")

    # Bloco 2 — Módulos
    st.markdown("#### Parâmetros dos módulos")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    cfg["mod_inicial"] = m1.number_input("Módulos iniciais", min_value=0, step=1,
                                value=int(cfg["mod_inicial"]), key="cfg_mod_ini")
    cfg["custo_modulo"] = m2.number_input("Custo por módulo (R$)", min_value=0.0, step=500.0,
                                value=float(cfg["custo_modulo"]), format="%.2f", key="cfg_custo_mod")
    cfg["receita_por_modulo"] = m3.number_input("Receita por módulo (R$/mês)", min_value=0.0, step=10.0,
                                value=float(cfg["receita_por_modulo"]), format="%.2f", key="cfg_receita_mod")
    cfg["gasto_por_modulo"] = m4.number_input("Gasto por módulo (R$/mês)", min_value=0.0, step=10.0,
                                value=float(cfg["gasto_por_modulo"]), format="%.2f", key="cfg_gasto_mod")
    cfg["incremento_modulos"] = m5.number_input("Incremento de módulos", min_value=0, step=1,
                                value=int(cfg["incremento_modulos"]), key="cfg_inc_mod")
    cfg["intervalo_incremento"] = m6.number_input("Intervalo de incremento (meses)", min_value=1, step=1,
                                value=int(cfg["intervalo_incremento"]), key="cfg_int_inc")

    st.markdown("---")

    # Bloco 3 — Terreno
    st.markdown("#### Parâmetros do terreno")
    t1, t2, t3, t4 = st.columns(4)
    cfg["custo_terreno"] = t1.number_input("Custo do terreno (R$)", min_value=0.0, step=1000.0,
                                value=float(cfg["custo_terreno"]), format="%.2f", key="cfg_custo_terreno")
    cfg["aluguel_terreno_mensal"] = t2.number_input("Aluguel do terreno (R$/mês)", min_value=0.0, step=100.0,
                                value=float(cfg["aluguel_terreno_mensal"]), format="%.2f", key="cfg_aluguel_terreno")
    cfg["imposto_terreno_mensal"] = t3.number_input("Imposto/Condomínio (R$/mês)", min_value=0.0, step=10.0,
                                value=float(cfg["imposto_terreno_mensal"]), format="%.2f", key="cfg_imposto_terreno")
    cfg["mes_compra_intercalar"] = t4.number_input("Intercalar: mês de compra do terreno", min_value=1, step=1,
                                value=int(cfg["mes_compra_intercalar"]), key="cfg_mes_compra")
    st.info("As simulações consideram três estratégias: Comprar, Alugar e Intercalar (aluga até comprar).", icon="ℹ️")

    # Persistência
    st.session_state.cfg = cfg
    st.success("Configurações salvas. Acesse o Dashboard para visualizar.", icon="✅")

# --------------------------------------------------------------------------------------
# Pré-cálculo das três estratégias (usado nas páginas seguintes)
# --------------------------------------------------------------------------------------
if page in ("Dashboard", "Relatórios e Dados"):
    cfg = st.session_state.cfg
    df_buy = simulate("Comprar", cfg)
    df_rent = simulate("Alugar", cfg)
    df_alt = simulate("Intercalar", cfg)

    # Frames agregados
    final_buy = df_buy.iloc[-1]
    final_rent = df_rent.iloc[-1]
    final_alt = df_alt.iloc[-1]

    # Melhor estratégia por patrimônio final
    finals = {
        "Comprar": final_buy["Patrimônio_Líquido"],
        "Alugar": final_rent["Patrimônio_Líquido"],
        "Intercalar": final_alt["Patrimônio_Líquido"],
    }
    best_strategy = max(finals, key=finals.get)

# --------------------------------------------------------------------------------------
# Página: Dashboard
# --------------------------------------------------------------------------------------
if page == "Dashboard":
    st.subheader("Escolha a estratégia de investimento e visualize os resultados")

    # Seletor tipo “pílula” (3 botões)
    st.markdown('<div class="strategy">', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns([1,1,1,6])
    if s1.button("Comprar Terreno", key="btn_buy"):
        st.session_state.selected_strategy = "Comprar"
    if s2.button("Alugar Terreno", key="btn_rent"):
        st.session_state.selected_strategy = "Alugar"
    if s3.button("Intercalar", key="btn_alt"):
        st.session_state.selected_strategy = "Intercalar"
    st.markdown('</div>', unsafe_allow_html=True)

    sel = st.session_state.selected_strategy
    df_map = {"Comprar": df_buy, "Alugar": df_rent, "Intercalar": df_alt}
    df_sel = df_map[sel]
    final_sel = df_sel.iloc[-1]

    # KPIs — layout suave
    st.markdown("")
    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1: render_kpi_soft("Investimento Inicial", fmt_brl(st.session_state.cfg["investimento_inicial"]), "#4F8CF3")
    with kc2: render_kpi_soft("Patrimônio Líquido", fmt_brl(final_sel["Patrimônio_Líquido"]), "#22C55E")
    with kc3: render_kpi_soft("Receitas Acumuladas", fmt_brl(final_sel["Receitas_Acumuladas"]), "#F59E0B")
    with kc4: render_kpi_soft("Gastos Acumulados", fmt_brl(final_sel["Gastos_Acumulados"]), "#14B8A6")

    st.markdown("")

    # Gráfico 1 — Comparativo Patrimônio vs Investimento (todas as estratégias)
    df_comp = pd.DataFrame({
        "Mês": df_buy["Mês"],
        "Patrimônio_Comprar": df_buy["Patrimônio_Líquido"],
        "Patrimônio_Alugar": df_rent["Patrimônio_Líquido"],
        "Patrimônio_Intercalar": df_alt["Patrimônio_Líquido"],
        "Investimento_Total": df_buy["Investimento_Total"],  # semelhante entre estratégias nesta modelagem
    })
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df_comp["Mês"], y=df_comp["Patrimônio_Comprar"], name="Patrimônio (Comprar)", line=dict(color="#4F8CF3")))
    fig1.add_trace(go.Scatter(x=df_comp["Mês"], y=df_comp["Patrimônio_Alugar"], name="Patrimônio (Alugar)", line=dict(color="#22C55E")))
    fig1.add_trace(go.Scatter(x=df_comp["Mês"], y=df_comp["Patrimônio_Intercalar"], name="Patrimônio (Intercalar)", line=dict(color="#F59E0B")))
    fig1.add_trace(go.Scatter(x=df_comp["Mês"], y=df_comp["Investimento_Total"], name="Investimento Total", line=dict(color="#94A3B8", dash="dash")))
    light_layout(fig1)
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2 — Módulos ativos (selecionado)
    fig2 = px.area(
        df_sel, x="Mês", y="Módulos_Ativos",
        title=f"Módulos Ativos — {sel}",
        color_discrete_sequence=["#94B8FF"]
    )
    light_layout(fig2)
    st.plotly_chart(fig2, use_container_width=True)

    # Gráfico 3 — Composição (Receitas x Gastos x Caixa) para o mês final
    values = [
        float(final_sel["Receitas_Acumuladas"]),
        float(final_sel["Gastos_Acumulados"]),
        max(0.0, float(final_sel["Caixa_Final"]))
    ]
    fig3 = go.Figure(data=[go.Pie(
        labels=["Receitas", "Gastos", "Caixa Final"],
        values=values,
        hole=0.4,
        marker=dict(colors=["#4F8CF3", "#EF4444", "#3B82F6"]),
    )])
    fig3.update_layout(title="Composição Acumulada")
    light_layout(fig3)
    st.plotly_chart(fig3, use_container_width=True)

    # KPI de Melhor Estratégia
    bc1, bc2, bc3 = st.columns([2,3,3])
    with bc1:
        render_kpi_soft("Melhor Estratégia (Patrimônio)", best_strategy, "#3B82F6")
    with bc2:
        render_kpi_soft("Patrimônio - Melhor", fmt_brl(finals[best_strategy]), "#22C55E")
    with bc3:
        render_kpi_soft("Patrimônio - Selecionada", fmt_brl(final_sel["Patrimônio_Líquido"]), "#14B8A6")

# --------------------------------------------------------------------------------------
# Página: Relatórios e Dados
# --------------------------------------------------------------------------------------
if page == "Relatórios e Dados":
    st.subheader("Relatórios e Dados")

    # Escolha da estratégia para a tabela
    csel1, csel2 = st.columns([2,8])
    estrategia_tbl = csel1.selectbox(
        "Escolha a estratégia",
        options=["Comprar", "Alugar", "Intercalar"],
        index=["Comprar", "Alugar", "Intercalar"].index(st.session_state.selected_strategy),
        key="relat_strategy_select"
    )
    df_map = {"Comprar": df_buy, "Alugar": df_rent, "Intercalar": df_alt}
    df_base = df_map[estrategia_tbl].copy()

    # Exibir tabela com seletor de colunas em cartões ON/OFF
    st.markdown("##### Seleção de colunas")
    all_columns = df_base.columns.tolist()

    # Preset de colunas “padrão”
    default_cols = ["Mês","Ano","Módulos_Ativos","Receita","Gastos","Caixa_Final","Patrimônio_Líquido"]

    # Estado: visibilidade de colunas por estratégia
    state_key = f"column_visibility_{slug(estrategia_tbl)}"
    if (state_key not in st.session_state) or set(st.session_state[state_key].keys()) != set(all_columns):
        st.session_state[state_key] = {c: (c in default_cols) for c in all_columns}

    act = st.columns([1,1,1,6])
    if act[0].button("Padrão", key=f"preset_default_{slug(estrategia_tbl)}"):
        st.session_state[state_key] = {c: (c in default_cols) for c in all_columns}
        st.rerun()
    if act[1].button("Todos", key=f"preset_all_{slug(estrategia_tbl)}"):
        st.session_state[state_key] = {c: True for c in all_columns}
        st.rerun()
    if act[2].button("Nenhum", key=f"preset_none_{slug(estrategia_tbl)}"):
        st.session_state[state_key] = {c: False for c in all_columns}
        st.rerun()

    st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)

    # Grade de cartões: cada cartão contém um toggle; o container recebe classe on/off
    grid_cols = st.columns(4)
    vis_map = st.session_state[state_key]

    for i, col_name in enumerate(all_columns):
        col = grid_cols[i % 4]
        with col:
            on = bool(vis_map.get(col_name, False))
            container = st.container()
            with container:
                # rótulo + "pílula" visual
                left, right = st.columns([5,1])
                with left:
                    st.markdown(
                        f"""
                        <div class="switch-card {'on' if on else ''}">
                          <div class="name">{col_name}</div>
                          <div class="switch-pill"><div class="knob"></div></div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with right:
                    # toggle real (mantém estado); chave única
                    new_on = st.toggle(
                        label=f" ",
                        value=on,
                        key=f"tg_{slug(estrategia_tbl)}_{slug(col_name)}",
                        label_visibility="collapsed",
                        help="Alternar coluna"
                    )
            # sincroniza estado (se diferente, aplica e reroda)
            if new_on != on:
                vis_map[col_name] = new_on
                st.session_state[state_key] = vis_map
                st.rerun()

    cols_to_show = [c for c, v in vis_map.items() if v]
    st.markdown("")
    if cols_to_show:
        st.dataframe(df_base[cols_to_show], use_container_width=True, hide_index=True)
        to_excel_download(df_base[cols_to_show], filename=f"relatorio_{slug(estrategia_tbl)}.xlsx")
    else:
        st.warning("Selecione ao menos uma coluna para visualizar a tabela.", icon="⚠️")

    st.markdown("---")

    # Pequenos relatórios
    st.markdown("#### Indicadores Resumo")
    last = df_base.iloc[-1]
    k1, k2, k3, k4 = st.columns(4)
    with k1: render_kpi_soft("Receitas Acumuladas", fmt_brl(last["Receitas_Acumuladas"]), "#4F8CF3")
    with k2: render_kpi_soft("Gastos Acumulados", fmt_brl(last["Gastos_Acumulados"]), "#EF4444")
    with k3: render_kpi_soft("Investimento Total", fmt_brl(last["Investimento_Total"]), "#14B8A6")
    with k4: render_kpi_soft("Patrimônio Líquido", fmt_brl(last["Patrimônio_Líquido"]), "#22C55E")

    # Gráfico simples mensal
    st.markdown("")
    g1, g2 = st.columns(2)
    with g1:
        figm = px.line(df_base, x="Mês", y=["Receita", "Gastos"], color_discrete_map={
            "Receita": "#4F8CF3",
            "Gastos": "#EF4444"
        })
        figm.update_traces(line=dict(width=3))
        light_layout(figm)
        st.plotly_chart(figm, use_container_width=True)
    with g2:
        figc = px.line(df_base, x="Mês", y=["Caixa_Final", "Patrimônio_Líquido"], color_discrete_map={
            "Caixa_Final": "#3B82F6",
            "Patrimônio_Líquido": "#22C55E"
        })
        figc.update_traces(line=dict(width=3))
        light_layout(figc)
        st.plotly_chart(figc, use_container_width=True)

# --------------------------------------------------------------------------------------
# Rodapé simples
# --------------------------------------------------------------------------------------
st.markdown("")
st.caption("Layout suave, cartões ON/OFF e correções de chave para evitar erros de elementos duplicados.")
