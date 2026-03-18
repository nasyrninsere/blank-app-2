"""
AirKorea 대기질 분석 대시보드 - 단일 파일 버전
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# =====================================================================
# 1. 페이지 및 공통 설정
# =====================================================================
st.set_page_config(
    page_title="AirKorea 대기질 분석 대시보드",
    page_icon="🌬️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 대기질 기준 색상 및 등급 정의 (CAI 한국 기준 근사치)
# PM10: 0-30 좋음, 31-80 보통, 81-150 나쁨, 151+ 매우나쁨
# PM2.5: 0-15 좋음, 16-35 보통, 36-75 나쁨, 76+ 매우나쁨
AQI_COLORS = {
    "좋음": "#00E676",  # Green
    "보통": "#FFD54F",  # Yellow
    "나쁨": "#FF9100",  # Orange
    "매우나쁨": "#FF1744" # Red
}

def get_aqi_grade_and_color(pollutant, value):
    if pd.isna(value): return "데이터 없음", "#888888"
    if pollutant == "PM10":
        if value <= 30: return "좋음", AQI_COLORS["좋음"]
        elif value <= 80: return "보통", AQI_COLORS["보통"]
        elif value <= 150: return "나쁨", AQI_COLORS["나쁨"]
        else: return "매우나쁨", AQI_COLORS["매우나쁨"]
    elif pollutant == "PM25":
        if value <= 15: return "좋음", AQI_COLORS["좋음"]
        elif value <= 35: return "보통", AQI_COLORS["보통"]
        elif value <= 75: return "나쁨", AQI_COLORS["나쁨"]
        else: return "매우나쁨", AQI_COLORS["매우나쁨"]
    elif pollutant == "O3":
        if value <= 0.03: return "좋음", AQI_COLORS["좋음"]
        elif value <= 0.09: return "보통", AQI_COLORS["보통"]
        elif value <= 0.15: return "나쁨", AQI_COLORS["나쁨"]
        else: return "매우나쁨", AQI_COLORS["매우나쁨"]
    # 기본값
    return "기타", "#0077B6"

st.markdown("""
<style>
/* 카드 스타일 */
[data-testid="stMetric"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    border-left: 5px solid #0077B6;
}
</style>
""", unsafe_allow_html=True)


# =====================================================================
# 2. 데이터 로더 모듈
# =====================================================================
@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    import os
    # 스크립트 파일 위치 기준 절대경로 생성
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "202501-air.csv")
            
    df = pd.read_csv(csv_path)
    
    # 정적 시간 변환
    df['측정일시'] = pd.to_datetime(df['측정일시'].astype(str), format='%Y%m%d%H', errors='coerce')
    df['주차'] = df['측정일시'].dt.to_period('W').dt.start_time
    
    # 지역 분기
    df['시도'] = df['지역'].apply(lambda x: str(x).split()[0] if pd.notnull(x) else '기타')
    df['시군구'] = df['지역'].apply(lambda x: str(x).split()[1] if pd.notnull(x) and len(str(x).split())>1 else '전체')
    
    # 숫자형 변환
    pollutants = ['SO2', 'CO', 'O3', 'NO2', 'PM10', 'PM25']
    for col in pollutants:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

# =====================================================================
# 3. 차트 컴포넌트
# =====================================================================
def chart_gauge_custom(value, ref_val, title_text, max_val=150):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=value,
        delta={'reference': ref_val, 'relative': False, 'valueformat': '.1f'},
        title={'text': title_text, 'font': {'size': 18}},
        gauge={
            'axis': {'range': [None, max_val]},
            'bar': {'color': "#0077B6"},
            'steps': [
                {'range': [0, max_val*0.2], 'color': AQI_COLORS["좋음"]},
                {'range': [max_val*0.2, max_val*0.5], 'color': AQI_COLORS["보통"]},
                {'range': [max_val*0.5, max_val*0.8], 'color': AQI_COLORS["나쁨"]},
                {'range': [max_val*0.8, max_val], 'color': AQI_COLORS["매우나쁨"]}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': value}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30), paper_bgcolor="#ffffff")
    return fig


# =====================================================================
# 4. 페이지 렌더링 함수
# =====================================================================

def render_home(filtered_df, pollutant_focus):
    st.title("🏠 대기질 통합 개요")
    st.divider()

    # KPI 집계
    avg_val = filtered_df[pollutant_focus].mean()
    max_val = filtered_df[pollutant_focus].max()
    max_station = filtered_df.loc[filtered_df[pollutant_focus].idxmax(), '측정소명'] if not filtered_df.dropna(subset=[pollutant_focus]).empty else "N/A"

    grade, color = get_aqi_grade_and_color(pollutant_focus, avg_val)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
         st.metric(f"평균 {pollutant_focus} 농도", f"{avg_val:.2f} ㎍/㎥" if pollutant_focus.startswith("PM") else f"{avg_val:.4f} ppm")
    with c2:
         st.metric(f"최고 {pollutant_focus} 농도", f"{max_val:.1f}")
    with c3:
         st.metric("최고 측정소", max_station)
    with c4:
         st.markdown(f"""
         <div style='background:{color}; color:white; padding:10px 20px; border-radius:10px; font-weight:bold; text-align:center; margin-top:15px;'>
         통합 등급: {grade}
         </div>
         """, unsafe_allow_html=True)
    
    st.divider()

    # 1. 게이지 차트
    c_gauge, c_line = st.columns([1, 2])
    with c_gauge:
         st.subheader("🎯 위험도 게이지")
         max_limit = 150 if pollutant_focus.startswith("PM") else 0.15
         st.plotly_chart(chart_gauge_custom(avg_val if not pd.isna(avg_val) else 0, avg_val*0.8, pollutant_focus, max_val=max_limit), use_container_width=True)

    with c_line:
         st.subheader("📈 일별/시간별 오염물질 추이")
         day_avg = filtered_df.groupby('측정일시')[pollutant_focus].mean().reset_index()
         fig_line = px.line(day_avg, x='측정일시', y=pollutant_focus, title=f"{pollutant_focus} 평균 변화")
         fig_line.update_layout(plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified")
         st.plotly_chart(fig_line, use_container_width=True)


def render_comparison(filtered_df, pollutant_focus):
    st.title("📊 지역별 비교 분석")
    st.divider()

    # 구별 평균 비교
    st.subheader("시군구별 오염물질 농도 비교")
    dist_avg = filtered_df.groupby('시군구')[pollutant_focus].mean().sort_values(ascending=False).reset_index()
    
    fig_bar = px.bar(dist_avg, x='시군구', y=pollutant_focus, color=pollutant_focus, 
                     color_continuous_scale="Reds", text_auto='.1f')
    fig_bar.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
         st.subheader("측정망별 비교")
         nt_avg = filtered_df.groupby('망')[pollutant_focus].mean().reset_index()
         fig_pie = px.pie(nt_avg, values=pollutant_focus, names='망', hole=0.4, title=f"측정망별 {pollutant_focus} 농도 합산비율")
         st.plotly_chart(fig_pie, use_container_width=True)
         
    with c2:
         st.subheader("측정소별 계층 구조")
         # 지점 -> 측정소 선버스트
         sun_df = filtered_df.groupby(['시도', '시군구', '측정소명'])[pollutant_focus].mean().fillna(0).reset_index()
         fig_sun = px.sunburst(sun_df, path=['시도', '시군구', '측정소명'], values=pollutant_focus, color=pollutant_focus, color_continuous_scale="Viridis")
         st.plotly_chart(fig_sun, use_container_width=True)


def render_analysis(filtered_df):
    st.title("📈 상관관계 및 히트맵 분석")
    st.divider()

    # SettingWithCopyWarning 방지
    _df = filtered_df.copy()

    c1, c2 = st.columns(2)
    with c1:
         st.subheader("PM10 vs PM2.5 상관관계")
         fig_scatter = px.scatter(_df.dropna(subset=['PM10', 'PM25']), x='PM10', y='PM25', 
                                  color='시군구', hover_name='측정소명', trendline="ols")
         fig_scatter.update_layout(plot_bgcolor="white")
         st.plotly_chart(fig_scatter, use_container_width=True)

    with c2:
         st.subheader("시간대별 패턴 분석")
         _df['시간'] = _df['측정일시'].dt.hour
         _df['일'] = _df['측정일시'].dt.day
         
         # 피벗 테이블 생성
         pivot_df = _df.pivot_table(values='PM10', index='시간', columns='일', aggfunc='mean').fillna(0)
         
         fig_heat = px.imshow(pivot_df, labels=dict(x="일자", y="시간대 (H)", color="PM10 평균"),
                              x=pivot_df.columns, y=pivot_df.index, color_continuous_scale="YlOrRd")
         st.plotly_chart(fig_heat, use_container_width=True)


def render_data(filtered_df):
    st.title("📋 데이터 관리 및 조회")
    st.divider()

    st.subheader("현재 필터링된 데이터 조각")
    st.dataframe(filtered_df.head(1000), use_container_width=True)
    
    csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 전체 필터링 데이터 CSV 다운로드", data=csv, file_name="air_filtered_data.csv")


# =====================================================================
# 5. 메인 실행 & 라우팅 분기
# =====================================================================
df = load_data()

with st.sidebar:
    st.markdown("## ⚙️ 설정 가이드")
    page = st.radio("메뉴 이동", ["통합 개요", "지역별 비교", "분석 지표", "원시 데이터"])
    st.divider()

    # 시도 필터
    cities = sorted(df['시도'].unique().tolist())
    selected_city = st.selectbox("시도 선택", cities, index=cities.index('서울') if '서울' in cities else 0)

    # 시군구 필터 (선택된 시도에 종속)
    districts = sorted(df[df['시도'] == selected_city]['시군구'].unique().tolist())
    selected_district = st.multiselect("시군구 선택 (다중)", ["전체"] + districts, default=["전체"])

    # 날짜 범위 필터
    min_date = df['측정일시'].min().date()
    max_date = df['측정일시'].max().date()
    # Range select
    date_range = st.date_input("조회 기간", [min_date, max_date])

    st.divider()
    pollutant_focus = st.selectbox("주시 오염물질", ['PM10', 'PM25', 'O3', 'NO2', 'CO', 'SO2'])


# 필터링 로직 분기
mask = (df['시도'] == selected_city)
if "전체" not in selected_district and selected_district:
    mask &= df['시군구'].isin(selected_district)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    mask &= (df['측정일시'].dt.date >= date_range[0]) & (df['측정일시'].dt.date <= date_range[1])

filtered_df = df[mask]

# 선택된 페이지 렌더링
if page == "통합 개요":
    render_home(filtered_df, pollutant_focus)
elif page == "지역별 비교":
    render_comparison(filtered_df, pollutant_focus)
elif page == "분석 지표":
    render_analysis(filtered_df)
elif page == "원시 데이터":
    render_data(filtered_df)
