import time
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import pandas as pd
import plotly.express as px
import pydeck as pdk
import time
import numpy as np
import locale
from statsbombpy import sb

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

state = {
    "selected_country": "Europe",
    "competition_id": None,
    "season_id": None,
    "match_id": None,
    "data": None,
    "current_view": 0,
    "current_explore_view": "Resumo da Partida",
}


def set_state(key, value):
    st.session_state[key] = value


def get_state(key):
    return st.session_state[key]


# Set initial state
for key, value in state.items():
    if key not in st.session_state:
        set_state(key, value)


############## UTIL FUNCTIONS ##############


def format_number(number):
    # Convert to number if necessary
    if isinstance(number, str):
        number = int(number)
    return locale.format_string("%d", number, grouping=True)


############## DATA FUNCTIONS ##############


def get_available_views():
    return ["Explorar", "Sobre"]


def get_current_view():
    return get_state("current_view") or get_available_views()[0]


############## StatsBombPy ##############


def display_competitions_selector():
    # Get competitions DataFrame
    competitions = sb.competitions()

    col1, col2, col3 = st.columns([1, 1, 1])
    # Filter by country
    with col1:
        # Get selected country from state
        country_name = competitions[
            competitions["country_name"] == get_state("selected_country")
        ]["country_name"].unique()[0]

        countries = competitions["country_name"].unique()
        idx = countries.tolist().index(country_name)

        selected_country = st.selectbox("Selecione um país", countries, index=idx)
        competitions = competitions[competitions["country_name"] == selected_country]
        set_state("selected_country", selected_country)

    # Filter by competition
    with col2:
        competition_names = competitions["competition_name"].unique()

        # Get selected competition from state
        competition_id = (
            get_state("competition_id") or competitions["competition_id"].values[0]
        )
        idx = 0
        # Check is the saved competition is in the current list
        if competition_id not in competitions["competition_id"].values:
            competition_id = competitions["competition_id"].values[0]
        else:
            idx = competition_names.tolist().index(
                competitions[competitions["competition_id"] == competition_id][
                    "competition_name"
                ].values[0]
            )

        selected_competition = st.selectbox(
            "Selecione uma competição", competition_names, index=idx
        )
        competition = competitions[
            competitions["competition_name"] == selected_competition
        ]
        competition_id = competition["competition_id"].values[0]
        set_state("competition_id", competition_id)

    # Filter by season
    with col3:
        seasons = competition["season_name"].unique()

        # Get selected season from state
        season_id = get_state("season_id") or competition["season_id"].values[0]
        idx = 0
        # Check is the saved season is in the current list
        if season_id not in competition["season_id"].values:
            season_id = competition["season_id"].values[0]
        else:
            idx = seasons.tolist().index(
                competition[competition["season_id"] == season_id][
                    "season_name"
                ].values[0]
            )

        selected_season = st.selectbox("Selecione uma temporada", seasons, index=idx)
        season = competition[competition["season_name"] == selected_season]
        season_id = season["season_id"].values[0]
        set_state("season_id", season_id)

    return competition_id, season_id


def display_matches_selector(competition_id: int, season_id: int):
    # Get matches DataFrame
    matches = sb.matches(competition_id=competition_id, season_id=season_id)

    # Filter by match
    match_ids = matches["match_id"].unique()

    # Get selected match from state if available
    match_id = get_state("match_id") or match_ids[0]
    if match_id not in match_ids:
        match_id = match_ids[0]

    # Generate a list of match names
    match_names = [generate_match_name(matches, match_id) for match_id in match_ids]

    # Check if the selected match id is in the list
    # The id can be retrieved from the match name after the last "-"
    idx = 0
    for i, name in enumerate(match_names):
        if str(match_id) in name:
            idx = i
            break

    # Show matches selector
    selected_match = st.selectbox("Selecione uma partida", match_names, index=idx)
    match_id = int(selected_match.split("-")[-1].strip())
    set_state("match_id", match_id)

    return match_id


def display_explore_view_selector():
    explore_options = ["Resumo da Partida", "Jogador VS Jogador", "DataFrame"]
    current_explore_view = get_state("current_explore_view") or explore_options[0]
    explore_view = st.selectbox(
        "Opções de Visualização",
        explore_options,
        index=explore_options.index(current_explore_view),
    )
    set_state("current_explore_view", explore_view)
    return explore_view


def generate_match_name(matches_df, match_id):
    if len(matches_df[matches_df["match_id"] == match_id]) == 0:
        return "Match not found"

    match_id = int(match_id)
    match_date = matches_df[matches_df["match_id"] == match_id]["match_date"].values[0]
    match_name = (
        (
            matches_df[matches_df["match_id"] == match_id]["home_team"]
            + " x "
            + matches_df[matches_df["match_id"] == match_id]["away_team"]
        )
        + " - "
        + match_date
        + " - "
        + str(match_id)
    )
    return match_name.values[0]


############## PLOTS & GRAPHS ##############

############## VIEWS ##############


### EXPLORE ###
def view_explore():
    st.title("🔍 Explorar")
    st.write("Selecione uma opção para visualizar os dados.")

    # Show competitions selector
    display_competitions_selector()

    # Show matches selector
    display_matches_selector(get_state("competition_id"), get_state("season_id"))

    # Show explore options
    display_explore_view_selector()

    # Explore the data
    st.write(get_state("current_explore_view"))
    if get_state("current_explore_view") == "Resumo da Partida":
        ##############################
        pass


### ABOUT ###
def view_about():
    st.title("✨ Sobre")
    st.write("""Este é um dashboard criado para explorar dados de futebol.""")
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
    st.sidebar.title("⚽ Dashboard StatsBombPy")
    st.sidebar.write("Selecione uma visualização para explorar os dados.")
    current_view = st.sidebar.radio("Menu", get_available_views(), index=view_index)
    set_state("current_view", current_view)


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
