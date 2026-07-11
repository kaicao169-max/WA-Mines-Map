# %%
import numpy as np
import json
import re
import folium
import geopandas as gpd
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Search, HeatMap
# %%
AREA_OPTIONS = {
    "Show all": (0, float('inf')),
    "Small (<50ha)": (0, 50),
    "Medium (50-500ha)": (50, 500),
    "Large (500-5000ha)": (500, 5000),
    "Extra-large (>5000ha)": (5000, float('inf'))
}
# %%
AREA_STYLES = {
    "Small (<50ha)": {'fillColor': '#d4edda', 'color': 'black', 'weight': 1, 'fillOpacity': 0.6},
    "Medium (50-500ha)": {'fillColor': '#76c7c0', 'color': 'black', 'weight': 1, 'fillOpacity': 0.6},
    "Large (500-5000ha)": {'fillColor': '#4a90e2', 'color': 'black', 'weight': 1, 'fillOpacity': 0.6},
    "Extra-large (>5000ha)": {'fillColor': '#d0021b', 'color': 'black', 'weight': 1, 'fillOpacity': 0.6}
}
# %%
POPUP_TEMPLATE = """
<div style="width: 250px; font-family: sans-serif; line-height: 1.4;">
    <h4 style="margin: 0 0 10px 0; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px;">信息详情</h4>
    <div style="margin-bottom: 5px;"><b>ID:</b> {tenid}</div>
    <div style="margin-bottom: 5px;"><b>日期:</b> {startdate}</div>
    <div style="margin-bottom: 5px;"><b>持有人:</b> {holder1}</div>
</div>
"""
# %%
@st.cache_data
def get_map():
    with open("BASE_MAP.json", 'r', encoding='utf-8') as f:
        return json.load(f)
BASE_MAP = get_map()
# %%
@st.cache_data
def get_data():
    gdf = gpd.read_file(r"data\WA_Mines_30483.geojson")
    gdf = gdf.to_crs(epsg=4326)
    return gdf
placeholder = st.empty()
with placeholder:
    st.info("Data geting...")
    origin_gdf = get_data()
placeholder.empty()
gdf = origin_gdf.copy()
# %%
@st.cache_data
def filter_criteria():
    all_holders = list(gdf['holder1'].unique())
    all_status = list(gdf['tenstatus'].unique())
    all_area = list(AREA_OPTIONS.keys())
    return all_holders, all_area, all_status
all_holders, all_area, all_status = filter_criteria()
# %%
@st.cache_data
def get_marker_info():
    data = new_gdf.geometry.centroid
    points = [[point.y, point.x] for point in data]
    return points
# %%
@st.cache_data
def status_style(feature):
    status = feature['properties']['tenstatus']
    if status == 'LIVE':
        return {
            'fillColor': '#28a745',  # 稳重的绿色
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        }
    elif status == 'PENDING':
        return {
            'fillColor': '#fd7e14',  # 醒目的橙色
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        }
    else:
        return {
            'fillColor': '#6c757d',  # 灰色
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        }
# %%
@st.cache_data
def highlight_style(feature):
    return {
        'fillColor': '#ffffff',  # 悬停时填充色变白（高亮）
        'color': 'red',          # 边界变红
        'weight': 3,             # 边界加粗到 3，非常明显
        'fillOpacity': 0.8       # 透明度增加，看起来更亮
    }
# %%
@st.cache_data
def area_style(feature):
    area = feature['properties']['legal_area']
    
    if area < 50:
        key = "Small (<50ha)"
    elif area < 500:
        key = "Medium (50-500ha)"
    elif area < 5000:
        key = "Large (500-5000ha)"
    else:
        key = "Extra-large (>5000ha)"

    return AREA_STYLES[key]
