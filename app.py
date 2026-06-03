import re
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


API_BASE_URL = "https://service.api.metro.tokyo.lg.jp"
WIFI_API = "t000029d0000000025-a9cf23fb2e2944f5f5e8e535b537f61d-0"
WIFI_SPEC = f"https://spec.api.metro.tokyo.lg.jp/spec/{WIFI_API}"


st.set_page_config(
    page_title="東京都 Wi-Fiアクセスポイントダッシュボード",
    page_icon="📡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin: 0.45rem 0 0.55rem;
    }
    .kpi-card {
        padding: 0.15rem 0;
        min-height: 64px;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: rgba(49, 51, 63, 0.72);
        line-height: 1.2;
        margin-bottom: 0.35rem;
        white-space: nowrap;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.2;
        letter-spacing: 0;
        white-space: nowrap;
    }
    .kpi-subvalue {
        font-size: 1.1rem;
        font-weight: 600;
        margin-left: 0.45rem;
        color: rgba(49, 51, 63, 0.72);
    }
    .compact-divider {
        border-top: 1px solid rgba(49, 51, 63, 0.2);
        margin: 0.45rem 0 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60 * 60)
def post_tokyo_api(api_id: str, limit: int = 1000) -> tuple[pd.DataFrame, dict[str, Any]]:
    session = requests.Session()
    session.trust_env = False
    response = session.post(
        f"{API_BASE_URL}/api/{api_id}/json",
        params={"limit": limit},
        headers={"accept": "application/json", "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    return pd.DataFrame(payload.get("hits", [])), payload.get("metadata", {})


def to_number(value: Any) -> float | None:
    if value in (None, "", "…", "-"):
        return None
    return pd.to_numeric(str(value).replace(",", ""), errors="coerce")


def extract_municipality(address: Any) -> str:
    text = str(address)
    ward_match = re.search(
        r"(千代田区|中央区|港区|新宿区|文京区|台東区|墨田区|江東区|品川区|目黒区|大田区|世田谷区|渋谷区|中野区|杉並区|豊島区|北区|荒川区|板橋区|練馬区|足立区|葛飾区|江戸川区)",
        text,
    )
    if ward_match:
        return ward_match.group(1)

    city_match = re.search(r"東京都(?:.+郡)?(.+?市)", text)
    if city_match:
        return city_match.group(1)

    town_village_match = re.search(r"東京都(?:.+郡)?(.+?[町村])", text)
    return town_village_match.group(1) if town_village_match else "不明"


def build_wifi(raw: pd.DataFrame) -> pd.DataFrame:
    wifi = raw.copy()
    wifi["緯度"] = wifi["緯度"].map(to_number)
    wifi["経度"] = wifi["経度"].map(to_number)
    wifi = wifi.dropna(subset=["緯度", "経度"])
    wifi = wifi.rename(columns={"緯度": "lat", "経度": "lon"})
    wifi["市区町村"] = wifi["住所"].map(extract_municipality)
    return wifi


def render_api_box(title: str, api_id: str, spec_url: str, metadata: dict[str, Any]) -> None:
    with st.expander(title, expanded=False):
        st.code(
            f"""POST {API_BASE_URL}/api/{api_id}/json?limit=1000
Content-Type: application/json

{{}}""",
            language="http",
        )
        st.link_button("API仕様を開く", spec_url)
        if metadata:
            st.json(metadata)


st.title("東京都 Wi-Fiアクセスポイントダッシュボード")
st.caption("東京都オープンデータAPIからFREE Wi-Fi & TOKYOの位置情報を取得し、市区町村単位で可視化します。")

with st.sidebar:
    st.header("表示設定")
    st.write("Web APIにPOSTしてJSONを取得し、住所から市区町村を抽出しています。")
    refresh = st.button("APIからデータを再取得")
    if refresh:
        st.cache_data.clear()
        st.rerun()

try:
    wifi_raw, wifi_metadata = post_tokyo_api(WIFI_API, limit=1000)
except Exception as exc:
    st.error("東京都オープンデータAPIからデータを取得できませんでした。")
    st.exception(exc)
    st.stop()

wifi = build_wifi(wifi_raw)

municipality_counts = (
    wifi.groupby("市区町村", dropna=True)
    .size()
    .sort_values(ascending=False)
    .reset_index(name="アクセスポイント数")
)
municipality_counts.insert(0, "順位", range(1, len(municipality_counts) + 1))
top_municipality = municipality_counts.iloc[0]

st.markdown(
    f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">アクセスポイント</div>
            <div class="kpi-value">{len(wifi):,}件</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">市区町村数</div>
            <div class="kpi-value">{wifi['市区町村'].nunique():,}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">最多エリア</div>
            <div class="kpi-value">{top_municipality['市区町村']}<span class="kpi-subvalue">{top_municipality['アクセスポイント数']:,}件</span></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)

rank_col, map_col = st.columns([1, 1.35])

with rank_col:
    st.subheader("市区町村別アクセスポイント数")
    rank_height = max(580, len(municipality_counts) * 28)
    fig_rank = px.bar(
        municipality_counts,
        x="アクセスポイント数",
        y="市区町村",
        orientation="h",
        text="アクセスポイント数",
        custom_data=["市区町村"],
    )
    fig_rank.update_traces(
        marker_color="#007C89",
        hovertemplate="%{y}<br>%{x:,}件<extra></extra>",
        textangle=0,
    )
    fig_rank.update_layout(
        height=rank_height,
        yaxis={"categoryorder": "total ascending"},
        margin={"l": 0, "r": 35, "t": 10, "b": 0},
        xaxis_title="アクセスポイント数",
        yaxis_title="",
    )
    with st.container(height=580, border=False):
        rank_event = st.plotly_chart(
            fig_rank,
            width="stretch",
            key="municipality_rank",
            on_select="rerun",
            selection_mode="points",
        )

selected_from_chart = None
if rank_event and rank_event.selection.points:
    selected_from_chart = rank_event.selection.points[0]["customdata"][0]

selected_municipality = selected_from_chart
map_data = wifi if selected_municipality is None else wifi[wifi["市区町村"] == selected_municipality]
map_center = None
map_zoom = 9
if selected_municipality is not None and not map_data.empty:
    map_center = {"lat": map_data["lat"].mean(), "lon": map_data["lon"].mean()}
    map_zoom = 13

with map_col:
    title = "FREE Wi-Fi & TOKYO アクセスポイント"
    if selected_municipality is not None:
        title = f"{selected_municipality}のアクセスポイント"
    st.subheader(title)
    map_args = {
        "data_frame": map_data,
        "lat": "lat",
        "lon": "lon",
        "hover_name": "名称",
        "hover_data": ["住所", "市区町村", "SSID", "設置者"],
        "color_discrete_sequence": ["#F28E2B"],
        "zoom": map_zoom,
        "height": 580,
    }
    if map_center is not None:
        map_args["center"] = map_center
    fig_map = px.scatter_map(**map_args)
    fig_map.update_layout(
        map_style="carto-positron",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        showlegend=False,
    )
    st.plotly_chart(fig_map, width="stretch")
    st.caption(f"表示件数: {len(map_data):,}件")

tab_data, tab_api = st.tabs(["取得データ", "API取得内容"])

with tab_data:
    st.subheader("公衆無線LANアクセスポイント一覧")
    display_columns = ["名称", "住所", "市区町村", "SSID", "設置者", "提供エリア", "lat", "lon", "最終確認日"]
    st.dataframe(
        map_data[[column for column in display_columns if column in map_data.columns]],
        width="stretch",
        hide_index=True,
    )

with tab_api:
    render_api_box("公衆無線LANアクセスポイント一覧 API", WIFI_API, WIFI_SPEC, wifi_metadata)
