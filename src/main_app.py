import streamlit as st
import tracker  # 만들어둔 추적 모듈 불러오기

st.title("🚀 데이터베이스 추적 연동 테스트")

# 앱이 처음 열렸을 때 '방문' 기록 1회 남기기
if 'visited' not in st.session_state:
    tracker.log_app_usage("유튜브_분석기", "app_opened")
    st.session_state['visited'] = True

st.write("아래 버튼을 누르고 VS Code의 SQLTools에서 실시간으로 데이터가 쌓이는지 확인해 보세요.")

# 특정 기능 동작 시 추적하기
if st.button("핵심 기능 실행"):
    # 버튼이 눌렸을 때 action 이름을 지정하여 로그 전송
    tracker.log_app_usage("유튜브_분석기", "core_feature_clicked")
    st.success("기능이 실행되었습니다! DB를 확인해 보세요.")

st.markdown("---")
# 법적 방어 및 투명성을 위한 최소한의 안내 문구
st.caption("본 프로그램은 더 나은 서비스 제공과 에러 수정을 위해 익명화된 최소한의 사용 통계(기능 클릭 수 등)를 수집합니다.")