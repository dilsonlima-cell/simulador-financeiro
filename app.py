import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import date, datetime
# from dateutil.relativedelta import relativedelta # placeholder to hint monthly ops
from io import BytesIO

# =========================================
# Simulador de Investimentos Imobiliários
# Arquivo único: app.py
# Requisitos implementados:
# - UI completa em PT-BR com Streamlit
# - Tema escuro "SIGELite" via CSS e Plotly
# - Editor de múltiplos financiamentos (PRICE/SAC) com carência, IPTU, custos, etc.
# - Motor de simulação mensal, com estratégias Comprar/Alugar/Alternar
# - Cálculo de caixa, dívida, valor de mercado, patrimônio, VPL e TIR (opcional)
# - Gráficos, Tabelas, Cronogramas, Exportação Excel
# =========================================

# -----------------------------------------------------
# Configuração de página
# -----------------------------------------------------
st.set_page_config(
    page_title="Simulador de Investimentos Imobiliários",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------
# Tema visual SIGELite - CSS e Plotly
# -----------------------------------------------------
SIGELITE = {
    "primary": "#1E88E5",
    "secondary": "#0D47A1",
    "accent": "#26C6DA",
    "bg": "#0B1220",
    "surface": "#111827",
    "text": "#E5E7EB",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "muted": "#94A3B8",
    "grid": "#1F2937"
}

def apply_sigelite_theme():
    css = f"""
    <style>
    :root {{
        --color-primary: {SIGELITE['primary']};
        --color-secondary: {SIGELITE['secondary']};
        --color-accent: {SIGELITE['accent']};
        --color-bg: {SIGELITE['bg']};
        --color-surface: {SIGELITE['surface']};
        --color-text: {SIGELITE['text']};
        --color-success: {SIGELITE['success']};
        --color-warning: {SIGELITE['warning']};
        --color-error: {SIGELITE['error']};
        --color-muted: {SIGELITE['muted']};
        --color-grid: {SIGELITE['grid']};
    }}

    html, body, [class^="css"]  {{
        background-color: var(--color-bg) !important;
        color: var(--color-text) !important;
    }}

    .stApp {{
        background-color: var(--color-bg);
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }}

    /* Cabeçalhos */
    h1, h2, h3, h4, h5, h6 {{
        color: var(--color-text);
    }}

    /* Botões */
    .stButton > button {{
        background-color: var(--color-primary);
        color: #fff;
        border: 1px solid var(--color-secondary);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: filter 0.2s ease-in-out, transform 0.02s;
    }}
    .stButton > button:hover {{
        filter: brightness(1.1);
    }}
    .stButton > button:active {{
        transform: translateY(1px);
    }}

    /* Inputs */
    .stNumberInput input, .stTextInput input, .stDateInput input, .stSelectbox div, .stTextArea textarea {{
        background-color: var(--color-surface) !important;
        color: var(--color-text) !important;
        border: 1px solid var(--color-grid) !important;
    }}

    /* Data editor */
    .stDataEditor {{
        background-color: var(--color-surface);
        color: var(--color-text);
    }}

    /* Tabs */
    .stTabs [role="tablist"] {{
        border-bottom: 1px solid var(--color-grid);
    }}
    .stTabs [role="tab"] {{
        color: var(--color-text);
        border: 1px solid var(--color-grid);
        background-color: var(--color-surface);
        margin-right: 6px;
        border-bottom: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: var(--color-primary) !important;
        color: #fff !important;
    }}

    /* Métricas */
    .stMetric {{
        background-color: var(--color-surface);
        border: 1px solid var(--color-grid);
        border-radius: 10px;
        padding: 1rem;
    }}

    /* Expander */
    .streamlit-expanderHeader {{
        background-color: var(--color-surface) !important;
        color: var(--color-text) !important;
        border: 1px solid var(--color-grid) !important;
        border-radius: 8px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def set_plotly_template():
    template = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=SIGELITE["bg"],
            plot_bgcolor=SIGELITE["surface"],
            font=dict(color=SIGELITE["text"], family="Inter, Segoe UI, system-ui, -apple-system, sans-serif"),
            xaxis=dict(
                gridcolor=SIGELITE["grid"],
                zerolinecolor=SIGELITE["grid"],
                linecolor=SIGELITE["grid"]
            ),
            yaxis=dict(
                gridcolor=SIGELITE["grid"],
                zerolinecolor=SIGELITE["grid"],
                linecolor=SIGELITE["grid"]
            ),
            colorway=[SIGELITE["primary"], SIGELITE["accent"], SIGELITE["success"], SIGELITE["warning"], SIGELITE["secondary"]],
            legend=dict(
                bgcolor=SIGELITE["surface"],
                bordercolor=SIGELITE["grid"]
            )
        )
    )
    pio.templates["sigelite_dark"] = template
    pio.templates.default = "sigelite_dark"

apply_sigelite_theme()
set_plotly_template()

# -----------------------------------------------------
# Utilitários
# -----------------------------------------------------
def first_day_of_month(d: date) -> date:
    return date(d.year, d.month, 1)

def parse_year_month_to_date(val):
    """
    Aceita:
    - string 'YYYY-MM'
    - datetime.date/datetime
    - pandas.Timestamp
    Retorna date no primeiro dia do mês.
    """
    if pd.isna(val):
        return None
    if isinstance(val, pd.Timestamp):
        return date(val.year, val.month, 1)
    if isinstance(val, datetime):
        return date(val.year, val.month, 1)
    if isinstance(val, date):
        return date(val.year, val.month, 1)
    if isinstance(val, str):
        try:
            parts = val.split("-")
            y, m = int(parts[0]), int(parts[1])
            return date(y, m, 1)
        except Exception:
            return None
    return None

def months_between(d_start: date, d_end: date) -> int:
    return (d_end.year - d_start.year) * 12 + (d_end.month - d_start.month)

def add_months(d: date, m: int) -> date:
    year = d.year + (d.month - 1 + m) // 12
    month = (d.month - 1 + m) % 12 + 1
    return date(year, month, 1)

def format_currency_br(valor) -> str:
    try:
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            return "R$ 0,00"
        s = f"{valor:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return "R$ 0,00"

def npv(flows: np.ndarray, rate_monthly: float) -> float:
    # VPL de série mensal: t=0..n-1
    if len(flows) == 0:
        return 0.0
    discounts = (1.0 + rate_monthly) ** np.arange(len(flows))
    return float(np.sum(flows / discounts))

def has_sign_change(arr):
    return np.any(arr < 0) and np.any(arr > 0)

def irr_bisection(flows: np.ndarray, low=-0.9999, high=1.0, tol=1e-7, max_iter=200):
    """
    TIR mensal via busca binária sobre taxa para NPV ~ 0.
    Retorna None quando não há mudança de sinal ou não converge.
    """
    if len(flows) < 2 or not has_sign_change(flows):
        return None
    # Ajustar high para tentar convergência
    def f(r):
        try:
            return npv(flows, r)
        except Exception:
            return np.inf
    f_low = f(low)
    f_high = f(high)
    # Expandir high até sinais diferentes ou atingir limite
    expand_steps = 0
    while f_low * f_high > 0 and expand_steps < 20:
        high = high + 1.0
        f_high = f(high)
        expand_steps += 1
    if f_low * f_high > 0:
        return None
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        f_mid = f(mid)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return mid

def safe_div(a, b):
    return a / b if b != 0 else 0.0

# -----------------------------------------------------
# Cálculo de cronogramas de financiamento
# -----------------------------------------------------
def build_loan_schedule(
    loan_id: str,
    start_date: date,
    principal_value: float,
    down_payment: float,
    annual_rate: float,
    years: int,
    system: str,
    grace_months: int,
    annual_appreciation: float,
    initial_costs_pct: float,
    iptu_pct_year: float,
    monthly_fixed_costs: float,
    timeline_index: pd.DatetimeIndex,
    monthly_inflation: float
) -> pd.DataFrame:
    """
    Gera cronograma mensal deste financiamento, alinhado ao índice da timeline (MS).
    - system: PRICE ou SAC
    - start_date: data da compra (1º dia do mês)
    Retorna DataFrame com index na timeline e colunas:
    ['ID','Prestacao','Juros','Amortizacao','SaldoDevedor','ValorMercado','IPTU','DespesasFixas','Entrada','CustosIniciais','Ativo']
    """
    # Preparação
    valor_terreno = float(principal_value)
    entrada = float(down_payment)
    valor_financiado = max(0.0, valor_terreno - entrada)
    prazo_meses = max(0, int(years * 12))
    carencia = max(0, int(grace_months))
    i_m = (1 + annual_rate) ** (1 / 12.0) - 1.0 if annual_rate is not None else 0.0
    a_m = (1 + annual_appreciation) ** (1 / 12.0) - 1.0 if annual_appreciation is not None else 0.0

    # Early exit se start_date for None ou prazo zero
    if start_date is None or prazo_meses <= 0:
        # Retornar estrutura vazia (com zeros)
        base = pd.DataFrame(index=timeline_index)
        for col in ['ID','Prestacao','Juros','Amortizacao','SaldoDevedor','ValorMercado','IPTU','DespesasFixas','Entrada','CustosIniciais','Ativo']:
            base[col] = 0.0
        base['ID'] = loan_id
        base['Ativo'] = 0.0
        return base

    # Construção de vetores alinhados à timeline
    # Meses desde começo da timeline para start_date
    timeline_start = timeline_index[0].date()
    n_total = len(timeline_index)
    start_offset = months_between(timeline_start, start_date)
    if start_offset >= n_total:
        # Compra depois do horizonte
        base = pd.DataFrame(index=timeline_index)
        for col in ['ID','Prestacao','Juros','Amortizacao','SaldoDevedor','ValorMercado','IPTU','DespesasFixas','Entrada','CustosIniciais','Ativo']:
            base[col] = 0.0
        base['ID'] = loan_id
        base['Ativo'] = 0.0
        return base

    # Arrays numéricos
    prest = np.zeros(n_total)
    juros = np.zeros(n_total)
    amort = np.zeros(n_total)
    saldo = np.zeros(n_total)
    valor_mercado = np.zeros(n_total)
    iptu = np.zeros(n_total)
    despesas = np.zeros(n_total)
    entrada_arr = np.zeros(n_total)
    custos_iniciais_arr = np.zeros(n_total)
    ativo_flag = np.zeros(n_total)  # 1 se esse financiamento está ativo a partir da compra

    # Custos iniciais e entrada no mês da compra
    if start_offset >= 0:
        entrada_arr[start_offset] = entrada
        custos_iniciais_arr[start_offset] = valor_terreno * initial_costs_pct

    # Valor de mercado evolui a partir da compra até o fim da linha do tempo
    vm = valor_terreno
    for t in range(start_offset, n_total):
        if t < start_offset:
            continue
        if t == start_offset:
            valor_mercado[t] = vm
        else:
            vm = vm * (1.0 + a_m)
            valor_mercado[t] = vm

    # Despesas fixas mensais (indexadas pela inflação mensal informada)
    if monthly_fixed_costs is None:
        monthly_fixed_costs = 0.0
    base_desp = monthly_fixed_costs
    for t in range(start_offset, n_total):
        # Aplica inflação acumulada desde o mês de início da compra
        meses_passados = t - start_offset
        despesas[t] = base_desp * ((1.0 + monthly_inflation) ** meses_passados)

    # IPTU mensal pró-rata sobre valor de mercado
    iptu_pct_mensal = iptu_pct_year / 12.0 if iptu_pct_year is not None else 0.0
    for t in range(start_offset, n_total):
        iptu[t] = valor_mercado[t] * iptu_pct_mensal

    # Amortização/juros/saldo conforme sistema e carência
    # Fluxo de financiamento apenas por "prazo_meses" após a compra (juros na carência + amortização no remanescente)
    saldo_atual = valor_financiado
    n_amort = max(0, prazo_meses - carencia)
    if system.upper() == "PRICE":
        if n_amort > 0:
            if abs(i_m) < 1e-12:
                parcela = saldo_atual / n_amort
            else:
                parcela = saldo_atual * (i_m * (1 + i_m) ** n_amort) / ((1 + i_m) ** n_amort - 1)
        else:
            parcela = 0.0

        for k in range(prazo_meses):  # k = 0...prazo-1
            t = start_offset + k
            if t >= n_total:
                break
            if k < carencia:
                # Paga somente juros
                j = saldo_atual * i_m
                juros[t] = j
                prest[t] = j
                amort[t] = 0.0
            else:
                j = saldo_atual * i_m
                a = parcela - j
                # Evitar saldo negativo no final por arredondamento
                if a > saldo_atual:
                    a = saldo_atual
                juros[t] = j
                amort[t] = a
                prest[t] = j + a
                saldo_atual = max(0.0, saldo_atual - a)
            saldo[t] = saldo_atual

    else:  # SAC
        A = saldo_atual / n_amort if n_amort > 0 else 0.0
        for k in range(prazo_meses):
            t = start_offset + k
            if t >= n_total:
                break
            if k < carencia:
                j = saldo_atual * i_m
                juros[t] = j
                prest[t] = j
                amort[t] = 0.0
            else:
                j = saldo_atual * i_m
                a = A
                if a > saldo_atual:
                    a = saldo_atual
                juros[t] = j
                amort[t] = a
                prest[t] = j + a
                saldo_atual = max(0.0, saldo_atual - a)
            saldo[t] = saldo_atual

    # Ativo flag = 1 a partir do mês da compra (para fins de filtragem rápida)
    ativo_flag[start_offset:] = 1.0

    df = pd.DataFrame(index=timeline_index)
    df["ID"] = loan_id
    df["Prestacao"] = prest
    df["Juros"] = juros
    df["Amortizacao"] = amort
    df["SaldoDevedor"] = saldo
    df["ValorMercado"] = valor_mercado
    df["IPTU"] = iptu
    df["DespesasFixas"] = despesas
    df["Entrada"] = entrada_arr
    df["CustosIniciais"] = custos_iniciais_arr
    df["Ativo"] = ativo_flag
    # Filtra antes da compra deve ser zero (já é)
    return df

# -----------------------------------------------------
# Entradas e validações
# -----------------------------------------------------
def build_inputs():
    with st.sidebar:
        st.header("Parâmetros Globais")
        horizonte_anos = st.number_input("Horizonte (anos)", min_value=1, max_value=40, value=25, step=1, format="%d")
        inflacao_anual = st.number_input("Inflação anual (%)", min_value=0.0, value=4.0, step=0.1, format="%.2f") / 100.0
        taxa_desconto_anual = st.number_input("Taxa de desconto anual (%) para KPIs (VPL)", min_value=0.0, value=8.0, step=0.1, format="%.2f") / 100.0
        estrategia = st.selectbox("Estratégia", options=["Comprar", "Alugar", "Alternar"], index=0)
        reserva_inicial = st.number_input("Reserva de caixa inicial (R$)", min_value=0.0, value=50000.0, step=1000.0, format="%.2f")

        anos_alternar = 2
        if estrategia == "Alternar":
            anos_alternar = st.number_input("Alternar a cada N anos", min_value=1, max_value=20, value=2, step=1, format="%d")

        st.markdown("---")
        st.subheader("Cenário de Aluguel")
        aluguel_inicial = st.number_input("Aluguel mensal inicial (R$)", min_value=0.0, value=2500.0, step=100.0, format="%.2f")
        reajuste_anual_aluguel = st.number_input("Reajuste anual do aluguel (%)", min_value=0.0, value=5.0, step=0.1, format="%.2f") / 100.0
        vacancia = st.number_input("Vacância esperada (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5, format="%.2f") / 100.0
        condominio_mensal = st.number_input("Condomínio mensal (R$)", min_value=0.0, value=500.0, step=50.0, format="%.2f")
        seguro_mensal = st.number_input("Seguro mensal (R$)", min_value=0.0, value=80.0, step=10.0, format="%.2f")

    st.subheader("Terrenos e Financiamentos")
    st.caption("Edite ou adicione vários financiamentos. Datas no formato YYYY-MM.")
    default_data = pd.DataFrame([
        {
            "Nome/ID": "Terreno A",
            "Data de compra (YYYY-MM)": date.today().strftime("%Y-%m"),
            "Valor do terreno (R$)": 300000.0,
            "Entrada (R$)": 60000.0,
            "Juros a.a. (%)": 12.0,
            "Prazo (anos)": 20,
            "Sistema": "PRICE",
            "Carência (meses)": 0,
            "Apreciação a.a. do terreno (%)": 6.0,
            "Custos iniciais (% sobre valor)": 3.0,
            "IPTU anual (% do valor de mercado)": 1.0,
            "Despesas fixas mensais (R$)": 200.0
        }
    ])

    column_config = {
        "Nome/ID": st.column_config.TextColumn("Nome/ID", help="Identificação do financiamento/terreno"),
        "Data de compra (YYYY-MM)": st.column_config.TextColumn("Data de compra (YYYY-MM)", help="No formato YYYY-MM (ex.: 2025-01)"),
        "Valor do terreno (R$)": st.column_config.NumberColumn("Valor do terreno (R$)", min_value=0.0, format="%.2f"),
        "Entrada (R$)": st.column_config.NumberColumn("Entrada (R$)", min_value=0.0, format="%.2f"),
        "Juros a.a. (%)": st.column_config.NumberColumn("Juros a.a. (%)", min_value=0.0, format="%.4f"),
        "Prazo (anos)": st.column_config.NumberColumn("Prazo (anos)", min_value=1, format="%d"),
        "Sistema": st.column_config.SelectboxColumn("Sistema", options=["PRICE", "SAC"], required=True),
        "Carência (meses)": st.column_config.NumberColumn("Carência (meses)", min_value=0, format="%d"),
        "Apreciação a.a. do terreno (%)": st.column_config.NumberColumn("Apreciação a.a. do terreno (%)", min_value=0.0, format="%.4f"),
        "Custos iniciais (% sobre valor)": st.column_config.NumberColumn("Custos iniciais (% sobre valor)", min_value=0.0, format="%.4f"),
        "IPTU anual (% do valor de mercado)": st.column_config.NumberColumn("IPTU anual (% do valor de mercado)", min_value=0.0, format="%.4f"),
        "Despesas fixas mensais (R$)": st.column_config.NumberColumn("Despesas fixas mensais (R$)", min_value=0.0, format="%.2f"),
    }

    edited_df = st.data_editor(
        default_data,
        use_container_width=True,
        num_rows="dynamic",
        key="fin_table",
        column_config=column_config
    ).copy()

    params = {
        "horizonte_anos": horizonte_anos,
        "inflacao_anual": inflacao_anual,
        "taxa_desconto_anual": taxa_desconto_anual,
        "estrategia": estrategia,
        "reserva_inicial": reserva_inicial,
        "anos_alternar": anos_alternar,
        "aluguel_inicial": aluguel_inicial,
        "reajuste_anual_aluguel": reajuste_anual_aluguel,
        "vacancia": vacancia,
        "condominio_mensal": condominio_mensal,
        "seguro_mensal": seguro_mensal
    }
    return params, edited_df

def validate_loans_df(df: pd.DataFrame):
    msgs = []
    if df is None or df.empty:
        msgs.append("Nenhum financiamento foi definido na tabela.")
        return msgs

    for idx, row in df.iterrows():
        nome = str(row.get("Nome/ID", f"Item {idx+1}"))
        data_compra = parse_year_month_to_date(row.get("Data de compra (YYYY-MM)", None))
        juros = float(row.get("Juros a.a. (%)", 0.0))
        prazo_anos = int(row.get("Prazo (anos)", 0))
        sistema = str(row.get("Sistema", "PRICE"))
        entrada = float(row.get("Entrada (R$)", 0.0))
        valor = float(row.get("Valor do terreno (R$)", 0.0))

        if data_compra is None:
            msgs.append(f"[{nome}] Data de compra inválida. Use o formato YYYY-MM.")
        if prazo_anos <= 0:
            msgs.append(f"[{nome}] Prazo (anos) deve ser > 0.")
        if juros < 0:
            msgs.append(f"[{nome}] Juros a.a. (%) não pode ser negativo.")
        if sistema.upper() not in ["PRICE", "SAC"]:
            msgs.append(f"[{nome}] Sistema inválido. Use PRICE ou SAC.")
        if entrada < 0 or valor < 0:
            msgs.append(f"[{nome}] Valores não podem ser negativos.")
        if entrada > valor:
            msgs.append(f"[{nome}] Entrada não pode ser maior que o valor do terreno.")

    return msgs

# -----------------------------------------------------
# Estratégia Alternar
# -----------------------------------------------------
def build_alternate_mode_map(start_date: date, total_months: int, years_window: int):
    """
    Mapa de meses -> True (modo Comprar) / False (modo Alugar).
    Inicia em modo Comprar e alterna a cada N anos (years_window).
    """
    mode = []
    block = years_window * 12
    is_buy = True
    for t in range(total_months):
        mode.append(is_buy)
        if (t + 1) % block == 0:
            is_buy = not is_buy
    return np.array(mode, dtype=bool)

# -----------------------------------------------------
# Motor de simulação
# -----------------------------------------------------
def simulate(params: dict, loans_df: pd.DataFrame):
    # Horizonte e timeline
    hoje = first_day_of_month(date.today())
    # Menor data entre compras
    min_purchase_date = None
    if loans_df is not None and not loans_df.empty and params["estrategia"] != "Alugar":
        dates = [parse_year_month_to_date(x) for x in loans_df["Data de compra (YYYY-MM)"].tolist()]
        dates = [d for d in dates if d is not None]
        if len(dates) > 0:
            min_purchase_date = min(dates)

    start_date = min_purchase_date if min_purchase_date is not None else hoje
    horizon_months = params["horizonte_anos"] * 12
    timeline = pd.date_range(start=start_date, periods=horizon_months, freq="MS")

    # Taxas mensais
    inflacao_mensal = (1 + params["inflacao_anual"]) ** (1 / 12.0) - 1.0
    desconto_mensal = (1 + params["taxa_desconto_anual"]) ** (1 / 12.0) - 1.0

    # Estratégia Alternar - mapa de meses
    alt_map = None
    if params["estrategia"] == "Alternar":
        alt_map = build_alternate_mode_map(start_date, horizon_months, params["anos_alternar"])

    included_loans = []
    schedules = {}

    # Sanitização do DF de financiamentos + inclusão condicional
    if loans_df is not None and not loans_df.empty and params["estrategia"] != "Alugar":
        for idx, row in loans_df.iterrows():
            nome = str(row.get("Nome/ID", f"Fin_{idx+1}"))
            data_compra = parse_year_month_to_date(row.get("Data de compra (YYYY-MM)", None))
            if data_compra is None:
                continue
            valor_terreno = float(row.get("Valor do terreno (R$)", 0.0))
            entrada = float(row.get("Entrada (R$)", 0.0))
            juros_aa = float(row.get("Juros a.a. (%)", 0.0)) / 100.0
            prazo_anos = int(row.get("Prazo (anos)", 1))
            sistema = str(row.get("Sistema", "PRICE")).upper()
            carencia = int(row.get("Carência (meses)", 0))
            apr_aa = float(row.get("Apreciação a.a. do terreno (%)", 0.0)) / 100.0
            custos_pct = float(row.get("Custos iniciais (% sobre valor)", 0.0)) / 100.0
            iptu_pct_aa = float(row.get("IPTU anual (% do valor de mercado)", 0.0)) / 100.0
            desp_fixas = float(row.get("Despesas fixas mensais (R$)", 0.0))

            # Regra da estratégia Alternar: só inicia compras em períodos BUY
            include_this = True
            if params["estrategia"] == "Alternar":
                offset = months_between(start_date, data_compra)
                include_this = (0 <= offset < horizon_months) and bool(alt_map[offset])
                # Se start for antes do início da timeline, considerar se é buy no mês 0
                if offset < 0:
                    include_this = bool(alt_map[0])

            if include_this:
                included_loans.append(nome)
                sch = build_loan_schedule(
                    loan_id=nome,
                    start_date=data_compra,
                    principal_value=valor_terreno,
                    down_payment=entrada,
                    annual_rate=juros_aa,
                    years=prazo_anos,
                    system=sistema,
                    grace_months=carencia,
                    annual_appreciation=apr_aa,
                    initial_costs_pct=custos_pct,
                    iptu_pct_year=iptu_pct_aa,
                    monthly_fixed_costs=desp_fixas,
                    timeline_index=timeline,
                    monthly_inflation=inflacao_mensal
                )
                schedules[nome] = sch

    # Agregação mensal
    agg_cols = [
        "Prestacao", "Juros", "Amortizacao", "SaldoDevedor",
        "ValorMercado", "IPTU", "DespesasFixas", "Entrada", "CustosIniciais"
    ]
    monthly = pd.DataFrame(index=timeline)
    for col in agg_cols:
        monthly[col] = 0.0

    if schedules:
        for name, sch in schedules.items():
            for col in agg_cols:
                monthly[col] += sch[col].values

    # Cenário de Aluguel: aplica custos conforme estratégia
    aluguel = np.zeros(len(timeline))
    condominio = np.zeros(len(timeline))
    seguro = np.zeros(len(timeline))

    if params["estrategia"] in ["Alugar", "Alternar"]:
        # Custos de aluguel em períodos correspondentes
        base_aluguel = params["aluguel_inicial"]
        reajuste_aa = params["reajuste_anual_aluguel"]
        vac = params["vacancia"]
        base_condo = params["condominio_mensal"]
        base_seg = params["seguro_mensal"]

        for t in range(len(timeline)):
            # Aplica reajuste anual no aluguel (stepwise a cada 12 meses)
            anos_decorridos = t // 12
            aluguel_bruto = base_aluguel * ((1.0 + reajuste_aa) ** anos_decorridos)
            aluguel_efetivo = aluguel_bruto * (1.0 - vac)
            # Condominio e seguro indexados pela inflação mensal global
            cond_val = base_condo * ((1.0 + inflacao_mensal) ** t)
            seg_val = base_seg * ((1.0 + inflacao_mensal) ** t)

            # No Alternar, só incide aluguel quando no modo "Alugar"
            if params["estrategia"] == "Alternar":
                if not bool(alt_map[t]):
                    aluguel[t] = aluguel_efetivo
                    condominio[t] = cond_val
                    seguro[t] = seg_val
            else:
                # Estratégia "Alugar" sempre
                aluguel[t] = aluguel_efetivo
                condominio[t] = cond_val
                seguro[t] = seg_val

    monthly["Aluguel"] = aluguel
    monthly["Condominio"] = condominio
    monthly["Seguro"] = seguro

    # Totais
    monthly["ValorMercadoTotal"] = monthly["ValorMercado"]
    monthly["SaldoDevedorTotal"] = monthly["SaldoDevedor"]
    monthly["PatrimonioTerrenos"] = monthly["ValorMercadoTotal"] - monthly["SaldoDevedorTotal"]

    # Fluxos de caixa (apenas saídas por ora)
    # Categorias de saída: Entrada, CustosIniciais, Prestacao, IPTU, DespesasFixas, Aluguel, Condominio, Seguro
    monthly["Saidas"] = (
        monthly["Entrada"] + monthly["CustosIniciais"] + monthly["Prestacao"] +
        monthly["IPTU"] + monthly["DespesasFixas"] + monthly["Aluguel"] +
        monthly["Condominio"] + monthly["Seguro"]
    )
    monthly["FluxoCaixa"] = -monthly["Saidas"]

    # Caixa/Reservas (não permitir negativo: clamp em zero e marcar flag)
    caixa = np.zeros(len(timeline))
    deficit = np.zeros(len(timeline))
    neg_flag = np.zeros(len(timeline), dtype=bool)
    caixa_prev = params["reserva_inicial"]
    for t in range(len(timeline)):
        caixa_calc = caixa_prev + monthly["FluxoCaixa"].iloc[t]
        if caixa_calc < 0:
            neg_flag[t] = True
            deficit[t] = -caixa_calc
            caixa[t] = 0.0
            caixa_prev = 0.0
        else:
            caixa[t] = caixa_calc
            caixa_prev = caixa_calc
    monthly["Caixa"] = caixa
    monthly["Deficit"] = deficit
    monthly["CaixaNegativo"] = neg_flag

    # Patrimônio Líquido
    monthly["PatrimonioLiquido"] = monthly["Caixa"] + monthly["PatrimonioTerrenos"]

    # KPIs finais
    final_row = monthly.iloc[-1]
    kpis = {
        "PatrimonioLiquido": float(final_row["PatrimonioLiquido"]),
        "DividaTotal": float(final_row["SaldoDevedorTotal"]),
        "ValorMercadoTerrenos": float(final_row["ValorMercadoTotal"]),
        "PatrimonioTerrenos": float(final_row["PatrimonioTerrenos"]),
        "Caixa": float(final_row["Caixa"])
    }

    # VPL dos fluxos
    flows = monthly["FluxoCaixa"].values.astype(float)
    kpis["VPL"] = float(npv(flows, desconto_mensal))

    # TIR mensal e anual (opcional)
    tir_mensal = irr_bisection(flows)
    kpis["TIR_mensal"] = tir_mensal
    kpis["TIR_anual"] = ((1.0 + tir_mensal) ** 12 - 1.0) if tir_mensal is not None else None

    # Pacote de cronogramas por financiamento (apenas os incluídos)
    loan_schedules = {}
    for name in schedules.keys():
        loan_schedules[name] = schedules[name].copy()

    # Dados auxiliares
    meta = {
        "timeline": timeline,
        "estrategia": params["estrategia"],
        "alt_map": alt_map,
        "desconto_mensal": desconto_mensal,
        "inflacao_mensal": inflacao_mensal
    }

    return monthly, loan_schedules, kpis, meta

# -----------------------------------------------------
# Visualizações
# -----------------------------------------------------
def build_charts(monthly: pd.DataFrame):
    charts = {}

    df_plot = monthly.reset_index().rename(columns={"index": "Data"})
    df_plot["Data"] = pd.to_datetime(df_plot["index"] if "index" in df_plot.columns else df_plot["Data"])

    # 1) Linha: evolução mensal
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_plot["Data"], y=df_plot["PatrimonioLiquido"], name="Patrimônio Líquido", mode="lines"))
    fig_line.add_trace(go.Scatter(x=df_plot["Data"], y=df_plot["SaldoDevedorTotal"], name="Dívida Total", mode="lines"))
    fig_line.add_trace(go.Scatter(x=df_plot["Data"], y=df_plot["ValorMercadoTotal"], name="Valor de Mercado Terrenos", mode="lines"))
    fig_line.add_trace(go.Scatter(x=df_plot["Data"], y=df_plot["Caixa"], name="Caixa/Reservas", mode="lines"))
    fig_line.update_layout(title="Evolução Mensal de Indicadores", hovermode="x unified", yaxis_tickprefix="R$ ")

    charts["linha_evolucao"] = fig_line

    # 2) Barras empilhadas: fluxo de caixa por categorias componentes
    bar_df = df_plot[["Data", "Entrada", "CustosIniciais", "Juros", "Amortizacao", "IPTU", "DespesasFixas", "Aluguel", "Condominio", "Seguro"]].copy()
    # Usar saídas positivas para visual de custos
    for c in ["Entrada", "CustosIniciais", "Juros", "Amortizacao", "IPTU", "DespesasFixas", "Aluguel", "Condominio", "Seguro"]:
        bar_df[c] = bar_df[c].astype(float)

    fig_bar = go.Figure()
    stack_order = ["Entrada", "CustosIniciais", "Juros", "Amortizacao", "IPTU", "DespesasFixas", "Aluguel", "Condominio", "Seguro"]
    for c in stack_order:
        fig_bar.add_trace(go.Bar(x=bar_df["Data"], y=bar_df[c], name=c))
    fig_bar.update_layout(barmode="stack", title="Fluxo de Caixa Mensal por Categoria (Saídas)")
    charts["barras_fluxo"] = fig_bar

    # 3) Donut: composição atual do patrimônio
    last = df_plot.iloc[-1]
    valores = [
        max(0.0, float(last["Caixa"])),
        max(0.0, float(last["PatrimonioTerrenos"])),
        max(0.0, float(last["SaldoDevedorTotal"]))
    ]
    labels = ["Caixa", "Patrimônio Terrenos", "Dívidas"]
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=valores, hole=0.5)])
    fig_donut.update_layout(title="Composição Atual (ativos x dívidas)")
    charts["donut_patrimonio"] = fig_donut

    # 4) Heatmap opcional: meses com caixa negativo flag
    heat = df_plot[["Data", "CaixaNegativo"]].copy()
    heat["Ano"] = heat["Data"].dt.year
    heat["Mes"] = heat["Data"].dt.month
    piv = heat.pivot_table(index="Ano", columns="Mes", values="CaixaNegativo", aggfunc="sum", fill_value=0)
    heat_values = piv.values
    fig_heat = go.Figure(data=go.Heatmap(
        z=heat_values,
        x=[f"{m:02d}" for m in piv.columns],
        y=piv.index.astype(str).tolist(),
        colorscale=[[0, SIGELITE["success"]], [1, SIGELITE["error"]]],
        showscale=False
    ))
    fig_heat.update_layout(title="Mapa de Meses com Caixa Insuficiente (1 = Negativo)", xaxis_title="Mês", yaxis_title="Ano")
    charts["heatmap_caixa"] = fig_heat

    return charts

# -----------------------------------------------------
# Exportação Excel
# -----------------------------------------------------
def export_excel(monthly: pd.DataFrame, loan_schedules: dict) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Resumo mensal
        monthly_out = monthly.copy()
        monthly_out.index.name = "Data"
        monthly_out_reset = monthly_out.reset_index()
        monthly_out_reset.to_excel(writer, sheet_name="Resumo_Mensal", index=False)

        # Formatação
        wb = writer.book
        money_fmt = wb.add_format({"num_format": "R$ #,##0.00"})
        int_fmt = wb.add_format({"num_format": "0"})
        percent_fmt = wb.add_format({"num_format": "0.00%"})
        header_fmt = wb.add_format({"bold": True, "border": 1})

        # Ajuste de colunas e formatação na aba Resumo
        ws = writer.sheets["Resumo_Mensal"]
        for col_idx, col in enumerate(monthly_out_reset.columns):
            maxlen = max(12, min(40, int(monthly_out_reset[col].astype(str).str.len().quantile(0.9))))
            ws.set_column(col_idx, col_idx, maxlen)
            # Formatar monetários
            if col in [
                "Prestacao","Juros","Amortizacao","SaldoDevedor","ValorMercado","IPTU",
                "DespesasFixas","Entrada","CustosIniciais","Aluguel","Condominio","Seguro",
                "ValorMercadoTotal","SaldoDevedorTotal","PatrimonioTerrenos","Saidas",
                "FluxoCaixa","Caixa","Deficit","PatrimonioLiquido"
            ]:
                ws.set_column(col_idx, col_idx, maxlen, money_fmt)
        ws.freeze_panes(1, 1)

        # Abas por financiamento
        if loan_schedules:
            for i, (name, sch) in enumerate(loan_schedules.items(), start=1):
                sheet_name = f"Fin_{i}"
                sch_out = sch.copy()
                sch_out.index.name = "Data"
                sch_out_reset = sch_out.reset_index()
                sch_out_reset.to_excel(writer, sheet_name=sheet_name, index=False)
                wsi = writer.sheets[sheet_name]
                for col_idx, col in enumerate(sch_out_reset.columns):
                    maxlen = max(12, min(40, int(sch_out_reset[col].astype(str).str.len().quantile(0.9))))
                    wsi.set_column(col_idx, col_idx, maxlen)
                    if col in ["Prestacao","Juros","Amortizacao","SaldoDevedor","ValorMercado","IPTU","DespesasFixas","Entrada","CustosIniciais"]:
                        wsi.set_column(col_idx, col_idx, maxlen, money_fmt)
                wsi.freeze_panes(1, 1)

    return output.getvalue()

# -----------------------------------------------------
# Tabelas formatadas para UI
# -----------------------------------------------------
def format_monthly_for_display(monthly: pd.DataFrame) -> pd.DataFrame:
    df = monthly.copy()
    df_disp = pd.DataFrame({
        "Data": df.index.strftime("%Y-%m"),
        "Caixa": df["Caixa"].apply(format_currency_br),
        "FluxoCaixa": df["FluxoCaixa"].apply(format_currency_br),
        "ValorMercadoTotal": df["ValorMercadoTotal"].apply(format_currency_br),
        "SaldoDevedorTotal": df["SaldoDevedorTotal"].apply(format_currency_br),
        "PatrimonioTerrenos": df["PatrimonioTerrenos"].apply(format_currency_br),
        "PatrimonioLiquido": df["PatrimonioLiquido"].apply(format_currency_br),
        "CaixaNegativo": df["CaixaNegativo"].map({True: "Sim", False: "Não"})
    })
    return df_disp

def format_schedule_for_display(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "Mês": df.index.strftime("%Y-%m"),
        "Prestação": df["Prestacao"].apply(format_currency_br),
        "Juros": df["Juros"].apply(format_currency_br),
        "Amortização": df["Amortizacao"].apply(format_currency_br),
        "Saldo Devedor": df["SaldoDevedor"].apply(format_currency_br),
        "Valor de Mercado": df["ValorMercado"].apply(format_currency_br),
        "IPTU": df["IPTU"].apply(format_currency_br),
        "Despesas Fixas": df["DespesasFixas"].apply(format_currency_br),
    })
    # Entrada e custos iniciais somente se ocorrerem (mostramos para transparência)
    out["Entrada"] = df["Entrada"].apply(format_currency_br)
    out["Custos Iniciais"] = df["CustosIniciais"].apply(format_currency_br)
    return out

# -----------------------------------------------------
# UI principal
# -----------------------------------------------------
def show_kpis(kpis: dict):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Patrimônio Líquido", format_currency_br(kpis.get("PatrimonioLiquido", 0.0)))
    with col2:
        st.metric("Dívida Total", format_currency_br(kpis.get("DividaTotal", 0.0)))
    with col3:
        st.metric("Valor de Mercado Terrenos", format_currency_br(kpis.get("ValorMercadoTerrenos", 0.0)))
    with col4:
        st.metric("Patrimônio Terrenos", format_currency_br(kpis.get("PatrimonioTerrenos", 0.0)))
    with col5:
        st.metric("Caixa/Reservas", format_currency_br(kpis.get("Caixa", 0.0)))
    with col6:
        st.metric("VPL (fluxos)", format_currency_br(kpis.get("VPL", 0.0)))

def main():
    st.title("Simulador de Investimentos Imobiliários")
    st.caption("Para iniciar, preencha os parâmetros, adicione seus financiamentos e clique em Rodar Simulação.")

    params, loans_df = build_inputs()

    # Validações de entrada
    warnings = []
    if params["estrategia"] != "Alugar":
        warnings.extend(validate_loans_df(loans_df))
    if len(warnings) > 0:
        for w in warnings:
            st.warning(w)

    c1, c2 = st.columns([1, 1])
    with c1:
        run = st.button("Rodar Simulação", type="primary", use_container_width=True)
    with c2:
        export_pressed = st.button("Exportar Excel", use_container_width=True, disabled=True)

    if "sim_results" not in st.session_state:
        st.session_state.sim_results = None

    # Rodar simulação
    if run:
        monthly, schedules, kpis, meta = simulate(params, loans_df)
        st.session_state.sim_results = {
            "monthly": monthly,
            "schedules": schedules,
            "kpis": kpis,
            "meta": meta,
            "params": params,
            "loans_df": loans_df
        }

    # Exibir resultados caso existam
    if st.session_state.sim_results is not None:
        monthly = st.session_state.sim_results["monthly"]
        schedules = st.session_state.sim_results["schedules"]
        kpis = st.session_state.sim_results["kpis"]
        meta = st.session_state.sim_results["meta"]
        params_state = st.session_state.sim_results["params"]
        loans_df_state = st.session_state.sim_results["loans_df"]

        # KPIs
        st.subheader("KPIs")
        show_kpis(kpis)

        # Tabs
        tabs = st.tabs(["KPIs", "Gráficos", "Tabelas", "Cronogramas", "Configurações"])
        with tabs[0]:
            st.markdown("Indicadores calculados ao final do horizonte de simulação. O VPL usa a taxa de desconto informada, com base mensal.")
            # Exibir TIR se existir
            cA, cB, cC = st.columns(3)
            with cA:
                tir_m = st.session_state.sim_results["kpis"].get("TIR_mensal", None)
                st.metric("TIR (mensal)", f"{tir_m*100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".") if tir_m is not None else "—")
            with cB:
                tir_a = st.session_state.sim_results["kpis"].get("TIR_anual", None)
                st.metric("TIR (anual)", f"{tir_a*100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".") if tir_a is not None else "—")
            with cC:
                neg_count = int((monthly["CaixaNegativo"] == True).sum())
                st.metric("Meses com caixa insuficiente", f"{neg_count} mês(es)")

        with tabs[1]:
            charts = build_charts(monthly)
            st.plotly_chart(charts["linha_evolucao"], use_container_width=True)
            st.plotly_chart(charts["barras_fluxo"], use_container_width=True)
            st.plotly_chart(charts["donut_patrimonio"], use_container_width=True)
            st.plotly_chart(charts["heatmap_caixa"], use_container_width=True)

        with tabs[2]:
            st.subheader("Resumo Mensal")
            df_disp = format_monthly_for_display(monthly)
            st.dataframe(df_disp, use_container_width=True, height=420)
            with st.expander("Filtros e detalhes"):
                colf1, colf2 = st.columns(2)
                with colf1:
                    show_neg_only = st.checkbox("Mostrar apenas meses com caixa insuficiente", value=False)
                with colf2:
                    show_last_12 = st.checkbox("Mostrar apenas últimos 12 meses", value=False)
                df_filter = monthly.copy()
                if show_neg_only:
                    df_filter = df_filter[df_filter["CaixaNegativo"] == True]
                if show_last_12 and len(df_filter) > 12:
                    df_filter = df_filter.iloc[-12:]
                st.write("Linhas filtradas (numéricas):")
                st.dataframe(df_filter, use_container_width=True, height=300)

        with tabs[3]:
            st.subheader("Cronogramas por Financiamento")
            if schedules:
                for i, (name, sch) in enumerate(schedules.items(), start=1):
                    with st.expander(f"{i}. {name}", expanded=False):
                        sch_disp = format_schedule_for_display(sch)
                        st.dataframe(sch_disp, use_container_width=True, height=350)
            else:
                st.info("Nenhum financiamento incluído nesta simulação (estratégia 'Alugar' ou filtros da estratégia Alternar).")

        with tabs[4]:
            st.subheader("Configurações Utilizadas")
            colx, coly = st.columns(2)
            with colx:
                st.write("Parâmetros Globais")
                params_table = pd.DataFrame({
                    "Parâmetro": [
                        "Horizonte (anos)","Inflação anual (%)","Taxa de desconto anual (%)",
                        "Estratégia","Reserva de caixa inicial (R$)","Alternar a cada N anos",
                        "Aluguel inicial (R$)","Reajuste anual aluguel (%)","Vacância (%)","Condomínio (R$)","Seguro (R$)"
                    ],
                    "Valor": [
                        params_state["horizonte_anos"],
                        f"{params_state['inflacao_anual']*100:.2f}%",
                        f"{params_state['taxa_desconto_anual']*100:.2f}%",
                        params_state["estrategia"],
                        format_currency_br(params_state["reserva_inicial"]),
                        params_state["anos_alternar"] if params_state["estrategia"]=="Alternar" else "—",
                        format_currency_br(params_state["aluguel_inicial"]),
                        f"{params_state['reajuste_anual_aluguel']*100:.2f}%",
                        f"{params_state['vacancia']*100:.2f}%",
                        format_currency_br(params_state["condominio_mensal"]),
                        format_currency_br(params_state["seguro_mensal"])
                    ]
                })
                st.dataframe(params_table, use_container_width=True, hide_index=True)
            with coly:
                st.write("Terrenos e Financiamentos (dados de entrada)")
                st.dataframe(loans_df_state, use_container_width=True, height=300)

        # Habilitar exportação
        st.session_state.export_bytes = export_excel(monthly, schedules)
        st.download_button(
            label="Exportar Excel",
            data=st.session_state.export_bytes,
            file_name="simulacao_imobiliaria.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    else:
        st.info("Defina os parâmetros e clique em 'Rodar Simulação' para ver os resultados.")

if __name__ == "__main__":
    main()
