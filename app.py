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
  --text:#1F2937;       /* Gray-800 */
  --muted:#6B7280;      /* Gray-500 */
  --border:#E5E7EB;     /* Gray-200 */
  --grid:#EEF2F7;
  /* Paleta de Azuis Corporativos */
  --brand-900: #1E3A8A; /* Azul escuro para títulos */
  --brand-700: #1D4ED8;
  --brand-500: #3B82F6; /* Azul principal suave */
  --brand-100: #DBEAFE;
  --brand-50: #EFF6FF;  /* Fundo sutil */
  
  --green:#22C55E;
  --teal:#14B8A6;
  --orange:#F59E0B;
  --red:#EF4444;
}

body, .stApp{ background:var(--bg)!important; color:var(--text); }
.main .block-container{ padding:1.25rem 1.5rem; }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--text); }
section[data-testid="stSidebar"] .css-1wvskkq, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2{
  color:#F9FAFB !important;
}
section[data-testid="stSidebar"] .st-emotion-cache-1g8pund{ color:#D1D5DB; } /* Descrição */
section[data-testid="stSidebar"] .stRadio > label {
    background-color: #374151;
    border-radius: 8px;
    color: #F9FAFB !important;
}
section[data-testid="stSidebar"] .st-emotion-cache-1wmy9hl:checked + div {
    color: var(--brand-500) !important; /* Cor do texto do rádio selecionado */
}


/* Botões padrão claros */
.stButton button{
  background: var(--card);
  color: var(--brand-500);
  border: 1px solid var(--brand-500);
  border-radius: 10px;
  font-weight: 600;
}
.stButton button:hover{
  background: var(--brand-50);
}

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
  background: var(--accent, var(--brand-500)); border-top-left-radius:12px; border-bottom-left-radius:12px;
}
.kpi-soft .label{ font-size:.85rem; color:var(--muted); font-weight:600; margin-bottom:.35rem; }
.kpi-soft .value{ font-size:1.6rem; font-weight:700; color:var(--text); }

/* Títulos na aba Relatórios com cor azul */
.report-title {
    color: var(--brand-900) !important;
}
/* Legendas e textos secundários na aba Relatórios */
.report-muted {
    color: var(--brand-700) !important;
}

/* Info box mais clean */
[data-testid="stInfo"], [data-testid="stSuccess"] { 
    background: var(--brand-50); 
    border: 1px solid var(--brand-100); 
    color: var(--brand-900); 
    border-radius: 8px;
}

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
    except (ValueError, TypeError):
        return "R$ 0,00"

def light_layout(fig: go.Figure, title=""):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=18, color="var(--brand-900)")),
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
        money_fmt = workbook.add_format({"num_format": 'R$ #,##0.00'})
        for col_idx, col_name in enumerate(df.columns):
            width = max(15, int(df[col_name].astype(str).str.len().max()))
            worksheet.set_column(col_idx, col_idx, width)
            if any(k in col_name.lower() for k in ["receita","gasto","caixa","patrimônio","invest","custo","aporte","total"]):
                worksheet.set_column(col_idx, col_idx, width, money_fmt)
    st.download_button(
        "Baixar Excel",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"dl_{filename}_{len(df)}_{df.columns[0] if len(df.columns) > 0 else ''}"
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
            mod_inicial=1,
            custo_modulo=7500.0,
            receita_por_modulo=280.0,
            taxa_ocupacao=0.95,
            gasto_por_modulo=150.0,
            incremento_modulos=1,
            intervalo_incremento=6,
            custo_terreno=120000.0,
            aluguel_terreno_mensal=2500.0,
            imposto_terreno_mensal=150.0,
            mes_compra_intercalar=36,
            fator_revenda=0.60
        )
    if "selected_strategy" not in st.session_state:
        st.session_state.selected_strategy = "Comprar"

init_state()

