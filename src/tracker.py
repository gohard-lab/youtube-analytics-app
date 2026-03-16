import streamlit as st
import requests
import uuid
import os
from supabase import create_client, Client
from datetime import datetime

# 싱글톤 패턴을 활용하여 클라이언트 한 번만 생성
@st.cache_resource
def get_supabase_client() -> Client:
    # 1. Streamlit 클라우드 Secrets를 먼저 찾습니다.
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
    except KeyError:
        # 2. 클라우드에 없으면 로컬 환경 변수(.env)나 하드코딩된 값을 찾습니다.
        supabase_url = os.environ.get("SUPABASE_URL", "https://gkzbiacodysnrzbpvavm.supabase.co")
        supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdremJpYWNvZHlzbnJ6YnB2YXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM1NzE2MTgsImV4cCI6MjA4OTE0NzYxOH0.Lv5uVeNZOyo21tgyl2jjGcESoLl_iQTJYp4jdCwuYDU")
        
    return create_client(supabase_url, supabase_key)

supabase = get_supabase_client()

def get_location_data():
    """사용자의 IP를 기반으로 익명화된 위치 정보를 가져옵니다."""
    if 'location' not in st.session_state:
        try:
            response = requests.get('http://ip-api.com/json/', timeout=3).json()
            if response.get('status') == 'success':
                st.session_state['location'] = {
                    "country": response.get("country", "Unknown"),
                    "region": response.get("regionName", "Unknown"),
                    "city": response.get("city", "Unknown"),
                    "lat": response.get("lat", 0.0),
                    "lon": response.get("lon", 0.0)
                }
            else:
                st.session_state['location'] = {"country": "Unknown", "region": "Unknown", "city": "Unknown", "lat": 0.0, "lon": 0.0}
        except Exception:
            st.session_state['location'] = {"country": "Unknown", "region": "Unknown", "city": "Unknown", "lat": 0.0, "lon": 0.0}
    return st.session_state['location']

def log_app_usage(app_name: str, action_name: str):
    """
    앱의 사용량을 데이터베이스에 기록합니다.
    """
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = str(uuid.uuid4())
        
    location = get_location_data()
    
    data = {
        "app_name": app_name,
        "session_id": st.session_state['session_id'],
        "action": action_name,
        "country": location["country"],
        "region": location["region"],
        "city": location["city"],
        "lat": location["lat"],
        "lon": location["lon"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        supabase.table("usage_logs").insert(data).execute()
    except Exception as e:
        # 인터넷 연결 없음 등의 에러가 발생해도 본 프로그램(누끼따기)은 정상 작동해야 합니다.
        pass