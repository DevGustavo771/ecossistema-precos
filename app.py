import streamlit as st
import pandas as pd

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Ecossistema de Preços",
    layout="wide"
)

# =============================
# BASE DE PRODUTOS
# =============================
PRODUTOS_PARAMETROS = {
    "UNIMED EXECUTIVO": 2.288633433,
    "UNIMED EXECUTIVO COMFORT": 2.041152113,
    "UNIMED EXECUTIVO PREMIUM": 2.524444286,
    "UNIMED NACIONAL REDE BASICA": 1.179901365,
    "UNIMED NACIONAL REDE ESPECIAL": 1.651776142,
    "UNIMED PLENO 80": 1.165320563,
    "UNIMED PLENO 100": 1.650346651,
    "UNIMED PLENO 200": 1.741369452,
    "CORPORATIVO SUPERIOR APTO": 1.826545754,
}

# =============================
# FUNÇÃO DE PONTO DE EQUILÍBRIO
# =============================
def obter_ponto_equilibrio(vidas):
    if vidas <= 199:
        return 0.75
    elif vidas <= 499:
        return 0.78
    elif vidas <= 999:
        return 0.80
    else:
        return 0.82

# =============================
# FUNÇÃO CENTRAL DE RECÁLCULO
# =============================
def recalcular_reajustes(df):
    df = df.copy()

    df["sinistralidade"] = (
        df["custo_assistencial_liquido"] / df["receita_assistencial"]
    )

    df["reajuste_meta"] = (
        (
            df["custo_assistencial_liquido"]
            - df["ajuste_mv"]
            - df["expurgo"]
        )
        / df["receita_assistencial"]
        / 0.75
    ) * (1 + df["indice_financeiro"]) - 1

    df["reajuste_meta"] = df[
        ["reajuste_meta", "indice_financeiro"]
    ].max(axis=1)

    df["reajuste_comercial"] = (
        (
            df["custo_assistencial_liquido"]
            - df["ajuste_mv"]
            - df["expurgo"]
        )
        / df["receita_assistencial"]
        / df["ponto_equilibrio"]
    ) * (1 + df["indice_financeiro"]) - 1

    df["reajuste_comercial"] = df[
        ["reajuste_comercial", "indice_financeiro"]
    ].max(axis=1)

    return df

# =============================
# ORDEM FINAL DAS COLUNAS
# =============================
ORDEM_COLUNAS = [
    "id_corporacao",
    "empresa",
    "vidas",
    "receita_assistencial",
    "custo_assistencial_liquido",
    "ajuste_mv",
    "expurgo",
    "sinistralidade",
    "indice_financeiro",
    "ponto_equilibrio",
    "reajuste_meta",
    "reajuste_comercial"
]

# =============================
# HEADER
# =============================
st.markdown("""
<h1 style='color:#2e7d32;'>Ecossistema de Preços & Reajustes</h1>
<hr>
""", unsafe_allow_html=True)

# =============================
# TABS
# =============================
tab_pricing, tab_arquivos = st.tabs([
    "💰 Pricing",
    "📂 Reajuste por Arquivos"
])

# =============================
# TAB PRICING
# =============================
with tab_pricing:
    col1, col2, col3 = st.columns(3)

    produto = col1.selectbox("Produto", list(PRODUTOS_PARAMETROS.keys()))
    valor_base = col2.number_input("Valor base (R$)", min_value=0.0, step=100.0)
    qtd_vidas = col3.number_input("Quantidade de vidas", min_value=1)

    preco_ajustado = valor_base * PRODUTOS_PARAMETROS[produto]
    margem = 1 - 0.15 - obter_ponto_equilibrio(qtd_vidas)

    st.metric("Preço Ajustado", f"R$ {preco_ajustado:,.2f}")
    st.metric("Margem", f"{margem:.2%}")

