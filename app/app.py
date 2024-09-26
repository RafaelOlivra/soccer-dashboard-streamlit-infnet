import streamlit as st
import plotly.express as px
import pandas as pd
import locale
from statsbombpy import sb
from mplsoccer import Pitch

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
    "current_explore_view": "Análise da Partida",
}


def set_state(key, value):
    st.session_state[key] = value


def get_state(key):
    return st.session_state[key]


# Set initial state
for key, value in state.items():
    if key not in st.session_state:
        set_state(key, value)

############## SETTINGS ##############


def get_vs_column_cfg():
    return [5, 2, 5]


############## VIEW FUNCTIONS ##############


def get_available_views():
    return ["Explorar", "Sobre"]


def get_current_view():
    return get_state("current_view") or get_available_views()[0]


############## StatsBombPy DATA FUNCTIONS ##############


@st.cache_data(ttl=3600)
def get_competitions():
    return sb.competitions()


@st.cache_data(ttl=3600)
def get_competition_matches(competition_id, season_id):
    return sb.matches(competition_id=competition_id, season_id=season_id)


@st.cache_data(ttl=3600)
def get_match_events(match_id):
    return sb.events(match_id=match_id)


@st.cache_data(ttl=3600)
def get_teams(competition_id, season_id, match_id):
    matches = get_competition_matches(competition_id, season_id)
    match = matches[matches["match_id"] == match_id]
    home_team = match["home_team"].values[0]
    away_team = match["away_team"].values[0]
    return home_team, away_team


@st.cache_data(ttl=3600)
def get_match_score_dict(competition_id, season_id, match_id):
    # Get goals for open play and penalties
    goals = get_goals_df(match_id)
    teams = get_teams(competition_id, season_id, match_id)

    # Penalty goals are counted after the minute 120
    penalty_goals = goals[goals["minute"] >= 120]
    open_play_goals = goals[goals["minute"] < 120]

    # Get total goals for each team
    open_play_goals = open_play_goals.groupby("team").size()
    penalty_goals = penalty_goals.groupby("team").size()

    home_team_open_play_goals = (
        open_play_goals[teams[0]] if teams[0] in open_play_goals else 0
    )
    home_team_penalty_goals = (
        penalty_goals[teams[0]] if teams[0] in penalty_goals else 0
    )

    # Get player name and time for each goal
    home_team_player_goals = goals[goals["team"] == teams[0]][["player", "minute"]]
    alway_team_player_goals = goals[goals["team"] == teams[1]][["player", "minute"]]

    home_team_player_goals_text = ""
    for i, row in home_team_player_goals.iterrows():
        home_team_player_goals_text += f"{row['player']} ({row['minute']}'), "
    home_team_player_goals_text = home_team_player_goals_text[:-2]

    alway_team_player_goals_text = ""
    for i, row in alway_team_player_goals.iterrows():
        alway_team_player_goals_text += f"{row['player']} ({row['minute']}'), "
    alway_team_player_goals_text = alway_team_player_goals_text[:-2]

    # Check if there are two teams
    if len(teams) == 2:
        alway_team_open_play_goals = (
            open_play_goals[teams[1]] if teams[1] in open_play_goals else 0
        )

        alway_team_penalty_goals = (
            penalty_goals[teams[1]] if teams[1] in penalty_goals else 0
        )
    else:
        alway_team_open_play_goals = 0
        alway_team_penalty_goals = 0

    return {
        "home_team_name": teams[0],
        "home_team_open_play": home_team_open_play_goals,
        "home_team_penalty": home_team_penalty_goals,
        "home_team_player_goals": home_team_player_goals_text,
        "alway_team_name": teams[1],
        "alway_team_open_play": alway_team_open_play_goals,
        "alway_team_penalty": alway_team_penalty_goals,
        "alway_team_player_goals": alway_team_player_goals_text,
    }


@st.cache_data(ttl=3600)
def get_goals_df(match_id, team="", shot_type=""):
    events = get_match_events(match_id)
    goals = events[events["type"] == "Shot"]
    goals = goals[goals["shot_outcome"] == "Goal"]

    if shot_type:
        goals = goals[goals["shot_type"] == shot_type]

    if team:
        goals = goals[goals["team"] == team]
    return goals


