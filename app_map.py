import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from urllib.parse import urlencode
import numpy as np

st.set_page_config(page_title="OSM Route Only", layout="wide")
st.title("🗺️ OpenStreetMap 경로 표시 (OSRM + Nominatim)")

# ----------------------------
# Helpers
# ----------------------------
def geocode_nominatim(query: str, limit=1):
    if not query.strip():
        return None
    base = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": str(limit)}
    url = base + "?" + urlencode(params)

    headers = {"User-Agent": "streamlit-osm-route-demo/1.0 (learning project)"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    return {
        "lat": float(data[0]["lat"]),
        "lon": float(data[0]["lon"]),
        "name": data[0].get("display_name", query)
    }

def route_osrm(start_lat, start_lon, end_lat, end_lon, profile="driving"):
    base = "https://router.project-osrm.org/route/v1"
    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"  # lon,lat
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }
    url = f"{base}/{profile}/{coords}?" + urlencode(params)
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def human_km(m): 
    return f"{m/1000:.2f} km"

def human_min(s):
    return f"{s/60:.0f} min"

# ----------------------------
# UI
# ----------------------------
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    start_addr = st.text_input("출발지", value=st.session_state.get("start_addr", "서울역"))
with c2:
    end_addr = st.text_input("도착지", value=st.session_state.get("end_addr", "광화문"))
with c3:
    profile = st.selectbox("이동 수단", ["driving", "walking", "cycling"],
                           index=["driving","walking","cycling"].index(st.session_state.get("profile","driving")))

go = st.button("경로 표시", use_container_width=True)

# 버튼을 눌렀으면 계산해서 session_state에 저장
if go:
    st.session_state["start_addr"] = start_addr
    st.session_state["end_addr"] = end_addr
    st.session_state["profile"] = profile

    with st.spinner("주소 → 좌표 변환 + 경로 계산 중..."):
        s = geocode_nominatim(start_addr)
        e = geocode_nominatim(end_addr)

        if s is None or e is None:
            st.session_state["route_ready"] = False
            st.error("주소를 좌표로 못 찾았어. 다른 표현으로 입력해줘.")
        else:
            data = route_osrm(s["lat"], s["lon"], e["lat"], e["lon"], profile=profile)
            if data.get("code") != "Ok":
                st.session_state["route_ready"] = False
                st.error(f"OSRM 경로 계산 실패: {data.get('message', 'unknown error')}")
            else:
                route = data["routes"][0]
                st.session_state["route_ready"] = True
                st.session_state["start_info"] = s
                st.session_state["end_info"] = e
                st.session_state["route"] = route

# ✅ 버튼을 안 눌렀더라도, 이전에 계산된 결과가 있으면 계속 표시
if not st.session_state.get("route_ready", False):
    st.info("출발/도착 입력 후 ‘경로 표시’를 누르면 지도에 경로가 그려져. (한 번 그리면 사라지지 않게 고정해뒀어)")
    st.stop()

s = st.session_state["start_info"]
e = st.session_state["end_info"]
route = st.session_state["route"]

distance = route.get("distance", 0.0)
duration = route.get("duration", 0.0)

st.success("경로 생성 완료! (지금부터는 rerun 돼도 안 사라짐)")
st.write(f"총 거리: **{human_km(distance)}** | 예상 시간: **{human_min(duration)}**")
st.caption(f"출발: {s['name']}")
st.caption(f"도착: {e['name']}")

# ----------------------------
# 지도 그리기
# ----------------------------
center_lat = (s["lat"] + e["lat"]) / 2
center_lon = (s["lon"] + e["lon"]) / 2

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")
folium.Marker([s["lat"], s["lon"]], tooltip="출발").add_to(m)
folium.Marker([e["lat"], e["lon"]], tooltip="도착").add_to(m)

geom = route.get("geometry", {})
coords = geom.get("coordinates", [])  # [lon,lat]
latlon = [[c[1], c[0]] for c in coords]
folium.PolyLine(latlon, weight=6, opacity=0.85).add_to(m)

# ✅ key를 고정해두면 렌더가 더 안정적이야
st_folium(m, width=1100, height=560, key="route_map")

# ----------------------------
# 도로명 목록
# ----------------------------
legs = route.get("legs", [])
steps = legs[0].get("steps", []) if legs else []

road_names = []
for stp in steps:
    nm = (stp.get("name") or "").strip()
    if nm and nm not in road_names:
        road_names.append(nm)

with st.expander("🛣️ 경로에서 지나가는 도로/구간 이름", expanded=True):
    if road_names:
        st.write(f"총 **{len(road_names)}개** 도로/구간 이름")
        st.write(road_names)
    else:
        st.warning("이 경로에서는 도로명이 충분히 잡히지 않았어(데이터가 비어있는 구간이 있음).")
