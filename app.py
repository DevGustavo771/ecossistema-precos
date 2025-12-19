import streamlit as st
import pandas as pd

# =============================
# AUTENTICAÇÃO
# =============================
SENHA_CORRETA = "unimed@2025"  # esconder no github

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acesso Restrito")
    st.caption("Informe a senha para acessar o Ecossistema de Preços")

    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if senha == SENHA_CORRETA:
            st.session_state["autenticado"] = True
            st.success("Acesso liberado ✅")
            st.rerun()
        else:
            st.error("Senha incorreta ❌")

    st.stop()  # ⛔ trava o restante do app


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
# BASE DE CUSTO MÉDIO (CM)
# =============================
BASE_CM = pd.DataFrame({
    "faixa_etaria": [
        "0-18", "19-23", "24-28", "29-33", "34-38",
        "39-43", "44-48", "49-53", "54-58", "59-999"
    ],
    "cm_masculino": [
        350.57, 154.03, 187.26, 219.73, 236.74,
        277.15, 353.56, 400.63, 570.91, 1074.40
    ],
    "cm_feminino": [
        246.35, 234.78, 335.68, 386.81, 401.83,
        457.36, 501.02, 561.06, 615.32, 1058.30
    ]
})


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

    df["fatmodproj"] = (
        df["valor_receita_faturada_fator_moderador_esp017"].replace(0, pd.NA)
        / df["custo_assistencial_bruto"].replace(0, pd.NA)
    ) * df["custo_projetado"]

    df["reaj_preco"] = (
        (
            (df["custo_projetado"].replace(0, pd.NA)
             - df["fatmodproj"].replace(0, pd.NA))
            / df["receita_sem_reajuste"].replace(0, pd.NA)
        )
        / pd.Series(0.75, index=df.index).replace(0, pd.NA)
    ) - 1

    df["reaj_preco"] = df[
        ["reaj_preco", "indice_financeiro"]
    ].max(axis=1)

    df["reajuste_meta"] = (
        (
            (
                df["custo_assistencial_liquido"]
                - df["ajuste_mv"]
                - df["expurgo"]
            )
            / df["receita_assistencial"]
            / 0.75
        ) * (1 + df["indice_financeiro"]) - 1
    )

    df["reajuste_meta"] = df[
        ["reajuste_meta", "indice_financeiro"]
    ].max(axis=1)

    df["reajuste_comercial"] = (
        (
            (
                df["custo_assistencial_liquido"]
                - df["ajuste_mv"]
                - df["expurgo"]
            )
            / df["receita_assistencial"]
            / df["ponto_equilibrio"]
        ) * (1 + df["indice_financeiro"]) - 1
    )

    df["reajuste_comercial"] = df[
        ["reajuste_comercial", "indice_financeiro"]
    ].max(axis=1)

    return df


# =============================
# ORDEM DAS COLUNAS
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
    "reajuste_comercial",
    "reaj_preco"
]