@st.cache_data(ttl=3600)
def get_shots_on_goal_df(match_events_df, team=""):
    shots_on_goal = match_events_df[
        match_events_df["shot_outcome"].isin(["Goal", "Saved", "Saved to Corner"])
    ]

    if team:
        shots_on_goal = shots_on_goal[shots_on_goal["team"] == team]
    return shots_on_goal


@st.cache_data(ttl=3600)
def get_match_stats_dict(match_events_df, stats_map=None):
    events = match_events_df

    if stats_map is None:
        stats_map = {
            "⚽ Total de Chutes": "Shot",
            "🅿️ Total de Passes": "Pass",
            "❌ Faltas": {"type": "Foul Committed"},
            "🏳️ Escanteios": {"play_pattern": "From Corner"},
            "🟨 Cartões Amarelos": {
                "foul_committed_card": "Yellow Card",
                "bad_behaviour_card": "Yellow Card",
            },
            "🟥 Cartões Vermelhos": {
                "foul_committed_card": "Red Card",
                "bad_behaviour_card": "Red Card",
            },
        }

    # Get stats for each team
    teams = events["team"].unique()
    stats = {}

    for team in teams:
        team_events = events[events["team"] == team]
        team_stats = {}
        for stat_name, stat_type in stats_map.items():
            if isinstance(stat_type, dict):
                stat = 0
                for key, value in stat_type.items():
                    # Check if the key exists in the DataFrame
                    if key in team_events.columns:
                        stat += len(team_events[team_events[key] == value])
            else:
                stat = len(team_events[team_events["type"] == stat_type])
            team_stats[stat_name] = stat
        stats[team] = team_stats

    return stats


############## Display Functions ##############


def display_match_score(score_obj):
    col1, col2, col3 = st.columns(get_vs_column_cfg())
    with col1:
        st.markdown(
            f"<h5 style='text-align: center; padding: 0;'>{score_obj['home_team_name']}</h5>",
            unsafe_allow_html=True,
        )
        if score_obj["home_team_penalty"]:
            st.markdown(
                f"<h1 style='text-align: center;'>{score_obj['home_team_open_play']} ({score_obj['home_team_penalty']})</h1>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<h1 style='text-align: center;'>{score_obj['home_team_open_play']}</h1>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<p style='text-align: center; font-size: 12px;'>{score_obj['home_team_player_goals']}</p>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<h1 style='text-align: center;'>x</h1>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<h5 style='text-align: center; padding: 0;'>{score_obj['alway_team_name']}</h5>",
            unsafe_allow_html=True,
        )
        if score_obj["alway_team_penalty"]:
            st.markdown(
                f"<h1 style='text-align: center;'>{score_obj['alway_team_open_play']} ({score_obj['alway_team_penalty']})</h1>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<h1 style='text-align: center;'>{score_obj['alway_team_open_play']}</h1>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<p style='text-align: center; font-size: 12px;'>{score_obj['alway_team_player_goals']}</p>",
            unsafe_allow_html=True,
        )


def display_overall_match_stats(match_events_df, home_team, alway_team):
    stats = get_match_stats_dict(match_events_df)

    col1, col2, col3 = st.columns(get_vs_column_cfg())
    stats_names = list(stats[home_team].keys())
    with col1:
        for stat_name in stats_names:
            st.markdown(
                f"<p style='text-align: center;'>{stats[home_team][stat_name]}</p>",
                unsafe_allow_html=True,
            )
    with col2:
        for stat_name in stats_names:
            st.markdown(
                f"<p style='text-align: center; font-weight: bold;'>{stat_name}</p>",
                unsafe_allow_html=True,
            )
    with col3:
        for stat_name in stats_names:
            st.markdown(
                f"<p style='text-align: center;'>{stats[alway_team][stat_name]}</p>",
                unsafe_allow_html=True,
            )


############## StatsBombPy ##############


def competitions_selector():
    # Get competitions DataFrame
    competitions = get_competitions()

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


def matches_selector(competition_id: int, season_id: int):
    # Get matches DataFrame
    matches = get_competition_matches(competition_id, season_id)

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
    match_name = st.selectbox("Selecione uma partida", match_names, index=idx)
    match_id = int(match_name.split("-")[-1].strip())
    set_state("match_id", match_id)

    # Get match data
    match_events_df = get_match_events(match_id)

    return match_id, match_name, match_events_df


