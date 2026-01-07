import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import time
from urllib.parse import urlencode

st.set_page_config(page_title="OSM Navi UI", layout="wide")
st.title("🧭 OpenStreetMap 네비 느낌 경로 안내 (OSRM + Nominatim)")

# ----------------------------
# 유틸
# ----------------------------
def human_km(meters: float) -> str:
    return f"{meters/1000:.2f} km"

def human_min(seconds: float) -> str:
    return f"{seconds/60:.0f} min"

def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# ----------------------------
# 1) 지오코딩: Nominatim (주소 -> 좌표)
# - 무료지만 트래픽 제한 있음. 과도 호출 금지!
# ----------------------------
def geocode_nominatim(query: str, limit=1):
    if not query.strip():
        return None
    base = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": str(limit)}
    url = base + "?" + urlencode(params)

    # Nominatim은 User-Agent 필수 권장
    headers = {"User-Agent": "streamlit-osm-navi-demo/1.0 (learning project)"}

    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    display_name = data[0].get("display_name", query)
    return {"lat": lat, "lon": lon, "name": display_name}

# ----------------------------
# 2) 라우팅: OSRM public (좌표 -> 경로 + steps)
# ----------------------------
def route_osrm(start_lat, start_lon, end_lat, end_lon, profile="driving"):
    # OSRM은 lon,lat 순서!
    base = "https://router.project-osrm.org/route/v1"
    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }
    url = f"{base}/{profile}/{coords}?" + urlencode(params)

    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

# ----------------------------
# 세션 상태
# ----------------------------
if "route" not in st.session_state:
    st.session_state.route = None
if "start" not in st.session_state:
    st.session_state.start = None
if "end" not in st.session_state:
    st.session_state.end = None
if "step_idx" not in st.session_state:
    st.session_state.step_idx = 0

# ----------------------------
# UI: 입력
# ----------------------------
st.caption("✅ 주소 입력(지오코딩) 또는 위/경도 입력 → OSRM으로 경로 계산 → 네비처럼 단계 안내")

tab1, tab2 = st.tabs(["📍 주소로 찾기", "🧷 위/경도로 입력"])

with tab1:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        start_addr = st.text_input("출발지 주소", value="서울역")
    with c2:
        end_addr = st.text_input("도착지 주소", value="광화문")
    with c3:
        profile = st.selectbox("이동 수단(프로필)", ["driving", "walking", "cycling"], index=0)

    geocode_btn = st.button("🔎 주소로 경로 만들기", use_container_width=True)

with tab2:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.subheader("출발 좌표")
        s_lat = st.number_input("출발 위도", value=37.5551, format="%.6f")
        s_lon = st.number_input("출발 경도", value=126.9707, format="%.6f")
    with c2:
        st.subheader("도착 좌표")
        e_lat = st.number_input("도착 위도", value=37.5759, format="%.6f")
        e_lon = st.number_input("도착 경도", value=126.9768, format="%.6f")
    with c3:
        profile2 = st.selectbox("이동 수단(프로필)", ["driving", "walking", "cycling"], index=0, key="profile2")

    coords_btn = st.button("🧭 좌표로 경로 만들기", use_container_width=True)

reset_btn = st.button("🧹 초기화", type="secondary")

# ----------------------------
# 동작: 초기화
# ----------------------------
if reset_btn:
    st.session_state.route = None
    st.session_state.start = None
    st.session_state.end = None
    st.session_state.step_idx = 0
    st.rerun()

# ----------------------------
# 동작: 주소 기반
# ----------------------------
if geocode_btn:
    with st.spinner("주소를 좌표로 변환하고(OSM), 경로를 계산하는 중(OSRM)..."):
        # 과도 호출 방지(예의)
        time.sleep(0.5)

        s = geocode_nominatim(start_addr)
        time.sleep(0.5)
        e = geocode_nominatim(end_addr)

        if s is None or e is None:
            st.error("주소를 좌표로 못 찾았어. 다른 표현으로 입력하거나 좌표 입력 탭을 써줘.")
        else:
            data = route_osrm(s["lat"], s["lon"], e["lat"], e["lon"], profile=profile)
            if data.get("code") != "Ok":
                st.error(f"경로 계산 실패: {data.get('message', 'unknown error')}")
            else:
                st.session_state.start = s
                st.session_state.end = e
                st.session_state.route = data
                st.session_state.step_idx = 0
                st.success("경로 생성 완료!")
                st.rerun()