# "valor_receita_faturada_fator_moderador_esp017",
# "custo_assistencial_bruto",
# "receita_sem_reajuste",
# "custo_projetado"

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
    usr_file = st.file_uploader("Upload usr_MMYY.csv", type=["csv"])

    # ==================================================
    # PROCESSAMENTO DOS ARQUIVOS
    # ==================================================
    if base_12m and reajuste_file and usr_file:

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
            ["id_contrato", "id_corporacao", "receita_assistencial",
             "custo_assistencial_liquido", "custo_assistencial_bruto",
             "valor_receita_faturada_fator_moderador_esp017"]
        ]

        df_base_corp = (
            df_base_sel
            .groupby("id_corporacao", as_index=False)
            .agg({
                "receita_assistencial": "sum",
                "custo_assistencial_liquido": "sum",
                "custo_assistencial_bruto": "sum",
                "valor_receita_faturada_fator_moderador_esp017": "sum"
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

        # ---------- CSV USUÁRIOS (USR_MMYY) ----------
        df_usr = pd.read_csv(usr_file, sep=";", encoding="latin1")

        # Padroniza colunas
        df_usr.columns = (
            df_usr.columns.str.strip().str.lower()
            .str.replace(" ", "_")
            .str.replace("ç", "c")
            .str.replace("ã", "a")
            .str.replace("á", "a")
            .str.replace("é", "e")
            .str.replace("í", "i")
            .str.replace("ó", "o")
            .str.replace("ú", "u")
        )

        df_usr = df_usr[[
            "id_corporacao_contrato",
            "descricao_tipo_sexo",
            "descricao_faixa_etaria_10_faixas",
            "qtd_usuarios_ativos_ultimo_dia_competencia"
        ]].rename(columns={
            "id_corporacao_contrato": "id_corporacao",
            "descricao_tipo_sexo": "sexo",
            "descricao_faixa_etaria_10_faixas": "faixa_etaria",
            "qtd_usuarios_ativos_ultimo_dia_competencia": "qtd_usuarios"
        })

        # ---------- NORMALIZA SEXO ----------
        df_usr["sexo"] = (
            df_usr["sexo"]
            .str.upper()
            .str.strip()
        )

        # ---------- MAPA DE FAIXA ETÁRIA ----------
        mapa_faixa = {
            "0 A 18": "0-18",
            "19 A 23": "19-23",
            "24 A 28": "24-28",
            "29 A 33": "29-33",
            "34 A 38": "34-38",
            "39 A 43": "39-43",
            "44 A 48": "44-48",
            "49 A 53": "49-53",
            "54 A 58": "54-58",
            "ACIMA DE 59": "59-999"
        }

        df_usr["faixa_etaria"] = (
            df_usr["faixa_etaria"]
            .str.upper()
            .str.strip()
            .map(mapa_faixa)
        )

        # Remove registros sem faixa válida
        df_usr = df_usr.dropna(subset=["faixa_etaria"])

        # ---------- MERGE COM BASE CM ----------
        df_usr = df_usr.merge(
            BASE_CM,
            on="faixa_etaria",
            how="left"
        )

        # ---------- ESCOLHA DO CM POR SEXO ----------
        df_usr["cm_utilizado"] = df_usr.apply(
            lambda x: x["cm_masculino"]
            if x["sexo"] == "MASCULINO"
            else x["cm_feminino"],
            axis=1
        )

        # ---------- CUSTO PROJETADO ----------
        df_usr["custo_projetado"] = (
            df_usr["qtd_usuarios"]
            * df_usr["cm_utilizado"]
            * 12
        )

        # ---------- AGREGA POR CORPORAÇÃO ----------
        df_custo_proj = (
            df_usr
            .groupby("id_corporacao", as_index=False)
            .agg({
                "custo_projetado": "sum"
            })
        )

        # =============================
        # RECEITA SEM REAJUSTE (CSV)
        # =============================
        df_reaj_receita = df_reaj[[
            "codigo_contrato",
            "vigente_coletivo",
            "vigente_privativo",
            "total_usuarios_coletivo",
            "total_usuarios_privativo"
        ]].rename(columns={
            "codigo_contrato": "id_contrato"
        })

        cols_valores = [
            "vigente_coletivo",
            "vigente_privativo",
            "total_usuarios_coletivo",
            "total_usuarios_privativo"
        ]

        df_reaj_receita[cols_valores] = (
            df_reaj_receita[cols_valores]
            .fillna(0)
            .astype(float)
        )

        df_reaj_receita["receita_sem_reajuste"] = 12 * ((
            df_reaj_receita["vigente_coletivo"]
            * df_reaj_receita["total_usuarios_coletivo"]
        ) + (
            df_reaj_receita["vigente_privativo"]
            * df_reaj_receita["total_usuarios_privativo"]
        ))

        df_reaj_sel["vidas"] = (
            df_reaj_sel["total_usuarios_coletivo"].fillna(0)
            + df_reaj_sel["total_usuarios_privativo"].fillna(0)
        )

        df_reaj_sel["indice_financeiro"] = df_reaj_sel["indice_financeiro"] / 100

        contrato_corp = df_base_sel[["id_contrato", "id_corporacao"]].drop_duplicates()

        df_reaj_receita = df_reaj_receita.merge(
            contrato_corp,
            on="id_contrato",
            how="inner"
        )

        df_receita_corp = (
            df_reaj_receita
            .groupby("id_corporacao", as_index=False)
            .agg({
                "receita_sem_reajuste": "sum"
            })
        )

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

        df_corp = df_corp.merge(
            df_receita_corp,
            on="id_corporacao",
            how="left"
        )
        df_corp = df_corp.merge(
            df_custo_proj,
            on="id_corporacao",
            how="left"
        )

         # ... (código anterior de merges e preparação) ...

        df_corp["ajuste_mv"] = 0.0
        df_corp["expurgo"] = 0.0

         # 1. Calcula os reajustes iniciais
        df_corp = recalcular_reajustes(df_corp)
    
       # ---------------------------------------------------------
       # CORREÇÃO 1: SALVAR O DATAFRAME COMPLETO (SEM FILTRAR)
       # ---------------------------------------------------------
       # Não fazemos df_corp = df_corp[ORDEM_COLUNAS] aqui!
       # Salvamos ele "sujo" (com todas as colunas de cálculo)
        st.session_state["df_corp"] = df_corp.copy()

        st.subheader("📊 Resultado por Corporação")
    
       # Filtramos APENAS na hora de mostrar na tela
        st.dataframe(df_corp[ORDEM_COLUNAS], use_container_width=True)

       # ==================================================
       # AJUSTES MANUAIS (COM FORM)
       # ==================================================
       # Recupera o DataFrame COMPLETO (com as colunas de cálculo) da memória
df_corp_full = st.session_state.get("df_corp")

if df_corp_full is not None:

    # Usa o df completo para calcular elegibilidade
    df_corp_full["elegivel_ajuste"] = (
        (df_corp_full["reajuste_meta"] >= 0.15) &
        (df_corp_full["vidas"] >= 200)
    )

    df_ajustes_base = df_corp_full.loc[
        df_corp_full["elegivel_ajuste"],
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
        # Faz o merge no DataFrame COMPLETO
        df_corp_full = df_corp_full.merge(
            df_ajustes,
            on=["id_corporacao", "empresa"],
            how="left",
            suffixes=("", "_edit")
        )

        # Atualiza valores
        df_corp_full["ajuste_mv"] = df_corp_full["ajuste_mv_edit"].fillna(df_corp_full["ajuste_mv"])
        df_corp_full["expurgo"] = df_corp_full["expurgo_edit"].fillna(df_corp_full["expurgo"])

        df_corp_full.drop(
            columns=["ajuste_mv_edit", "expurgo_edit"],
            inplace=True
        )

        # ---------------------------------------------------------
        # CORREÇÃO 2: RECALCULAR COM A BASE COMPLETA
        # ---------------------------------------------------------
        # Agora funciona, pois df_corp_full ainda tem 'custo_projetado', etc.
        df_corp_full = recalcular_reajustes(df_corp_full)
        
        # Atualiza o Session State com a nova versão COMPLETA
        st.session_state["df_corp"] = df_corp_full.copy()

        st.success("Reajustes recalculados com sucesso ✅")
        
        # Filtra APENAS na visualização final
        st.dataframe(df_corp_full[ORDEM_COLUNAS], use_container_width=True)