def explore_view_selector():
    explore_options = ["Análise da Partida", "Explorar DataFrame"]
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


@st.cache_data(ttl=3600)
def plot_event_map(match_events_df, team_name="", event_type="Pass", color="blue"):
    with st.spinner("Carregando..."):
        try:
            # Filter for events by the given team
            events = match_events_df[(match_events_df["type"] == event_type)]

            # Filter for events by the given team
            if team_name:
                events = events[events["team"] == team_name]

            # Create a soccer pitch
            pitch = Pitch(
                pitch_type="statsbomb", pitch_color="grass", line_color="white"
            )

            # Set up the pitch plot
            fig, ax = pitch.draw(figsize=(10, 7))

            # Plot the passes
            event_name = event_type.lower()
            pitch.arrows(
                events["location"].str[0],
                events["location"].str[1],
                events[f"{event_name}_end_location"].str[0],
                events[f"{event_name}_end_location"].str[1],
                width=2,
                headwidth=3,
                headlength=5,
                color=color,
                ax=ax,
                label=f"{event_type}s",
            )

            # Add title and display plot
            st.pyplot(fig)
        except Exception as e:
            st.warning(f"⚠️ Não é possível gerar um gráfico para os dados fornecidos.")
        return True


@st.cache_data(ttl=3600)
def plot_player_heatmap(match_events_df, team_name="", player_name=""):
    with st.spinner("Carregando..."):
        try:
            # Filter for passes by the given team
            events = match_events_df[(match_events_df["type"] == "Pass")]

            # Filter for events by the given team and player
            if team_name:
                events = events[events["team"] == team_name]
            if player_name:
                events = events[events["player"] == player_name]

            # Ensure that 'location' column is available and contains coordinates
            if "location" not in events.columns or events["location"].isnull().all():
                st.warning("No location data available to plot the heatmap.")
                return

            # Extract 'x' and 'y' coordinates from 'location' (assuming it's a list of [x, y] coordinates)
            locations = (
                events["location"]
                .dropna()
                .apply(
                    lambda loc: loc if isinstance(loc, list) and len(loc) == 2 else None
                )
            )
            locations = pd.DataFrame(locations.tolist(), columns=["x", "y"]).dropna()

            # Create a soccer pitch
            pitch = Pitch(
                pitch_type="statsbomb", pitch_color="grass", line_color="white"
            )

            # Set up the pitch plot
            fig, ax = pitch.draw(figsize=(10, 7))

            # Plot the heatmap using the x and y coordinates
            pitch.heatmap(
                locations[["x", "y"]].values,
                ax=ax,
                edgecolors="w",
                bins=(10, 7),
                cmap="coolwarm",
            )

            # Add title and display plot
            ax.set_title(f"Heatmap for {player_name} ({team_name})", fontsize=16)
            st.pyplot(fig)

        except Exception as e:
            st.warning(f"⚠️ Não é possível gerar um gráfico para os dados fornecidos.")
            st.exception(e)
        return True


############## PAGES ##############


