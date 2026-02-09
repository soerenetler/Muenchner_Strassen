import streamlit as st
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
from shapely.geometry import box

from streamlit_extras.let_it_rain import rain 

from streamlit_folium import st_folium
import folium


import geopandas as gpd

@st.cache_data
def load_strassen_25832():
    df = gpd.read_file("processed_data/strassen_adressen_muenchen.geojson")
    # Ensure metric CRS for accurate distance and spatial operations
    assert df.crs.to_string() == "EPSG:25832"
    return df


@st.cache_data
def load_bezirke_25832():
    df = gpd.read_file("processed_data/muenchen_stadtbezirke.geojson")
    assert df.crs.to_string() == "EPSG:25832"
    return df


@st.cache_data
def get_bezirke_4326():
    """Load and convert bezirke to EPSG:4326 for mapping."""
    return load_bezirke_25832().to_crs("EPSG:4326")


@st.cache_data
def get_available_streets(selection):
    """Filter streets by selected districts using spatial join. Cached for performance."""
    strassen_df = load_strassen_25832()
    bezirke_df = load_bezirke_25832()
    filtered_bezirke = bezirke_df[bezirke_df["sb_name"].isin(selection)]
    return gpd.sjoin(strassen_df, filtered_bezirke, predicate="within")


def calculate_distance():
    """Calculate distance and update session state. Reads all data from st.session_state."""
    lat, lon = st.session_state.user_guess

    # Create the guess point in Lat/Lon (EPSG:4326)
    guess_gs = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")

    # Re-project the guess to the same meter-based system as our source data
    guess_meters = guess_gs.to_crs(epsg=25832)

    # Both geometries are now in EPSG:25832, so we can calculate distance directly.
    target_geometry = st.session_state.target_street_25832
    distance = guess_meters.distance(target_geometry).iloc[0]
    st.session_state.distance = distance

    # Calculate connector line
    p1, p2 = nearest_points(guess_meters.iloc[0], target_geometry)
    line = LineString([p1, p2])
    line_gs = gpd.GeoSeries([line], crs="EPSG:25832")
    line_4326 = line_gs.to_crs("EPSG:4326").iloc[0]

    # Extract coordinates for Folium (Lat, Lon)
    st.session_state.connector_line = [(p[1], p[0]) for p in line_4326.coords]


@st.dialog("Willkommen zum :blue[StreetGuesser]! 🎉", dismissible=False)
def start_game_dialog():
    st.write(f"Wähle die Stadtbezirke aus, in denen du spielen möchtest. Viel Spaß beim Spielen! 🚗🗺️")
    
    bezirke_df = load_bezirke_25832()

    bezirk_options = list(bezirke_df["sb_name"])
    selection = st.pills(
        "Stadtbezirke", bezirk_options, default=bezirk_options, selection_mode="multi"
    )
    
    if not selection:
        st.warning("Bitte mindestens einen Stadtbezirk auswählen, um zu spielen.")

    if st.button("Spiel starten", icon="🗺️", disabled=not selection, type="primary"):
        # Initialize the target street, pre-calculating and storing geometries
        st.session_state.bezirk_selection = selection
        start_game()
        st.rerun()

def start_game():
    joined_df = get_available_streets(st.session_state.bezirk_selection)
    
    if joined_df.empty:
        st.warning(
            "In den ausgewählten Bezirken wurden keine Straßen gefunden. Bitte andere Bezirke auswählen."
        )
        st.stop()
    target_series = joined_df.sample(1, weights=joined_df["laenge"]*joined_df["laenge"]).iloc[0]
    st.session_state.target_street_name = target_series["STRANAM"]
    st.session_state.target_street_25832 = target_series.geometry

    # Pre-calculate the geometry for map display (EPSG:4326) and store it
    target_gs = gpd.GeoSeries([target_series.geometry], crs="EPSG:25832")
    st.session_state.target_street_4326 = target_gs.to_crs("EPSG:4326").iloc[0]

def empty_map():
    # Convert bezirke to the correct CRS for Folium
    bezirke_4326 = get_bezirke_4326()

    if "bezirk_selection" in st.session_state:
        bezirke_4326 = bezirke_4326[bezirke_4326["sb_name"].isin(st.session_state.bezirk_selection)]

    print(f"Bezirke for map: {bezirke_4326['sb_name'].tolist()}")

    # Create a mask for the area outside Munich
    munich_geom = bezirke_4326.geometry.union_all()
    bounds = munich_geom.bounds
    min_lon, min_lat, max_lon, max_lat = bounds

    ## --- Map Setup ---
    if "distance" not in st.session_state:
        m = folium.Map(
            # Use max_bounds to constrain the map view. This prevents panning outside the box.
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            max_bounds=True,
            min_zoom=11,
            max_zoom=18,
            tiles="CartoDB.VoyagerNoLabels"
        )
    else:
        m = folium.Map(
            # Use max_bounds to constrain the map view. This prevents panning outside the box.
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            max_bounds=True,
            min_zoom=11,
            max_zoom=18,
            tiles="CartoDB.Voyager"
        )



    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

    outer_box = box(min_lon - 0.5, min_lat - 0.5, max_lon + 0.5, max_lat + 0.5)
    selected_geo = bezirke_4326
    
    # Optimized mask: Difference between outer box and selected area
    mask = outer_box.difference(selected_geo.union_all())

    # Add unselected districts (darkened)
    folium.GeoJson(
        mask,
        style_function=lambda x: {
            "fillColor": "black",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.5,
        },
        name="Unselected Area",
    ).add_to(m)

    # Add selected districts (lightly shaded)
    if not selected_geo.empty:
        folium.GeoJson(
            selected_geo.union_all(),
            style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0},
            name="Selected Area",
        ).add_to(m)

    return m
