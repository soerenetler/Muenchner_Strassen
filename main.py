import streamlit as st
from streamlit_folium import st_folium
import folium

from game_utils import *

@st.dialog("🎉 Ergebnis", dismissible=False)
def result_dialog():
    if st.session_state.distance is not None:
        distance = st.session_state.distance
        if distance >= 1000:
            st.metric("Entfernung zum Ziel", f"{distance/1000:.1f} km")
        else:
            st.metric("Entfernung zum Ziel", f"{distance:.0f} m")

        if distance < 100:
            st.success("🎉 Sehr gut! Du hast die Straße gefunden!")
        else:
            st.warning("Fast, aber nicht ganz!")

    if st.button("OK", icon="🗺️", type="primary"):
        st.session_state.hide_results = True
        st.rerun()

# Page config should be the first Streamlit command
st.set_page_config(page_title="StreetGuesser", layout="wide")

st.logo("images/logo_streetguesser.png", size="large")

# increase width of the map container
st.markdown("""
     <style>
     [title~="st.iframe"] { width: 100%}
     </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <style>
           .block-container {
                padding-top: 4rem;
            }
    </style>
    """, unsafe_allow_html=True, )

# This logic should be run at the start of each script run
# to process the map state from the *previous* run.
if "street_quiz_map" in st.session_state and st.session_state.street_quiz_map:
    map_state_change = st.session_state.street_quiz_map

    # Update center and zoom on any map interaction
    # if map_state_change.get("center"):
    #    st.session_state.center = (
    #        map_state_change["center"]["lat"],
    #        map_state_change["center"]["lng"],
    #    )
    #if map_state_change.get("zoom"):
    #    st.session_state.zoom = map_state_change["zoom"]

    # If the interaction includes a click, update the user's guess
    if map_state_change.get("last_clicked") and "distance" not in st.session_state:
        loc = map_state_change["last_clicked"]
        st.session_state.user_guess = (loc["lat"], loc["lng"])

if "user_guess" not in st.session_state:
    st.session_state.user_guess = None

if "hide_results" not in st.session_state:
    st.session_state.hide_results = False


def main():
    if "bezirk_selection" not in st.session_state:
        start_game_dialog()

    if "target_street_name" not in st.session_state:
        if "bezirk_selection" in st.session_state:
            start_game()
        m = empty_map()
        output = st_folium(
            m,
            height=500,
            key="street_quiz_map",
            use_container_width=True
        )
    elif "distance" not in st.session_state:
        if st.session_state.target_street_name.lower().endswith("str."):
            st.markdown(f"Wo ist die **:primary-background[{st.session_state.target_street_name}]**?")
        elif st.session_state.target_street_name.lower().endswith("weg"):
            st.markdown(f"Wo ist der **:primary-background[{st.session_state.target_street_name}]**?")
        elif st.session_state.target_street_name.lower().endswith("pl."):
            st.markdown(f"Wo ist der **:primary-background[{st.session_state.target_street_name}]**?")
        else:
            st.markdown(f"Wo ist der/die/das **:primary-background[{st.session_state.target_street_name}]**?")

        m = empty_map()

        if st.session_state.user_guess is not None:
            folium.Marker(
                location=st.session_state.user_guess,
                icon=folium.Icon(color="red"),
            ).add_to(m)

        output = st_folium(
            m,
            height=500,
            key="street_quiz_map",
            returned_objects=["last_clicked"],
            use_container_width=True
        )

        st.button(
            "Bestätigen",
            on_click=calculate_distance,
            disabled=(
                st.session_state.user_guess is None
            ),
        )

    else:
        if st.session_state.target_street_name.lower().endswith("str."):
            st.markdown(f"Wo ist die **:primary-background[{st.session_state.target_street_name}]**?")
        elif st.session_state.target_street_name.lower().endswith("weg"):
            st.markdown(f"Wo ist der **:primary-background[{st.session_state.target_street_name}]**?")
        elif st.session_state.target_street_name.lower().endswith("pl."):
            st.markdown(f"Wo ist der **:primary-background[{st.session_state.target_street_name}]**?")
        else:
            st.markdown(f"Wo ist der/die/das **:primary-background[{st.session_state.target_street_name}]**?")

        m = empty_map()

        folium.Marker(
            location=st.session_state.user_guess,
            icon=folium.Icon(color="red"),
        ).add_to(m)
        # Use the pre-calculated geometry for display, avoiding repeated conversions
        folium.GeoJson(
            st.session_state.target_street_4326,
            style_function=lambda x: {"color": "green", "weight": 5, "opacity": 0.8},
            tooltip=folium.Tooltip(st.session_state.target_street_name, permanent=True),
        ).add_to(m)

        folium.PolyLine(
            locations=st.session_state.connector_line,
            color="black",
            weight=2,
            dash_array="5, 5",
            tooltip=folium.Tooltip(f"{st.session_state.distance/1000:.1f} km", permanent=True),
        ).add_to(m)

        # Zoom to fit both the user's guess and the target street
        street_coords = []
        if st.session_state.target_street_4326.geom_type == "LineString":
            street_coords = [(p[1], p[0]) for p in st.session_state.target_street_4326.coords]
        elif st.session_state.target_street_4326.geom_type == "MultiLineString":
            for part in st.session_state.target_street_4326.geoms:
                street_coords += [(p[1], p[0]) for p in part.coords]

        m.fit_bounds(st.session_state.connector_line + street_coords, padding=(50, 50))

        # Simplified call
        output = st_folium(
            m,
            height=500,
            key="street_quiz_map",
            returned_objects=[],
            use_container_width=True
        )

        # Display results here, based on session_state
        if not st.session_state.hide_results:
            result_dialog()

        if st.button("Neues Spiel", icon="🔄", type="secondary"):
                        # A more robust way to clear the game state for the next round
            keys_to_clear = [
                "bezirk_selection",
                "target_street_name",
                "target_street_25832",
                "target_street_4326",
                "user_guess",
                "distance",
                "connector_line",
                "street_quiz_map"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            st.session_state.hide_results = False
            st.rerun()


        if st.button("Neue Straße", icon="🎯", type="primary"):
            # A more robust way to clear the game state for the next round
            keys_to_clear = [
                "target_street_name",
                "target_street_25832",
                "target_street_4326",
                "user_guess",
                "distance",
                "connector_line",
                "street_quiz_map"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            st.session_state.hide_results = False
            st.rerun()


if __name__ == "__main__":
    main()
