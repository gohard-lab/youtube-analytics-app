import streamlit as st
import plotly.express as px 

# 🚨 [해결] 무조건 다른 모든 st. 명령어보다 먼저 와야 함! (최상단 배치 완료)
st.set_page_config(page_title="사용자 분석 대시보드", layout="wide")

import pandas as pd
import plotly.express as px
from supabase import create_client

# 1. secrets.toml에서 정보를 안전하게 불러옵니다.
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🌐 글로벌 사용량 분석 대시보드")
st.markdown("전 세계 어디서 우리 프로그램을 사용하고 있는지 실시간으로 확인합니다.")

@st.cache_data(ttl=30)
def load_data():
    # 🚨 [핵심 패치] order() 내림차순 정렬과 limit()을 명시하여 최신 데이터를 우선적으로 확보합니다.
    response = supabase.table('usage_logs').select("*").order("timestamp", desc=True).limit(100000).execute()
    
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
        # 💡 [PATCH] Preserve absolute raw dataframe for overall ranking calculation
        raw_df = df.copy()

        # --- [날짜 필터 추가 영역] ---
        st.sidebar.header("🗓️ 기간 필터")
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        today = pd.Timestamp.now(tz='UTC').normalize()
        
        filter_option = st.sidebar.selectbox(
            "조회 기간을 선택하세요",
            ["전체 기간", "오늘", "최근 7일", "이번 달"]
        )

        # 🚨 [패치 1] 날짜 필터링을 가하기 전에, 원본 데이터에서 프로그램 고유 목록을 무조건 먼저 추출합니다!
        # 이렇게 해야 선택한 기간에 데이터가 없더라도 콤보박스에 'pwned_checker_web'이 사라지지 않고 유지됩니다.
        if 'app_name' in df.columns:
            # 결측치 처리 및 문자열 공백 제거 전처리
            clean_series = df['app_name'].fillna('Unknown App').astype(str).str.strip()
            # 대소문자 구분 없이 순수한 알파벳/한글 순 정렬 (A-Z)
            unique_apps = sorted(list(set(clean_series.unique())), key=str.lower)
            app_list = ["전체 프로그램"] + unique_apps
        else:
            app_list = ["전체 프로그램"]


        # 이후에 날짜 필터링 조건을 유연하게 적용합니다.
        if filter_option == "오늘":
            df = df[df['timestamp'].dt.normalize() == today]
        elif filter_option == "최근 7일":
            seven_days_ago = today - pd.Timedelta(days=7)
            df = df[df['timestamp'] >= seven_days_ago]
        elif filter_option == "이번 달":
            df = df[df['timestamp'].dt.month == today.month]

        
        # 특정 기간에 데이터가 비어있을 때는 사이드바 경고만 띄우고 흐름을 유지합니다.
        if df.empty:
            st.sidebar.warning(f"⚠️ '{filter_option}' 기간에 조회된 데이터가 없습니다.")
        # -----------------------------

        # --- [프로그램 필터 추가 영역] ---
        st.sidebar.divider() 

        selected_app = st.sidebar.selectbox(
            "💻 프로그램 선택",
            options=app_list,
            index=0
        )

        # 💡 [UI REFACTOR] Removed the manual submit button. 
        # Streamlit naturally triggers a reactive re-run whenever any sidebar widget state changes.
        st.sidebar.divider()

        # ==========================================================
        # 📊 [LOCAL FILTER REFACTOR] Switch view targets instantly
        # ==========================================================
        view_mode = st.sidebar.radio(
            "📊 모니터링 목적 선택", 
            [
                "👥 순수 시청자 통계 보기", 
                "🛠️ 나의 로컬 테스트 이력 보기",
                "⚙️ 시스템 유령 핑 및 인프라 봇 보기",
                "🤖 자동화 로봇 점검 (뉴스 포스터 / 유튜브 동기화)"
            ]
        )

        # Define common bot/ghost condition flags
        is_automation = df['app_name'].isin(['news_auto_poster', 'youtube_hub_sync'])
        is_bot = df['user_agent'].str.contains('github|cron|bot|uptime|polymath-engine-ping|polymath', case=False, na=False)
        is_ghost = (df['user_agent'] == 'Unknown') | (df['ip_address'] == 'Pending') | (df['ip_address'] == 'TypeError: Failed to fetch')
        is_us = df['country'] == 'United States'
        
        # 🚨 [CRITICAL BEHAVIORAL PATCH] Catch disguised infrastructure bots based on export analysis
        # 1. Filter out users who only trigger 'dashboardTab_opened' with an 'Unknown' IP address
        # 2. Filter out the static legacy browser signature ('Chrome/124.0.0.0') used by the system checker
        is_disguised_bot = (
            ((df['ip_address'] == 'Unknown') & (df['action'] == 'dashboardTab_opened')) | 
            df['user_agent'].str.contains('Chrome/124.0.0.0', na=False)
        )

        # 🕵️‍♂️ [CAPTURE CEO's TESTS] Isolate CEO's local subnet, Namyangju public IPs, and city
        is_my_local_ip = df['ip_address'].str.startswith(('192.168.', '127.0.0.1'), na=False)
        is_my_public_ip = df['ip_address'].isin(['125.142.130.52', '125.142.130.77'])
        is_namyangju = df['city'] == 'Namyangju'

        is_my_test = (is_my_local_ip | is_my_public_ip | is_namyangju)

        if view_mode == "👥 순수 시청자 통해 보기":
            # Cleanly exclude all backend bots, ghosts, US traffic, and newly identified disguised system bots
            df = df[~(is_automation | is_bot | is_ghost | is_us | is_disguised_bot)]
            
        elif view_mode == "🛠️ 나의 로컬 테스트 이력 보기":
            df = df[is_my_test]

        elif view_mode == "⚙️ 시스템 유령 핑 및 인프라 봇 보기":
            # Include newly identified disguised bots into the infrastructure view target
            df = df[(is_bot | is_ghost | is_us | is_disguised_bot) & ~is_automation]

        elif view_mode == "🤖 자동화 로봇 점검 (뉴스 포스터 / 유튜브 동기화)":
            df = df[is_automation]
            
            
        if df.empty:
            st.warning("선택하신 필터 조건에 해당하는 데이터가 없습니다.")
            st.stop()
        # ----------------------------------------------------------

        # '전체 프로그램'이 아닌 특정 앱을 선택했을 때만 데이터를 필터링합니다.
        # 1. 💻 [APP FILTER] Filter main dataframe by selected app first
        if not df.empty and selected_app != "전체 프로그램":
            df = df[df['app_name'] == selected_app]

        # 2. 🛡️ [VIEW MODE FILTER] Apply bot, ghost, US, disguised bot, and CEO test filters to MAIN df
        is_automation = df['app_name'].isin(['news_auto_poster', 'youtube_hub_sync'])
        is_bot = df['user_agent'].str.contains('github|cron|bot|uptime|polymath-engine-ping|polymath|prerender', case=False, na=False)
        is_ghost = (df['user_agent'] == 'Unknown') | (df['ip_address'] == 'TypeError: Failed to fetch')        
        is_us = df['country'] == 'United States'
        is_disguised_bot = (
            ((df['ip_address'] == 'Unknown') & (df['action'] == 'dashboardTab_opened')) | 
            df['user_agent'].str.contains('Chrome/124.0.0.0', na=False)
        )

        # CEO's digital footprint flags for main dataframe
        is_my_local_ip = df['ip_address'].str.startswith(('192.168.', '127.0.0.1'), na=False)
        is_my_public_ip = df['ip_address'].isin(['125.142.130.52', '125.142.130.77'])
        is_namyangju = df['city'] == 'Namyangju'
        is_my_test = (is_my_local_ip | is_my_public_ip | is_namyangju)

        # 💡 [PERFECT SYNC] Exclude is_my_test from pure viewers view target
        if view_mode == "👥 순수 시청자 통계 보기":
            df = df[~(is_automation | is_bot | is_ghost | is_us | is_disguised_bot | is_my_test)]
        elif view_mode == "🛠️ 나의 로컬 테스트 이력 보기":
            df = df[is_my_test]
        elif view_mode == "🤖 자동화 로봇 점검 (뉴스 포스터 / 유튜브 동기화)":
            df = df[is_automation]
        elif view_mode == "⚙️ 시스템 유령 핑 및 인프라 봇 보기":
            df = df[(is_bot | is_ghost | is_us | is_disguised_bot) & ~is_automation]

        if df.empty:
            st.warning("선택하신 필터 조건에 해당하는 데이터가 없습니다.")
            st.stop()

        # 3. 🏆 [LEADERBOARD BASE] Calculate absolute totals for ranking chart (using raw_df)
        if 'app_name' in raw_df.columns and not raw_df.empty:
            raw_automation = raw_df['app_name'].isin(['news_auto_poster', 'youtube_hub_sync'])
            raw_bot = raw_df['user_agent'].str.contains('github|cron|bot|uptime|polymath-engine-ping|polymath|prerender', case=False, na=False)
            raw_ghost = (raw_df['user_agent'] == 'Unknown') | (raw_df['ip_address'] == 'TypeError: Failed to fetch')
            raw_us = raw_df['country'] == 'United States'
            raw_disguised_bot = (
                ((raw_df['ip_address'] == 'Unknown') & (raw_df['action'] == 'dashboardTab_opened')) | 
                raw_df['user_agent'].str.contains('Chrome/124.0.0.0', na=False)
            )

            raw_my_local_ip = raw_df['ip_address'].str.startswith(('192.168.', '127.0.0.1'), na=False)
            raw_my_public_ip = raw_df['ip_address'].isin(['125.142.130.52', '125.142.130.77'])
            raw_namyangju = raw_df['city'] == 'Namyangju'
            raw_my_test = (raw_my_local_ip | raw_my_public_ip | raw_namyangju)

            if view_mode == "👥 순수 시청자 통계 보기":
                rank_base = raw_df[~(raw_automation | raw_bot | raw_ghost | raw_us | raw_disguised_bot | raw_my_test)]
            elif view_mode == "🛠️ 나의 로컬 테스트 이력 보기":
                rank_base = raw_df[raw_my_test]
            elif view_mode == "🤖 자동화 로봇 점검 (뉴스 포스터 / 유튜브 동기화)":
                rank_base = raw_df[raw_automation]
            elif view_mode == "⚙️ 시스템 유령 핑 및 인프라 봇 보기":
                rank_base = raw_df[(raw_bot | raw_ghost | raw_us | raw_disguised_bot) & ~raw_automation]
        else:
            rank_base = raw_df

        # --- [상단 지표 출력 부분] ---
        c1, c2, c3 = st.columns(3)
        
        # 💡 [PERFECT SYNC FIX] Now df is fully filtered by both App and View Mode. 
        # len(df) will accurately display 91 instead of 1647.
        display_count = len(df)
        
        c1.metric("총 이벤트", f"{display_count}건")
        c2.metric("방문 도시 수", f"{df['city'].nunique()}곳")
        
        # Prevent error if dataframe is empty after filtering
        # Unknown, null, 빈 값 제외 후 최신 도시 추출 (timestamp DESC 정렬 기준)
        if not df.empty and 'city' in df.columns:
            valid_df = df[df['city'].notnull() & ~df['city'].isin(['Unknown', '', 'null'])]
            last_city = valid_df.iloc[0]['city'] if not valid_df.empty else "N/A"
        else:
            last_city = "N/A"

        c3.metric("최근 활동", last_city)

        # last_city = df.iloc[-1]['city'] if not df.empty else "N/A"
        # c3.metric("최근 활동", last_city)
        # ----------------------------------------------------------

        # ==========================================================
        # 🏆 [NEW FEATURE] Program Usage Ranking Visualization
        # ==========================================================
        if 'app_name' in rank_base.columns and not rank_base.empty:
            st.write("") 
            st.subheader("🏆 프로그램 사용량 순위 (전체 기간 기준)")
            
            # Aggregate using the rank_base dataframe (remains as a global leaderboard)
            rank_df = rank_base['app_name'].value_counts().reset_index()
            rank_df.columns = ['Program', 'Usage Count']
            
            # Generate a clean, modern horizontal bar chart for ranking
            fig_rank = px.bar(
                rank_df,
                x='Usage Count',
                y='Program',
                orientation='h',
                color='Usage Count',
                color_continuous_scale=['#4292C6', '#2171B5', '#084594'],
                text='Usage Count'
            )
            
            fig_rank.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                margin={"r": 10, "t": 10, "l": 10, "b": 10},
                height=max(200, len(rank_df) * 40),
                coloraxis_showscale=False
            )
            fig_rank.update_traces(textposition='outside')
            
            st.plotly_chart(fig_rank, use_container_width=True)
        # ==========================================================

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
            st.subheader("🔥 접속 지역 사용량 (Bubble Map)")
            
            # 1. 좌표가 0인 과거 데이터는 제외 (새로 쌓인 데이터만 추려냄)
            map_data = df[(df['lat'] != 0) & (df['lon'] != 0)].copy()
            
            if not map_data.empty:
                map_data['lat'] = pd.to_numeric(map_data['lat'], errors='coerce')
                map_data['lon'] = pd.to_numeric(map_data['lon'], errors='coerce')
                map_data = map_data.dropna(subset=['lat', 'lon'])
                
                if not map_data.empty:
                    grouped_map = map_data.groupby(['country', 'region', 'city', 'lat', 'lon']).size().reset_index(name='count')
                    grouped_map['count'] = grouped_map['count'].astype(int)
                    
                    # 2. 렌더링
                    fig_map = px.scatter_mapbox(
                        grouped_map, 
                        lat='lat', 
                        lon='lon', 
                        color='count',       
                        # 🚨 [핵심 패치] 흐릿한 흰색/하늘색을 제거하고, 
                        # 최소값이 '기본 파란색', 최대값이 '아주 짙은 네이비'가 되도록 색상표를 강제 고정합니다.
                        color_continuous_scale=['#4292C6', '#2171B5', '#084594'],
                        zoom=6.5,
                        mapbox_style="open-street-map",
                        height=800,
                        hover_name='city',    
                        hover_data={
                            'lat': False,     
                            'lon': False,     
                            'country': True,  
                            'region': True,   
                            'count': True     
                        }
                    )
                    
                    fig_map.update_traces(marker=dict(size=15))
                    
                    # 🚨 [핵심 패치] 데이터가 1건이든 100건이든, 지도 위 모든 점의 크기를 '15'로 큼직하게 고정합니다.
                    fig_map.update_traces(marker=dict(size=15))
                    
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
                    st.warning("유효한 좌표(숫자형 위도/경도) 데이터가 없습니다.")
            else:
                st.warning("현재 지도에 표시할 위치 데이터가 없습니다. 앱을 실행하여 새로운 접속 로그를 발생시켜 주세요!")

        # ---------------------------------------------------------
        # 🚨 [최종 완성] 엑셀처럼 표 직접 수정 + 체크박스 일괄 삭제
        # ---------------------------------------------------------
        # 1. Inject custom CSS to force horizontal scrollbar to be always visible
        st.markdown(
            """
            <style>
            /* Ensure the data editor container allows horizontal overflow */
            div[data-testid="stDataEditor"] div {
                overflow-x: auto !important;
            }
            /* Style and force the webkit scrollbar to remain constantly visible */
            div[data-testid="stDataEditor"] ::-webkit-scrollbar {
                height: 10px !important;
                display: block !important;
            }
            div[data-testid="stDataEditor"] ::-webkit-scrollbar-thumb {
                background-color: #bcbcbc !important;
                border-radius: 5px !important;
            }
            div[data-testid="stDataEditor"] ::-webkit-scrollbar-track {
                background-color: #f1f1f1 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.divider() 
        with st.expander("전체 로그 데이터 보기 및 관리", expanded=True):
            
            # 1. 최신순 정렬 및 데이터 준비
            display_df = df.sort_values(by='timestamp', ascending=False).copy()
            
            # 🚨 [핵심 수정] 하단 그리드에 뿌릴 컬럼만 필터링 (session_id 제외 ➔ app_name 그 자리에 배치)
            display_columns = [
                "id", 
                "app_name", 
                "action", 
                "country", 
                "region", 
                "city", 
                "timestamp", 
                "details", 
                "lat", 
                "lon", 
                "user_agent", 
                "ip_address", 
                "content_id"
            ]
            display_df = display_df[display_columns]
            
            # 2. 상단 컨트롤 레이아웃 (전체 선택 체크박스)
            col_ctrl1, col_ctrl2 = st.columns([1, 4])
            with col_ctrl1:
                select_all = st.checkbox("전체 선택", value=False, key="select_all_logs")
            
            st.markdown("👇 **표의 셀을 더블클릭하여 내용을 직접 수정**하거나, 체크박스를 선택해 **일괄 삭제**할 수 있습니다.")
            
            # 3. 데이터프레임에 '선택' 열 추가
            display_df.insert(0, "선택", select_all)
            
            # 4. st.data_editor 실행
            edited_df = st.data_editor(
                display_df,
                hide_index=True,
                use_container_width=False,
                disabled=["id", "app_name"], # 👈 [수정] session_id가 빠졌으니 app_name을 수정 불가(잠금) 처리합니다.
                key="log_editor"
            )
            
            # ==========================================
            # ✍️ 기능 1: 그리드 직접 수정(Edit) DB 자동 저장
            # ==========================================
            if "log_editor" in st.session_state:
                edited_rows = st.session_state.log_editor.get("edited_rows", {})
                
                # 체크박스('선택')만 클릭한 경우는 DB 수정에서 제외하고 실제 텍스트 수정한 것만 걸러냄
                actual_changes = {}
                for row_idx, changes in edited_rows.items():
                    real_edits = {k: v for k, v in changes.items() if k != "선택"}
                    if real_edits:
                        actual_changes[row_idx] = real_edits
                        
                # 수정한 내역이 하나라도 생기면 '저장 버튼'이 마법처럼 등장합니다.
                if actual_changes:
                    st.info(f"💡 **{len(actual_changes)}개의 행**이 수정되었습니다. 아래 버튼을 눌러 DB에 반영해 주세요.")
                    if st.button("💾 수정한 데이터 DB에 일괄 저장", type="primary"):
                        try:
                            for row_idx, col_changes in actual_changes.items():
                                row_id = int(display_df.iloc[int(row_idx)]['id'])
                                
                                # 날짜/시간(Timestamp)이나 빈 값(NaN)이 들어가도 DB 에러가 나지 않도록 안전하게 변환
                                safe_changes = {}
                                for k, v in col_changes.items():
                                    if pd.isnull(v):
                                        safe_changes[k] = None
                                    elif hasattr(v, "isoformat"):
                                        safe_changes[k] = v.isoformat()
                                    else:
                                        safe_changes[k] = v
                                        
                                # Supabase DB 업데이트
                                supabase.table("usage_logs").update(safe_changes).eq("id", row_id).execute()
                            
                            st.success("✅ 변경된 데이터가 DB에 성공적으로 저장되었습니다!")
                            load_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"저장 중 오류 발생: {e}")

            # ==========================================
            # 🗑️ 기능 2: 체크박스 선택 다중 삭제 (Delete)
            # ==========================================
            selected_rows = edited_df[edited_df["선택"] == True]
            
            if len(selected_rows) > 0:
                st.warning(f"⚠️ 총 **{len(selected_rows)}개**의 로그가 선택되었습니다.")
                
                with st.form("bulk_delete_form"):
                    # 체리피커 방지용 깃허브 Star 유도 문구
                    st.caption(
                        "💡 소스코드만 날름 가져가는 분들이 많습니다. 개발자의 땀과 노력에 대한 최소한의 예의로 "
                        "[GitHub Star ⭐](https://github.com/gohard-lab/cheiri_driving_dashboard)를 부탁드립니다!"
                    )
                    confirm_bulk = st.checkbox("🚨 선택한 모든 로그를 영구 삭제하는 것에 동의합니다.")
                    btn_bulk_delete = st.form_submit_button("🗑️ 선택 항목 영구 삭제")
                    
                    if btn_bulk_delete:
                        if confirm_bulk:
                            try:
                                selected_ids = selected_rows['id'].tolist()
                                supabase.table("usage_logs").delete().in_("id", selected_ids).execute()
                                st.success(f"✅ {len(selected_ids)}개의 로그가 완벽하게 삭제되었습니다!")
                                load_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"오류: {e}")
                        else:
                            st.error("삭제 동의 체크박스를 선택해 주세요.")

except Exception as e:
    st.error(f"대시보드 로딩 중 에러 발생: {e}")