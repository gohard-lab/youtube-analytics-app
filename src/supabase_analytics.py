import streamlit as st
import pandas as pd
import plotly.express as px
from tracker import get_supabase_client
from supabase import create_client

# 1. secrets.toml에서 정보를 안전하게 불러옵니다.
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="사용자 분석 대시보드", layout="wide")

st.title("🌐 글로벌 사용량 분석 대시보드")
st.markdown("전 세계 어디서 우리 프로그램을 사용하고 있는지 실시간으로 확인합니다.")

@st.cache_data(ttl=30)
def load_data():
    # 데이터를 모두 읽어옵니다.
    response = supabase.table('usage_logs').select("*").execute()
    
    if not response.data:
        return pd.DataFrame() 
        
    df = pd.DataFrame(response.data)
    
    # 1. 섞여 있는 모든 날짜 형식을 유연하게 읽어들입니다.
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')

    # 2. 대시보드 그래프가 에러 나지 않도록 꼬리표 강제 제거
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)

    return df

try:
    df = load_data()

    if df.empty:
        st.info("아직 데이터가 없습니다. 앱을 실행해 로그를 먼저 쌓아주세요!")
    else:
        # --- [날짜 필터 추가 영역] ---
        st.sidebar.header("🗓️ 기간 필터")
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        today = pd.Timestamp.now(tz='UTC').normalize()
        
        filter_option = st.sidebar.selectbox(
            "조회 기간을 선택하세요",
            ["전체 기간", "오늘", "최근 7일", "이번 달"]
        )

        if filter_option == "오늘":
            df = df[df['timestamp'].dt.normalize() == today]
        elif filter_option == "최근 7일":
            seven_days_ago = today - pd.Timedelta(days=7)
            df = df[df['timestamp'] >= seven_days_ago]
        elif filter_option == "이번 달":
            df = df[df['timestamp'].dt.month == today.month]
        
        if df.empty:
            st.warning(f"선택하신 '{filter_option}' 기간에는 데이터가 없습니다.")
            st.stop()
        # -----------------------------

        # --- [프로그램 필터 추가 영역] ---
        st.sidebar.divider() 
        
        df['app_name'] = df['app_name'].fillna('Unknown App')
        app_list = ["전체 프로그램"] + df['app_name'].unique().tolist()
        
        selected_app = st.sidebar.selectbox(
            "💻 프로그램 선택",
            app_list
        )

        # 🚨 [핵심 변경 사항] 프로그램 콤보박스 바로 아래에 조회 버튼 배치
        st.sidebar.write("") # 약간의 시각적 여백 추가
        if st.sidebar.button("🔄 조건에 맞게 최신 데이터 조회", use_container_width=True):
            # 1. DB에서 가장 최신 데이터를 가져오기 위해 캐시 삭제
            load_data.clear()
            # 2. 화면 전체 새로고침 (선택된 조건 유지된 상태로 새 데이터 반영)
            st.rerun()
        st.sidebar.divider()

        # '전체 프로그램'이 아닌 특정 앱을 선택했을 때만 데이터를 필터링합니다.
        if selected_app != "전체 프로그램":
            df = df[df['app_name'] == selected_app]
            
        if df.empty:
            st.warning(f"선택하신 '{selected_app}'의 데이터가 없습니다.")
            st.stop()
        # -----------------------------

        # 상단 지표
        c1, c2, c3 = st.columns(3)
        c1.metric("총 이벤트", f"{len(df)}건")
        c2.metric("방문 도시 수", f"{df['city'].nunique()}곳")
        c3.metric("최근 활동", df.iloc[-1]['city'])

        # 메인 시각화 섹션
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📍 지역별 접속 비중 (Pie Chart)")
            city_counts = df['city'].value_counts().reset_index()
            city_counts.columns = ['City', 'Count']
            fig_pie = px.pie(city_counts, values='Count', names='City', 
                             hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.subheader("🔥 접속 지역 히트맵 (Heatmap)")
            map_data = df[df['lat'] != 0].copy()
            
            if not map_data.empty:
                fig_map = px.density_mapbox(
                    map_data, 
                    lat='lat', 
                    lon='lon', 
                    z='id', 
                    radius=30,
                    center=dict(lat=36.5, lon=127.5),
                    zoom=6.5,
                    mapbox_style="open-street-map",
                    height=800
                )
                
                fig_map.update_layout(
                    margin={"r":0, "t":30, "l":0, "b":0},
                    mapbox=dict(
                        center=dict(lat=36.5, lon=127.5),
                        zoom=6.5
                    )
                )

                st.plotly_chart(
                    fig_map, 
                    use_container_width=True,
                    config={'scrollZoom': True} 
                )
            else:
                st.warning("좌표(lat, lon) 데이터가 포함된 새 로그가 필요합니다.")

        # ---------------------------------------------------------
        # 🚨 [가로 스크롤 반영] 화면 하단의 옛날 버튼은 지우고 그리드만 남김
        # ---------------------------------------------------------
        st.divider() 
        with st.expander("전체 로그 데이터 보기"):
            # use_container_width=True 를 제거하여 원본 크기로 쾌적하게 가로 스크롤 가능!
            st.dataframe(df.sort_values(by='timestamp', ascending=False))

except Exception as e:
    st.error(f"대시보드 로딩 중 에러 발생: {e}")