### EXPLORE ###
def view_explore():
    st.title("🔍 Explorar")
    st.write("Selecione uma opção para visualizar os dados.")

    # Show competitions selector
    competition_id, season_id = competitions_selector()

    # Show matches selector
    match_id, match_name, match_events_df = matches_selector(competition_id, season_id)

    # Show explore view selector
    current_explore_view = explore_view_selector()

    # Explore the data
    ##############################
    if current_explore_view == "Análise da Partida":
        st.write(f"---")

        score_obj = get_match_score_dict(competition_id, season_id, match_id)
        home_team = score_obj["home_team_name"]
        alway_team = score_obj["alway_team_name"]

        #  ---- Match summary
        # Match score
        display_match_score(score_obj)
        st.write(f"---")

        # Match stats
        display_overall_match_stats(match_events_df, home_team, alway_team)
        st.write(f"---")

        #  ---- DataFrame filters
        with st.expander("⚙️ Filtrar"):
            # Time filter
            time_filter = st.slider(
                "Filtrar por Minuto", min_value=0, max_value=120, value=(0, 120)
            )
            match_events_df = match_events_df[
                (match_events_df["minute"] >= time_filter[0])
                & (match_events_df["minute"] <= time_filter[1])
            ]
            # Player filter
            players = match_events_df["player"].dropna().unique()
            players.sort()
            player = st.selectbox("Filtrar por Jogador", ["Todos"] + list(players))
            if player != "Todos":
                match_events_df = match_events_df[match_events_df["player"] == player]

            # Event filter
            event_types = match_events_df["type"].dropna().unique()
            event_types.sort()
            event_type = st.selectbox(
                "Filtrar por Evento", ["Todos"] + list(event_types)
            )
            if event_type != "Todos":
                match_events_df = match_events_df[match_events_df["type"] == event_type]

        #  --- Metrics
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total de Chutes", len(match_events_df[match_events_df["type"] == "Shot"])
        )
        col2.metric("Chutes ao Gol", len(get_shots_on_goal_df(match_events_df)))
        col3.metric(
            "Total de Passes", len(match_events_df[match_events_df["type"] == "Pass"])
        )
        col4.metric(
            "Faltas Cometidas",
            len(match_events_df[match_events_df["type"] == "Foul Committed"]),
        )

        # ---- Plots
        # Pass map
        progress_bar = st.progress(0, text="Gerando visualizações...")

        col1, col2 = st.columns(2)
        with col1:
            title = f"Mapa de Passes - {home_team}"
            st.write(f"##### {title}")
            plot_event_map(match_events_df, home_team, event_type="Pass")
            progress_bar.progress(25, text=f"Finalizado: {title}...")
        with col2:
            title = f"Mapa de Passes - {alway_team}"
            st.write(f"##### {title}")
            plot_event_map(match_events_df, alway_team, event_type="Pass")
            progress_bar.progress(50, text=f"Finalizado: {title}...")

        # Shot map
        with col1:
            title = f"Mapa de Chutes - {home_team}"
            st.write(f"##### {title}")
            plot_event_map(
                match_events_df, home_team, event_type="Shot", color="yellow"
            )
            progress_bar.progress(75, text=f"Finalizado: {title}...")
        with col2:
            title = f"Mapa de Chutes - {alway_team}"
            st.write(f"##### {title}")
            plot_event_map(
                match_events_df, alway_team, event_type="Shot", color="yellow"
            )
            progress_bar.progress(100, text=f"Finalizado: {title}...")

        # Heatmap
        st.write(f"---")
        st.write("##### Heatmap de Passe")
        plot_player_heatmap(match_events_df)
        progress_bar.empty()
        st.write(f"---")

        # Display the data in a DataFrame
        st.write("##### DataFrame da Partida")
        st.dataframe(match_events_df, use_container_width=True)

        st.write("##### Download dos dados filtrados")
        st.write(
            "Clique no botão abaixo para fazer o download do arquivo CSV filtrado com base nas suas seleções."
        )
        csv_content = match_events_df.to_csv(index=False)
        st.download_button(
            label="Download do CSV",
            data=csv_content,
            file_name=f"{match_name}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

    ##############################
    if current_explore_view == "Explorar DataFrame":

        # Allow user to filter the displayed data
        st.write(f"---")

        # Make a multiselect for selecting the columns to display
        columns = st.multiselect(
            "Filtrar Colunas",
            match_events_df.columns.tolist(),
            default=match_events_df.columns.tolist(),
        )
        df = match_events_df[columns]

        # Allow user to filter the displayed data with a search_filter box
        search_filter = st.text_input("Filtrar Valores", "")
        if search_filter:
            df = df[
                df.astype(str)
                .apply(lambda x: x.str.contains(search_filter, case=False, na=False))
                .any(axis=1)
            ]

        # Show the data in a dataframe
        st.dataframe(df, use_container_width=True)

        # Permite ao usuário download do arquivo CSV
        st.write("##### Download dos dados filtrados")
        st.write(
            "Clique no botão abaixo para fazer o download do arquivo CSV filtrado com base nas suas seleções."
        )
        csv_content = df.to_csv(index=False)
        st.download_button(
            label="Download do CSV",
            data=csv_content,
            file_name=f"{match_name}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )


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
