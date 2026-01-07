import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from urllib.parse import urlencode
import time

st.set_page_config(page_title="OSM Route Only", layout="wide")
st.title("🗺️ OpenStreetMap 경로 표시 (OSRM + Nominatim)")

# ----------------------------
# 1) 지오코딩: Nominatim (주소 -> 좌표)
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

# ----------------------------
# 2) 라우팅: OSRM (좌표 -> 경로 + steps)
# ----------------------------
def route_osrm(start_lat, start_lon, end_lat, end_lon, profile="driving"):
    base = "https://router.project-osrm.org/route/v1"
    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"  # lon,lat
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"   # 도로명(name) 뽑으려고
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
    start_addr = st.text_input("출발지", value="서울역")
with c2:
    end_addr = st.text_input("도착지", value="광화문")
with c3:
    profile = st.selectbox("이동 수단", ["driving", "walking", "cycling"], index=0)

go = st.button("경로 표시", use_container_width=True)

if not go:
    st.info("출발/도착 입력 후 ‘경로 표시’ 눌러줘.")
    st.stop()

with st.spinner("주소 → 좌표 변환 + 경로 계산 중..."):
    time.sleep(0.4)  # 예의(과도호출 방지용)
    s = geocode_nominatim(start_addr)
    time.sleep(0.4)
    e = geocode_nominatim(end_addr)

    if s is None or e is None:
        st.error("주소를 좌표로 못 찾았어. 다른 표현으로 입력해줘.")
        st.stop()

    data = route_osrm(s["lat"], s["lon"], e["lat"], e["lon"], profile=profile)
    if data.get("code") != "Ok":
        st.error(f"OSRM 경로 계산 실패: {data.get('message', 'unknown error')}")
        st.stop()

route = data["routes"][0]
distance = route.get("distance", 0.0)
duration = route.get("duration", 0.0)

st.success("경로 생성 완료!")
st.write(f"총 거리: **{human_km(distance)}** | 예상 시간: **{human_min(duration)}**")
st.caption(f"출발: {s['name']}")
st.caption(f"도착: {e['name']}")

# ----------------------------
# 3) 지도 그리기 (경로만)
# ----------------------------
center_lat = (s["lat"] + e["lat"]) / 2
center_lon = (s["lon"] + e["lon"]) / 2

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")
folium.Marker([s["lat"], s["lon"]], tooltip="출발").add_to(m)
folium.Marker([e["lat"], e["lon"]], tooltip="도착").add_to(m)

geom = route.get("geometry", {})
coords = geom.get("coordinates", [])  # [lon,lat] 리스트
latlon = [[c[1], c[0]] for c in coords]
folium.PolyLine(latlon, weight=6, opacity=0.85).add_to(m)

st_folium(m, width=1050, height=560)

# ----------------------------
# 4) 큰 길(도로명) 뽑기
#    - OSRM steps의 "name"을 모아서 유니크하게
# ----------------------------
legs = route.get("legs", [])
steps = legs[0].get("steps", []) if legs else []

road_names = []
for stp in steps:
    nm = (stp.get("name") or "").strip()
    # 이름이 너무 짧거나 공백이면 제외
    if nm and nm not in road_names:
        road_names.append(nm)

with st.expander("🛣️ 이 경로에서 지나가는 주요 도로/구간 이름 보기", expanded=True):
    if road_names:
        st.write(f"총 **{len(road_names)}개** 도로/구간 이름이 잡혔어.")
        st.write(road_names)
    else:
        st.warning("이 경로에서는 도로명이 충분히 잡히지 않았어. (OSM 데이터에 이름이 비어있거나, 구간이 짧을 때 발생)")