# --------------------------------------------------------------------------------------
# Motor de simulação
# --------------------------------------------------------------------------------------
@st.cache_data
def simulate(strategy: str, **cfg) -> pd.DataFrame:
    # ... (A LÓGICA DE SIMULAÇÃO PERMANECE A MESMA) ...
    # (O código completo da função foi omitido aqui para não repetir,
    # mas ele é idêntico ao que você enviou na sua última mensagem)
    # >>> INÍCIO DA LÓGICA DE SIMULAÇÃO (idêntica à sua) <<<
    meses = int(cfg["meses"])
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

    if strategy == "Comprar":
        caixa -= custo_terreno
        investimento_total += custo_terreno
        possui_terreno = True

    for m in range(meses):
        ano = anos_base + (m // 12)
        mes = (m % 12) + 1

        if strategy == "Intercalar" and (m + 1 == mes_compra_intercalar) and (not possui_terreno):
            caixa -= custo_terreno
            investimento_total += custo_terreno
            possui_terreno = True

        novos = inc_mod if (m > 0 and (m % int_inc == 0)) else 0
        if novos > 0:
            custo_novos = novos * custo_modulo
            caixa -= custo_novos
            investimento_total += custo_novos
            mod += novos

        caixa += aporte_mensal
        investimento_total += aporte_mensal

        receita = mod * receita_mod * ocup
        gastos_var = mod * gasto_mod

        aluguel = aluguel_terreno_mensal if (strategy == "Alugar" or (strategy == "Intercalar" and not possui_terreno)) else 0.0
        imposto = imposto_terreno_mensal if possui_terreno else 0.0

        caixa += receita
        caixa -= (gastos_var + aluguel + imposto)
        receitas_acum += receita
        gastos_acum += (gastos_var + aluguel + imposto)

        patrimonio_liquido = caixa + (mod * custo_modulo * fator_revenda) + (custo_terreno * (1.00 if possui_terreno else 0.0))

        rows.append(dict(
            Estratégia=strategy, Mês=m+1, Ano=ano,
            Módulos_Ativos=mod, Receita=round(receita,2),
            Gastos=round(gastos_var + aluguel + imposto,2),
            Aporte=round(aporte_mensal,2), Caixa_Final=round(caixa,2),
            Receitas_Acumuladas=round(receitas_acum,2),
            Gastos_Acumulados=round(gastos_acum,2),
            Investimento_Total=round(investimento_total,2),
            Patrimônio_Líquido=round(patrimonio_liquido,2),
            Aluguel=round(aluguel, 2), Imposto=round(imposto, 2) # Adicionando colunas para análise
        ))
    # >>> FIM DA LÓGICA DE SIMULAÇÃO <<<
    return pd.DataFrame(rows)

# --------------------------------------------------------------------------------------
# Sidebar (navegação)
# --------------------------------------------------------------------------------------
st.sidebar.title("Simulador Modular")
st.sidebar.caption("Projeto com reinvestimento")
page = st.sidebar.radio(
    "Navegação",
    options=["Configurações", "Dashboard", "Relatórios e Dados"],
    index=["Configurações", "Dashboard", "Relatórios e Dados"].index("Dashboard"),
    key="nav_radio_unique"
)

# --------------------------------------------------------------------------------------
# Página: Configurações
# --------------------------------------------------------------------------------------
if page == "Configurações":
    st.subheader("Defina parâmetros iniciais e eventos financeiros")
    cfg = st.session_state.cfg
    
    with st.container(border=True):
        st.markdown("#### Parâmetros Gerais")
        c1, c2, c3, c4 = st.columns(4)
        cfg["meses"] = c1.number_input("Meses de simulação", 12, None, int(cfg["meses"]), 12, key="cfg_meses")
        cfg["investimento_inicial"] = c2.number_input("Investimento inicial (R$)", 0.0, None, float(cfg["investimento_inicial"]), 1000.0, "%.2f", key="cfg_inv_ini")
        cfg["aporte_mensal"] = c3.number_input("Aporte mensal (R$)", 0.0, None, float(cfg["aporte_mensal"]), 100.0, "%.2f", key="cfg_aporte")
        cfg["taxa_ocupacao"] = c4.number_input("Taxa de ocupação (%)", 0.0, 1.0, float(cfg["taxa_ocupacao"]), 0.01, "%.2f", key="cfg_ocup")
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### Parâmetros dos Módulos")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        cfg["mod_inicial"] = m1.number_input("Módulos iniciais", 0, None, int(cfg["mod_inicial"]), 1, key="cfg_mod_ini")
        cfg["custo_modulo"] = m2.number_input("Custo por módulo (R$)", 0.0, None, float(cfg["custo_modulo"]), 500.0, "%.2f", key="cfg_custo_mod")
        cfg["receita_por_modulo"] = m3.number_input("Receita por módulo (R$/mês)", 0.0, None, float(cfg["receita_por_modulo"]), 10.0, "%.2f", key="cfg_receita_mod")
        cfg["gasto_por_modulo"] = m4.number_input("Gasto por módulo (R$/mês)", 0.0, None, float(cfg["gasto_por_modulo"]), 10.0, "%.2f", key="cfg_gasto_mod")
        cfg["incremento_modulos"] = m5.number_input("Incremento de módulos", 0, None, int(cfg["incremento_modulos"]), 1, key="cfg_inc_mod")
        cfg["intervalo_incremento"] = m6.number_input("Intervalo de incremento (meses)", 1, None, int(cfg["intervalo_incremento"]), 1, key="cfg_int_inc")

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### Parâmetros do Terreno e Revenda")
        t1, t2, t3, t4, t5 = st.columns(5)
        cfg["custo_terreno"] = t1.number_input("Custo do terreno (R$)", 0.0, None, float(cfg["custo_terreno"]), 1000.0, "%.2f", key="cfg_custo_terreno")
        cfg["aluguel_terreno_mensal"] = t2.number_input("Aluguel do terreno (R$/mês)", 0.0, None, float(cfg["aluguel_terreno_mensal"]), 100.0, "%.2f", key="cfg_aluguel_terreno")
        cfg["imposto_terreno_mensal"] = t3.number_input("Imposto/Condomínio (R$/mês)", 0.0, None, float(cfg["imposto_terreno_mensal"]), 10.0, "%.2f", key="cfg_imposto_terreno")
        cfg["mes_compra_intercalar"] = t4.number_input("Intercalar: mês de compra", 1, None, int(cfg["mes_compra_intercalar"]), 1, key="cfg_mes_compra")
        cfg["fator_revenda"] = t5.number_input("Fator de revenda (%)", 0.0, 1.0, float(cfg["fator_revenda"]), 0.01, "%.2f", help="Percentual do custo do módulo considerado no cálculo do patrimônio.")
    
    st.session_state.cfg = cfg
    st.success("Configurações salvas. Acesse o Dashboard para visualizar.", icon="✅")

# --------------------------------------------------------------------------------------
# Pré-cálculo das três estratégias (usado nas páginas seguintes)
# --------------------------------------------------------------------------------------
if page in ("Dashboard", "Relatórios e Dados"):
    cfg = st.session_state.cfg
    df_buy = simulate("Comprar", **cfg)
    df_rent = simulate("Alugar", **cfg)
    df_alt = simulate("Intercalar", **cfg)
    
    final_buy = df_buy.iloc[-1]
    final_rent = df_rent.iloc[-1]
    final_alt = df_alt.iloc[-1]

    finals = {"Comprar": final_buy["Patrimônio_Líquido"], "Alugar": final_rent["Patrimônio_Líquido"], "Intercalar": final_alt["Patrimônio_Líquido"]}
    best_strategy = max(finals, key=finals.get)

# --------------------------------------------------------------------------------------
# Página: Dashboard
# --------------------------------------------------------------------------------------
if page == "Dashboard":
    st.subheader("Escolha a estratégia de investimento e visualize os resultados")
    
    sel = st.radio("Estratégia", ["Comprar", "Alugar", "Intercalar"], horizontal=True, key="dash_strategy_radio")
    st.session_state.selected_strategy = sel
    
    df_map = {"Comprar": df_buy, "Alugar": df_rent, "Intercalar": df_alt}
    df_sel = df_map[sel]
    final_sel = df_sel.iloc[-1]

    st.markdown("---")
    st.subheader("Indicadores Principais")
    kc1, kc2, kc3, kc4, kc5, kc6, kc7 = st.columns(7)
    with kc1: render_kpi_soft("Invest. Inicial", fmt_brl(cfg["investimento_inicial"]), "var(--orange)")
    with kc2: render_kpi_soft("Patrimônio Final", fmt_brl(final_sel["Patrimônio_Líquido"]), "var(--green)")
    with kc3: render_kpi_soft("Receitas Acum.", fmt_brl(final_sel["Receitas_Acumuladas"]), "var(--brand-500)")
    with kc4: render_kpi_soft("Gastos Acum.", fmt_brl(final_sel["Gastos_Acumulados"]), "var(--red)")
    with kc5: render_kpi_soft("Caixa Final", fmt_brl(final_sel["Caixa_Final"]), "var(--teal)")
    with kc6: render_kpi_soft("Melhor Estratégia", best_strategy, "var(--brand-700)")
    with kc7: render_kpi_soft("Patrimônio (Melhor)", fmt_brl(finals[best_strategy]), "var(--brand-900)")

    st.markdown("<br>", unsafe_allow_html=True)

    gc1, gc2, gc3 = st.columns(3)
    with gc1:
        df_comp = pd.concat([df_buy, df_rent, df_alt])
        fig1 = px.line(df_comp, x="Mês", y="Patrimônio_Líquido", color="Estratégia", color_discrete_map={"Comprar": "var(--brand-500)", "Alugar": "var(--green)", "Intercalar": "var(--orange)"})
        light_layout(fig1, "Comparativo de Patrimônio Líquido")
        st.plotly_chart(fig1, use_container_width=True)
    with gc2:
        fig2 = px.area(df_sel, x="Mês", y="Módulos_Ativos", color_discrete_sequence=["var(--brand-100)"])
        fig2.update_traces(line=dict(color="var(--brand-500)"))
        light_layout(fig2, f"Módulos Ativos — {sel}")
        st.plotly_chart(fig2, use_container_width=True)
    with gc3:
        values = [float(final_sel["Receitas_Acumuladas"]), float(final_sel["Gastos_Acumulados"]), max(0.0, float(final_sel["Caixa_Final"]))]
        fig3 = go.Figure(data=[go.Pie(labels=["Receitas", "Gastos", "Caixa Final"], values=values, hole=0.4, marker=dict(colors=["var(--brand-500)", "var(--red)", "var(--teal)"]))])
        light_layout(fig3, "Composição Acumulada")
        st.plotly_chart(fig3, use_container_width=True)

# --------------------------------------------------------------------------------------
# Página: Relatórios e Dados
# --------------------------------------------------------------------------------------
if page == "Relatórios e Dados":
    st.subheader("Relatórios e Dados")
    
    estrategia_tbl = st.selectbox(
        "Escolha a estratégia para análise detalhada",
        options=["Comprar", "Alugar", "Intercalar"],
        index=["Comprar", "Alugar", "Intercalar"].index(st.session_state.selected_strategy),
        key="relat_strategy_select"
    )
    df_map = {"Comprar": df_buy, "Alugar": df_rent, "Intercalar": df_alt}
    df_base = df_map[estrategia_tbl].copy()

    st.markdown("---")
    
    # --- ANÁLISE POR PONTO NO TEMPO (RESTAURADA) ---
    st.markdown("<h4 class='report-title'>Análise por Ponto no Tempo</h4>", unsafe_allow_html=True)
    ac1, ac2 = st.columns([1, 2])
    with ac1:
        st.markdown("<h5 class='report-muted'>Selecione o Período</h5>", unsafe_allow_html=True)
        anos_disponiveis = df_base['Ano'].unique()
        selected_year = st.selectbox("Ano", options=anos_disponiveis, key="relat_year_select")
        
        months_in_year = df_base[df_base['Ano'] == selected_year]['Mês'].apply(lambda x: ((x - 1) % 12) + 1).unique()
        selected_month_label = st.selectbox("Mês", options=sorted(months_in_year), key="relat_month_select")
        
        data_point_df = df_base[(df_base['Ano'] == selected_year) & (((df_base['Mês'] - 1) % 12) + 1 == selected_month_label)]
        if not data_point_df.empty:
            data_point = data_point_df.iloc[0]
            st.markdown("<br>", unsafe_allow_html=True)
            render_kpi_soft("Patrimônio no Mês", fmt_brl(data_point["Patrimônio_Líquido"]), "var(--green)")
            st.markdown("<br>", unsafe_allow_html=True)
            render_kpi_soft("Caixa Final do Mês", fmt_brl(data_point["Caixa_Final"]), "var(--teal)")
    with ac2:
        if not data_point_df.empty:
            st.markdown(f"<h5 class='report-muted'>Fluxo de Caixa do Mês {data_point['Mês']}</h5>", unsafe_allow_html=True)
            chart_data = pd.DataFrame({"Categoria": ["Receita", "Gastos"],"Valor": [data_point['Receita'], data_point['Gastos']]})
            fig_monthly = px.bar(chart_data, x="Categoria", y="Valor", text_auto='.2s', color="Categoria", color_discrete_map={"Receita": "var(--green)", "Gastos": "var(--red)"})
            light_layout(fig_monthly, f"Receita vs. Gasto (Mês {data_point['Mês']})").update_layout(showlegend=False)
            st.plotly_chart(fig_monthly, use_container_width=True)

    st.markdown("---")
    
    st.markdown("<h4 class='report-title'>Tabela Completa da Simulação</h4>", unsafe_allow_html=True)
    all_columns = df_base.columns.tolist()
    default_cols = ["Mês","Ano","Módulos_Ativos","Receita","Gastos","Caixa_Final","Patrimônio_Líquido"]

    state_key = f"column_visibility_{slug(estrategia_tbl)}"
    if (state_key not in st.session_state) or set(st.session_state[state_key].keys()) != set(all_columns):
        st.session_state[state_key] = {c: (c in default_cols) for c in all_columns}
    
    with st.expander("Exibir/Ocultar Colunas"):
        vis_map = st.session_state[state_key]
        grid_cols = st.columns(5)
        for i, col_name in enumerate(all_columns):
            with grid_cols[i % 5]:
                new_on = st.toggle(col_name, value=vis_map.get(col_name, False), key=f"tg_{slug(estrategia_tbl)}_{slug(col_name)}")
                if new_on != vis_map.get(col_name, False):
                    vis_map[col_name] = new_on
                    st.session_state[state_key] = vis_map
                    st.rerun()

    cols_to_show = [c for c, v in st.session_state[state_key].items() if v]
    if cols_to_show:
        st.dataframe(df_base[cols_to_show], use_container_width=True, hide_index=True)
        to_excel_download(df_base[cols_to_show], filename=f"relatorio_{slug(estrategia_tbl)}.xlsx")
    else:
        st.warning("Selecione ao menos uma coluna para visualizar a tabela.", icon="⚠️")

    st.markdown("---")
    st.markdown("<h4 class='report-title'>Indicadores Resumo da Estratégia</h4>", unsafe_allow_html=True)
    last = df_base.iloc[-1]
    k1, k2, k3, k4 = st.columns(4)
    with k1: render_kpi_soft("Receitas Acumuladas", fmt_brl(last["Receitas_Acumuladas"]), "var(--brand-500)")
    with k2: render_kpi_soft("Gastos Acumulados", fmt_brl(last["Gastos_Acumulados"]), "var(--red)")
    with k3: render_kpi_soft("Investimento Total", fmt_brl(last["Investimento_Total"]), "var(--teal)")
    with k4: render_kpi_soft("Patrimônio Líquido Final", fmt_brl(last["Patrimônio_Líquido"]), "var(--green)")