# =============================
# TAB ARQUIVOS
# =============================
with tab_arquivos:

    base_12m = st.file_uploader("Upload base_12m.xlsx", type=["xlsx"])
    reajuste_file = st.file_uploader("Upload Reajuste_MMYYYY.csv", type=["csv"])

    # ==================================================
    # PROCESSAMENTO DOS ARQUIVOS
    # ==================================================
    if base_12m and reajuste_file:

        # ---------- BASE 12M ----------
        df_base = pd.read_excel(base_12m)

        df_base.columns = (
            df_base.columns.str.strip().str.lower()
            .str.replace(" ", "_")
            .str.replace("ç", "c")
            .str.replace("ã", "a")
            .str.replace("á", "a")
            .str.replace("é", "e")
            .str.replace("í", "i")
            .str.replace("ó", "o")
            .str.replace("ú", "u")
        )

        df_base_sel = df_base[
            ["id_contrato", "id_corporacao", "receita_assistencial", "custo_assistencial_liquido"]
        ]

        df_base_corp = (
            df_base_sel
            .groupby("id_corporacao", as_index=False)
            .agg({
                "receita_assistencial": "sum",
                "custo_assistencial_liquido": "sum"
            })
        )

        # ---------- CSV REAJUSTE ----------
        df_reaj = pd.read_csv(reajuste_file, sep=";", encoding="latin1")

        df_reaj.columns = (
            df_reaj.columns.str.strip().str.lower()
            .str.replace(" ", "_")
            .str.replace("ç", "c")
            .str.replace("ã", "a")
            .str.replace("á", "a")
            .str.replace("é", "e")
            .str.replace("í", "i")
            .str.replace("ó", "o")
            .str.replace("ú", "u")
        )

        df_reaj_sel = df_reaj[[
            "codigo_contrato",
            "empresa",
            "total_usuarios_coletivo",
            "total_usuarios_privativo",
            "reajuste_financeiro"
        ]].rename(columns={
            "codigo_contrato": "id_contrato",
            "reajuste_financeiro": "indice_financeiro"
        })

        df_reaj_sel["vidas"] = (
            df_reaj_sel["total_usuarios_coletivo"].fillna(0)
            + df_reaj_sel["total_usuarios_privativo"].fillna(0)
        )

        df_reaj_sel["indice_financeiro"] = df_reaj_sel["indice_financeiro"] / 100

        contrato_corp = df_base_sel[["id_contrato", "id_corporacao"]].drop_duplicates()

        df_reaj_corp = (
            df_reaj_sel
            .merge(contrato_corp, on="id_contrato", how="inner")
            .groupby("id_corporacao", as_index=False)
            .agg({
                "empresa": "first",
                "vidas": "sum",
                "indice_financeiro": "mean"
            })
        )

        df_reaj_corp["ponto_equilibrio"] = df_reaj_corp["vidas"].apply(obter_ponto_equilibrio)

        # ---------- MERGE FINAL ----------
        df_corp = df_base_corp.merge(df_reaj_corp, on="id_corporacao", how="inner")

        df_corp["ajuste_mv"] = 0.0
        df_corp["expurgo"] = 0.0

        df_corp = recalcular_reajustes(df_corp)
        df_corp = df_corp[ORDEM_COLUNAS]

        st.session_state["df_corp"] = df_corp.copy()

        st.subheader("📊 Resultado por Corporação")
        st.dataframe(df_corp, use_container_width=True)

# ==================================================
# AJUSTES MANUAIS (COM FORM)
# ==================================================
df_corp = st.session_state.get("df_corp")

if df_corp is not None:

    df_corp["elegivel_ajuste"] = (
        (df_corp["reajuste_meta"] >= 0.15) &
        (df_corp["vidas"] >= 200)
    )

    df_ajustes_base = df_corp.loc[
        df_corp["elegivel_ajuste"],
        ["id_corporacao", "empresa", "ajuste_mv", "expurgo"]
    ].copy()

    st.subheader("✏️ Ajustes Manuais (MV e Expurgo)")
    st.caption("Somente corporações com reajuste meta ≥ 15% e ≥ 200 vidas.")

    with st.form("form_ajustes"):
        df_ajustes = st.data_editor(
            df_ajustes_base,
            num_rows="fixed",
            use_container_width=True
        )

        submitted = st.form_submit_button("🔄 Recalcular com Ajustes Manuais")

    if submitted:

        df_corp = df_corp.merge(
            df_ajustes,
            on=["id_corporacao", "empresa"],
            how="left",
            suffixes=("", "_edit")
        )

        df_corp["ajuste_mv"] = df_corp["ajuste_mv_edit"].fillna(df_corp["ajuste_mv"])
        df_corp["expurgo"] = df_corp["expurgo_edit"].fillna(df_corp["expurgo"])

        df_corp.drop(
            columns=["ajuste_mv_edit", "expurgo_edit"],
            inplace=True
        )

        df_corp = recalcular_reajustes(df_corp)
        df_corp = df_corp[ORDEM_COLUNAS]

        st.session_state["df_corp"] = df_corp.copy()

        st.success("Reajustes recalculados com sucesso ✅")
        st.dataframe(df_corp, use_container_width=True)
