import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.title("🚗 무료 경로 보기 (OpenStreetMap)")

origin = st.text_input("출발지", "서울역")
destination = st.text_input("도착지", "강남역")

def geocode(addr):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": addr, "format": "json"}
    r = requests.get(url, params=params, headers={"User-Agent": "streamlit"})
    data = r.json()
    return float(data[0]["lat"]), float(data[0]["lon"])

if st.button("경로 보기"):
    lat1, lon1 = geocode(origin)
    lat2, lon2 = geocode(destination)

    route_url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    route = requests.get(route_url).json()

    m = folium.Map(location=[lat1, lon1], zoom_start=12)
    folium.Marker([lat1, lon1], tooltip="출발").add_to(m)
    folium.Marker([lat2, lon2], tooltip="도착").add_to(m)
    folium.GeoJson(route["routes"][0]["geometry"]).add_to(m)

    st_folium(m, width=700, height=500)
