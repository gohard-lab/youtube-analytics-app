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
    # 데이터를 모두 읽어옵니다. (필요하다면 .eq('app_name', '테슬라_비전_시뮬레이터')를 추가할 수 있습니다)
    response = supabase.table('usage_logs').select("*").execute()
    
    if not response.data:
        return pd.DataFrame() # 데이터가 진짜 없으면 빈 프레임 반환
        
    df = pd.DataFrame(response.data)
    
    # 시간대(Timezone)를 한국 시간(KST)으로 변환하는 핵심 코드
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Seoul')
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')

    return df

try:
    df = load_data()

    if df.empty:
        st.info("아직 데이터가 없습니다. 앱을 실행해 로그를 먼저 쌓아주세요!")
    else:
        # --- [날짜 필터 추가 영역] ---
        st.sidebar.header("🗓️ 기간 필터")
        # 1. Supabase 데이터를 시간대 정보가 포함된 datetime으로 변환
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        # 2. 오늘 날짜도 UTC 기준으로 생성 (시간대 일치)
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
        
        # 데이터가 필터링된 후 개수 확인
        if df.empty:
            st.warning(f"선택하신 '{filter_option}' 기간에는 데이터가 없습니다.")
            st.stop()
        # -----------------------------

        # --- [프로그램 필터 추가 영역] ---
        st.sidebar.divider() # 시각적인 구분선
        
        # DB에 있는 고유한 앱 이름들을 모아서 리스트로 만듭니다.
        # 기존 데이터의 결측치를 방지하기 위해 'Unknown App' 처리
        df['app_name'] = df['app_name'].fillna('Unknown App')
        app_list = ["전체 프로그램"] + df['app_name'].unique().tolist()
        
        selected_app = st.sidebar.selectbox(
            "💻 프로그램 선택",
            app_list
        )

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
                
                # 에러를 일으킨 scrollzoom 대신, 안전하게 줌 기능을 포함한 레이아웃 설정
                # 레이아웃 설정 최적화
                fig_map.update_layout(
                    margin={"r":0, "t":30, "l":0, "b":0},
                    # mapbox 객체 내부의 'config'와 유사한 설정을 통해 제어합니다.
                    mapbox=dict(
                        center=dict(lat=36.5, lon=127.5),
                        zoom=6.5
                    )
                )

                # st.plotly_chart 호출 시 'config' 옵션을 통해 휠 줌을 강제 활성화합니다.
                st.plotly_chart(
                    fig_map, 
                    use_container_width=True,
                    config={'scrollZoom': True} # 이 한 줄이 휠 줌을 강제로 깨웁니다!
                )
            else:
                st.warning("좌표(lat, lon) 데이터가 포함된 새 로그가 필요합니다.")

        # 하단 전체 로그 테이블
        with st.expander("전체 로그 데이터 보기"):
            st.dataframe(df.sort_values(by='timestamp', ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"대시보드 로딩 중 에러 발생: {e}")