# %%
st.set_page_config(page_title="WA_Mines_Dashboard", page_icon="🗻", layout="wide")
st.markdown("""
    <style>
        /* 调整主区域顶部的 Padding */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        /* 如果你想把标题和子标题间的空隙也减小 */
        h1 { margin-top: -20px; }
        h2 { margin-top: -20px; }
            
        /* 强制列容器填满 */
        [data-testid="column"] {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)
st.title("Interactive Map of Mining Tenement in WA")
st.sidebar.title("Filter Criteria")
# %%
YEAR = sorted(gdf['startdate'].dt.year.unique())
max_date = max(YEAR)
# %%
with st.sidebar.form("filter_form"):
    selected_date = st.sidebar.select_slider(
        "Choose deadline",
        options=YEAR,
        value=max_date,
        help="拖动滑块以查看截止到该日期的矿权热度分布"
    )

    holder_choice = st.sidebar.selectbox("Filter holders", ["Show all"] + all_holders)
    Area_choice = st.sidebar.selectbox("Filter area", all_area)
    Status_choice = st.sidebar.selectbox("Filter status",  ["Show all"] + all_status)

    max_val_input = st.sidebar.slider(
        "Heat Comparison of HeatMap", 
        min_value=0.01,
        max_value=1.0,
        value=0.6,
        step=0.05
    )

    submitted = st.form_submit_button("Start Analyzing")
# %%
if submitted:
    st.session_state.gdf = gdf[gdf['startdate'].dt.year <= selected_date]

    st.session_state['heatmap_ready'] = (
        (holder_choice == "Show all") 
        and (Area_choice == "Show all") 
        and (Status_choice == "Show all")
    )

if 'heatmap_ready' not in st.session_state:
    st.info('Please select filter criteria in the sidebar, then click the "Start Analysis" button.')
    st.stop()

if st.session_state.heatmap_ready:
    temp_weight = np.log1p(st.session_state.gdf['legal_area'])
    norm_weight = (temp_weight - temp_weight.min()) / (temp_weight.max() - temp_weight.min())
    bounds_1 = gdf.total_bounds
    lat = (bounds_1[1] + bounds_1[3]) / 2
    lon = (bounds_1[0] + bounds_1[2]) / 2
    st.info("High-performance aggregated view has been enabled for you.")
    m = folium.Map(location=[lat, lon], zoom_start=11)
    heat_data = [[row.geometry.centroid.y, row.geometry.centroid.x, norm_weight[i]] 
                for i, row in st.session_state.gdf.iterrows()]
    HeatMap(heat_data, radius=6, blur=8, max_val=max_val_input).add_to(m)
    st_folium(m, key="my_map", returned_objects=[], width=1000, height=700)
else:
    min_area, max_area = AREA_OPTIONS[Area_choice]
    new_gdf = st.session_state.gdf.copy()
    new_gdf['startdate'] = new_gdf['startdate'].dt.strftime('%Y-%m-%d')

    if holder_choice != "Show all":
        new_gdf = new_gdf.loc[new_gdf["holder1"] == holder_choice]

    if Area_choice != "Show all":
        new_gdf = new_gdf.loc[(new_gdf["legal_area"] >= min_area) & (new_gdf["legal_area"] < max_area)]

    if Status_choice != "Show all":
        new_gdf = new_gdf.loc[new_gdf["tenstatus"] == Status_choice]

    if len(new_gdf) == 0:
        st.warning("⚠️ No tenement matching the current filter criteria was found!")
    
        # 方式 B：显示一张空白地图或提示图（防止页面留白太突兀）
        st.info("💡 Note: You can try to change 'holder' or adjust the area range.")

        m_empty = folium.Map(location=[-25, 135], zoom_start=4)
        st_folium(m_empty, width=1200, height=800)

    col_1, col_2 = st.columns([8, 2])
    
    new_gdf['geometry'] = new_gdf.geometry.simplify(tolerance=0.005, preserve_topology=True)

    points = get_marker_info()
    bounds = new_gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], tiles=None, width="100%", height="100%")

    for name, value in BASE_MAP.items():
        folium.TileLayer(
            tiles=value.get('url', None),
            attr=value.get('attr', None),
            name=name
        ).add_to(m)
    fast_cluster = MarkerCluster(name="Marker Layer").add_to(m)
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    status_layer = folium.GeoJson(
        data=new_gdf,
        style_function=status_style,
        highlight_function=highlight_style,
        tooltip=folium.GeoJsonTooltip(fields=['tenid', 'tenstatus', 'holder1'],
                                    aliases=['ID: ', "Status: ", "Holder: "],
                                    localize=True),
        name="Status Layer"
    ).add_to(m)


    area_layer = folium.GeoJson(
        data=new_gdf,
        style_function=area_style,
        highlight_function=highlight_style,
        tooltip=folium.GeoJsonTooltip(fields=['tenid', 'legal_area', 'holder1'],
                                    aliases=['ID: ', "Area(ha): ", "Holder: "],
                                    localize=True),
        name="Area Layer"
    ).add_to(m)

    for _, row in new_gdf.iterrows():
        folium.CircleMarker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            radius=10,
            color="#080707",
            fill=True,
            fill_color="#070841",
            fill_opacity=0.6,
            popup=folium.Popup(html=POPUP_TEMPLATE.format(**row), max_width=300)
        ).add_to(fast_cluster)

    Search(
        layer=status_layer,
        search_label="tenid",
        placeholder="Please enter id tp search the mine",
        collapsed=True,
        search_zoom=12
    ).add_to(m)

    folium.LayerControl().add_to(m)
    with col_1:
        map_content = st_folium(
            m, 
            key='my_map', 
            use_container_width=True, 
            height=600,
            returned_objects=['last_object_clicked_tooltip'])
        
    # map_content['last_object_clicked_tooltip']返回的是一个长字符串
    st.session_state.map_content = map_content['last_object_clicked_tooltip']

    with col_2:
        st.metric('Total area(ha):', f"{new_gdf['legal_area'].sum():.4f}")
        st.metric('Total number:', len(new_gdf))

        if st.session_state.map_content:
            full_tooltip = st.session_state.map_content
            # tooltip_list = full_tooltip.split(':')
            # tooltip_str = (',').join(tooltip_list)

            click_id = None

            match = re.search(r'([A-Za-z]+\d+)', full_tooltip)

            if match:
                click_id = match.group(1)
                st.write(f"Successfully Get ID: {click_id}")
                selected_row = new_gdf[new_gdf['tenid'].astype(str).str.strip() == click_id]

                tab1, tab2 = st.tabs(["Key Information", "Statistical analysis"])

                with tab1:
                    st.write(selected_row.T) # .T 是转置，让信息竖着排列，更适合侧边栏阅读
                with tab2:
                    st.bar_chart(None)
            else:
                st.info("Didn't find anything.")

        else:
            st.info("No ID, No Data Table!")
