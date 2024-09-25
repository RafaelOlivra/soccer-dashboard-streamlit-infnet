import time
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import pandas as pd
import plotly.express as px
import pydeck as pdk
import time
import numpy as np
import locale

############## CONFIG ##############

# Set locale for number formatting
locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")

# Set page config
st.set_page_config(
    page_title="StatsBombPy",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="auto",
)

############## SESSION STATE FUNCTIONS ##############

if "data" not in st.session_state:
    st.session_state.data = None

if "current_view" not in st.session_state:
    st.session_state.current_view = 0

if "current_explore_view" not in st.session_state:
    st.session_state.current_explore_view = "Explorador"

############## UTIL FUNCTIONS ##############


def format_number(number):
    # Convert to number if necessary
    if isinstance(number, str):
        number = int(number)
    return locale.format_string("%d", number, grouping=True)


############## DATA FUNCTIONS ##############


@st.cache_data
def get_csv_content(csv_file):
    df = pd.read_csv(csv_file)
    return df.to_csv(index=False)


def get_data():
    return st.session_state.data


def set_data(data):
    # Make sure Ano is a string
    if data is not None and "Ano" in data.columns:
        data["Ano"] = data["Ano"].astype(str)
    st.session_state.data = data


def get_available_views():
    return ["Upload dos Dados", "Explorar", "Customizar", "Sobre"]


def get_current_view():
    current_view = st.session_state.current_view
    return current_view or get_available_views()[0]


def get_current_view_index():
    return get_available_views().index(get_current_view())


def set_current_view(view):
    st.session_state.current_view = view


def get_available_explore_views():
    return ["Explorador", "Editor"]


def get_current_explore_view():
    current_explore_view = st.session_state.current_explore_view
    return current_explore_view or get_available_explore_views()[0]


def get_current_explore_view_index():
    return get_available_explore_views().index(get_current_explore_view())


############## PLOTS & GRAPHS ##############

############## VIEWS ##############


### EXPLORE ###
def view_explore():
    st.title("🔍 Explorar")
    st.write("Selecione uma opção para visualizar os dados.")

    if get_data() is None:
        st.warning("⚠️ Faça o upload dos dados para explorar.")
        return

    explore_options = get_available_explore_views()
    current_explore_view = get_current_explore_view()
    explore_option = st.selectbox(
        "Opções de Visualização",
        explore_options,
        index=explore_options.index(current_explore_view),
    )

    # Save the current explore view
    st.session_state.current_explore_view = explore_option

    # Show a loader while the data is being loaded
    with st.spinner("Carregando dados..."):
        data = get_data()

    # Explore the data
    if explore_option == "Explorador":
        ##############################
        pass

        ##############################

    # Edit the data
    elif explore_option == "Editor":
        ##############################

        # Allow user to filter the displayed data
        st.write("###### Editor")


### ABOUT ###
def view_about():
    st.title("✨ Sobre")
    st.write("""...""")
    st.write("### Fonte dos Dados")
    st.write(
        """Os dados utilizados nessa foram disponibilizados pela biblioteca StatsBomb: https://github.com/statsbomb/statsbombpy"""
    )
    st.write("### Sobre o Autor")
    st.write(
        """Este projeto foi criado Rafael Oliveira: https://github.com/RafaelOlivra/datario-streamlit-exploration"""
    )


##############  DASHBOARD ##############
def get_sidebar(view_index=0):
    st.sidebar.title("🧳Chegada de turistas pelo Município do Rio de Janeiro")
    st.sidebar.write("Selecione uma opção para visualizar os dados.")
    current_view = st.sidebar.radio("Menu", get_available_views(), index=view_index)
    set_current_view(current_view)


def dashboard():
    ### SIDEBAR ###
    get_sidebar()

    ### EXPLORE ###
    current_view = get_current_view()
    if current_view == "Explorar":
        view_explore()
    ### ABOUT ###
    elif current_view == "Sobre":
        view_about()


if __name__ == "__main__":
    dashboard()
