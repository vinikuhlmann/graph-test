import pandas as pd
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config, ConfigBuilder

st.set_page_config(layout="wide")


def get_score(row):
    multiplier = 1
    if any(role in row["Cargo"].lower() for role in ["ceo", "cfo"]):
        multiplier = 5
    elif any(
        role in row["Cargo"].lower()
        for role in [
            "diretor",
            "gerente",
            "director",
            "socio",
            "chief",
            "partner",
            "owner",
        ]
    ):
        multiplier = 3
    elif any(
        role in row["Cargo"].lower()
        for role in ["coordenaor", "analista", "assistente", "pleno"]
    ):
        multiplier = 2

    return multiplier * 1 + (
        (1 if row["Convite Linkedin Enviado"] == "Sim" else 0)
        + (1 if row["Snovio Enviado ?"] == "Sim" else 0)
        + (3 if row["Já é Conexão Linkedin?"] == "Sim" else 0)
    )


if "df" not in st.session_state:
    filepath = "/home/vinikuhlmann/Desktop/graph-test/Planilha exemplo pessoas.csv"
    df = pd.read_csv(filepath)
    df["Nome completo"] = df["Nome"] + " " + df["Sobrenome"]
    df.drop(columns=["Nome", "Sobrenome"], inplace=True)
    df["Score"] = df.apply(get_score, axis=1)
    st.session_state.df = df

df = st.session_state.df
df = df.copy()

# Session state values to track the order of filter selection
if "confirmed" not in st.session_state:
    st.session_state.confirmed = []
    st.session_state.last_edited = None


def last_edited(i, col):
    """Update session state values to track order of editing

    i:int
        index of the column that was last edited
    col:str
        name of the column that was last edited
    """
    if st.session_state.last_edited is None:  # Nothing was previously selected/edited
        st.session_state.last_edited = (i, col)
        return
    if st.session_state.last_edited == (i, col):  # The same column was last edited
        undo(col)
        return
    # Some other column was last edited:
    confirmed(*st.session_state.last_edited)
    st.session_state.last_edited = (i, col)
    return


def undo(col):
    """Undoes the last confirmation if the last edit was to clear a filter

    col : str
        name of the column that was last edited
    """
    if st.session_state["col_" + col] == []:  # Check state of widget by key
        last_confirmed = safe_pop(st.session_state.confirmed, -1)
        st.session_state.last_edited = last_confirmed


def safe_pop(lst, i):
    """Pops the ith element of a list, returning None if the index is out of bounds

    lst : list
        list to pop from
    i : int
        index to pop
    """
    try:
        return lst.pop(i)
    except IndexError:
        return None


def confirmed(i, col):
    """Adds the last edited column to the confirmed list

    i:int
        index of the column that was last edited
    col:str
        name of the column that was last edited
    """
    st.session_state.confirmed.append((i, col))


# Columns to display the filters (Streamlit with create multiselect widgets
# according to the order of user edits, but columns will keep them displaying
# in their original order for the user)
st.markdown("## Grafo")
cols = st.columns(4)
selected_cols = ["Nome da empresa", "Cargo"]
selected = {col: [] for col in selected_cols}

# Confirmed filters
for i, col in st.session_state.confirmed:
    selected[col] = cols[i].multiselect(
        col,
        df[col].unique(),
        key=f"col_{col}",
        on_change=last_edited,
        args=[i, col],
        disabled=True,
    )
    df = df[df[col].isin(selected[col])]

# Currently editing
if st.session_state.last_edited is not None:
    i, col = st.session_state.last_edited
    selected[col] = cols[i].multiselect(
        col,
        df[col].unique(),
        key=f"col_{col}",
        on_change=last_edited,
        args=[i, col],
    )
    df = df[df[col].isin(selected[col])]

# Not yet edited filters
for i, col in enumerate(selected_cols):
    if (i, col) not in st.session_state.confirmed and (
        i,
        col,
    ) != st.session_state.last_edited:
        selected[col] = cols[i].multiselect(
            col,
            df[col].unique(),
            key=f"col_{col}",
            on_change=last_edited,
            args=[i, col],
        )
    if selected[col] != []:
        df = df[df[col].isin(selected[col])]


min_score = cols[3].number_input("Score mínimo", min_value=0, value=0)


def get_graph():
    nodes = [Node(id="root", label="root", size=1, group="root")]
    edges = []
    score_empresas = df.groupby("Nome da empresa")["Score"].max().to_dict()
    score_cargos = df.groupby(["Nome da empresa", "Cargo"])["Score"].max().to_dict()
    for empresa, score in score_empresas.items():
        if score < min_score:
            continue
        nodes.append(
            Node(
                id=empresa,
                label=f"{empresa}\n(max score={score})",
                size=score,
                group=empresa,
            )
        )
        edges.append(Edge(source="root", target=empresa))
    for (empresa, cargo), score in score_cargos.items():
        if score < min_score:
            continue
        nodes.append(
            Node(
                id="@".join((empresa, cargo)),
                label=f"{cargo}\n(max score={score})",
                size=score,
                group=empresa,
            )
        )
        edges.append(Edge(source=empresa, target="@".join((empresa, cargo))))
    for row in df.to_dict(orient="records"):
        if row["Score"] < min_score:
            continue
        nodes.append(
            Node(
                id=row["Nome completo"],
                label=f"{row['Nome completo']}\n(score={row['Score']})",
                size=row["Score"],
                group=row["Cargo"],
            )
        )
        edges.append(
            Edge(
                source="@".join((row["Nome da empresa"], row["Cargo"])),
                target=row["Nome completo"],
            )
        )

    return nodes, edges


mode = cols[2].selectbox("Tipo de grafo", ["Radial", "Hierárquico"])
nodes, edges = get_graph()

# config_builder = ConfigBuilder(nodes)
# config = config_builder.build()
# config.save("config.json")
config = (
    Config(from_json="radial_config.json")
    if mode == "Radial"
    else Config(from_json="hierarchical_config.json")
)
with st.container(border=True):
    agraph(nodes=nodes, edges=edges, config=config)

st.markdown("## Dados filtrados")
st.write(df)