# ----------------------------
# 동작: 좌표 기반
# ----------------------------
if coords_btn:
    with st.spinner("좌표 기반으로 경로를 계산하는 중(OSRM)..."):
        data = route_osrm(s_lat, s_lon, e_lat, e_lon, profile=profile2)
        if data.get("code") != "Ok":
            st.error(f"경로 계산 실패: {data.get('message', 'unknown error')}")
        else:
            st.session_state.start = {"lat": float(s_lat), "lon": float(s_lon), "name": "Start"}
            st.session_state.end = {"lat": float(e_lat), "lon": float(e_lon), "name": "End"}
            st.session_state.route = data
            st.session_state.step_idx = 0
            st.success("경로 생성 완료!")
            st.rerun()

# ----------------------------
# 3) 결과 표시 (지도 + 네비 UI)
# ----------------------------
route = st.session_state.route
if route is None:
    st.info("왼쪽 탭에서 출발/도착을 입력하고 경로를 만들어줘. (주소 또는 좌표)")
    st.stop()

# 경로 기본 정보
routes = route.get("routes", [])
if not routes:
    st.error("경로 데이터가 비어있어. 다시 시도해줘.")
    st.stop()

best = routes[0]
distance = best.get("distance", 0.0)
duration = best.get("duration", 0.0)

legs = best.get("legs", [])
steps = []
if legs:
    steps = legs[0].get("steps", [])

# 현재 step index 보정
if st.session_state.step_idx < 0:
    st.session_state.step_idx = 0
if st.session_state.step_idx >= max(1, len(steps)):
    st.session_state.step_idx = max(0, len(steps) - 1)

# 레이아웃
left, right = st.columns([2.2, 1], gap="large")

with right:
    st.subheader("📟 네비 패널")
    st.write(f"**총 거리:** {human_km(distance)}")
    st.write(f"**예상 시간:** {human_min(duration)}")
    st.write(f"**스텝 수:** {len(steps)}")

    st.divider()

    if steps:
        cur = steps[st.session_state.step_idx]
        instr = safe_get(cur, "maneuver", "instruction", default="(안내 없음)")
        step_dist = cur.get("distance", 0.0)
        step_dur = cur.get("duration", 0.0)
        name = cur.get("name", "")

        st.markdown(f"### ➡️ 다음 안내")
        st.markdown(f"**{instr}**")
        if name:
            st.caption(f"도로/구간: {name}")
        st.write(f"구간 거리: {human_km(step_dist)}")
        st.write(f"구간 시간: {human_min(step_dur)}")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("◀ 이전", use_container_width=True):
                st.session_state.step_idx = max(0, st.session_state.step_idx - 1)
                st.rerun()
        with c2:
            if st.button("⏺ 처음", use_container_width=True):
                st.session_state.step_idx = 0
                st.rerun()
        with c3:
            if st.button("다음 ▶", use_container_width=True):
                st.session_state.step_idx = min(len(steps) - 1, st.session_state.step_idx + 1)
                st.rerun()

        st.divider()
        with st.expander("🧾 전체 안내(턴바이턴) 보기", expanded=False):
            for i, s in enumerate(steps):
                ins = safe_get(s, "maneuver", "instruction", default="")
                d = s.get("distance", 0.0)
                if i == st.session_state.step_idx:
                    st.markdown(f"**[{i+1}] {ins}** — {human_km(d)}")
                else:
                    st.write(f"[{i+1}] {ins} — {human_km(d)}")
    else:
        st.warning("steps 정보가 없는 경로야. (OSRM 응답이 간단한 경우)")

with left:
    st.subheader("🗺️ 지도 (OSM)")
    s = st.session_state.start
    e = st.session_state.end

    # 지도 중심
    center_lat = (s["lat"] + e["lat"]) / 2
    center_lon = (s["lon"] + e["lon"]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")

    # 출발/도착 마커
    folium.Marker([s["lat"], s["lon"]], popup=f"출발: {s.get('name','Start')}", tooltip="출발").add_to(m)
    folium.Marker([e["lat"], e["lon"]], popup=f"도착: {e.get('name','End')}", tooltip="도착").add_to(m)

    # 경로선
    geom = best.get("geometry", {})
    coords = geom.get("coordinates", [])  # (lon,lat)
    latlon = [[c[1], c[0]] for c in coords]  # folium은 (lat,lon)
    folium.PolyLine(latlon, weight=6, opacity=0.85).add_to(m)

    # 현재 step 위치 표시(가능할 때)
    if steps:
        cur = steps[st.session_state.step_idx]
        loc = safe_get(cur, "maneuver", "location", default=None)  # [lon, lat]
        if loc:
            folium.CircleMarker(
                location=[loc[1], loc[0]],
                radius=8,
                popup="현재 스텝",
                tooltip="현재 스텝",
                fill=True
            ).add_to(m)

    st_folium(m, width=950, height=560)

st.caption("※ 무료 공개 지오코딩/라우팅을 사용하므로 과도한 호출은 제한될 수 있어. (학습/포트폴리오용으로는 충분히 좋아)")
