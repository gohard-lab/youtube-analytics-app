# 📊 잡학다식 개발자: 파이썬 & Streamlit 트래픽 분석 대시보드

이 프로젝트는 유튜브 '잡학다식 개발자' 채널의 콘텐츠용으로 제작된 파이썬 기반의 실시간 사용량 추적 및 시각화 대시보드입니다. 
웹(Streamlit Cloud) 배포 및 데스크톱(.exe) 실행 환경을 모두 지원하며, Supabase를 활용하여 데이터를 수집하고 분석합니다.

## 🚀 주요 기능 (Features)
* **실시간 트래픽 추적:** 사용자의 앱 실행 및 버튼 클릭 등 이벤트 로그 수집
* **IP 기반 위치 시각화:** Plotly와 Mapbox(`carto-positron` 스타일)를 활용한 접속 지역 히트맵 제공
* **동적 데이터 필터링:** 전체 기간, 오늘, 최근 7일 등 기간별 데이터 및 개별 프로그램(앱)별 통계 확인
* **유연한 배포 환경:** `pyproject.toml`을 통한 모던 패키지 관리 및 클라우드/로컬 환경 대응

## 🛠 기술 스택 (Tech Stack)
* **Language:** Python 3.10+
* **Frontend/Dashboard:** Streamlit, Plotly
* **Database:** Supabase (PostgreSQL)
* **Dependency Management:** pyproject.toml

## ⚙️ 설치 및 실행 방법 (How to Run)

### 1. 로컬 환경 설정
저장소를 클론한 후, 프로젝트 최상단 폴더에서 필요한 패키지를 설치합니다.

```bash
pip install .