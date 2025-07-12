import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import feedparser
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Basic settings ---
st.set_page_config(layout="wide")
st.title("🇺🇸 미국 주식 통합 분석 플랫폼")

# --- Initialize session state for the current ticker ---
if 'current_ticker' not in st.session_state:
    st.session_state['current_ticker'] = "AAPL" # Default initial ticker
if 'show_stock_info' not in st.session_state: # New state for button click
    st.session_state['show_stock_info'] = False

# --- Custom ticker input ---
selected_ticker = st.text_input("종목 코드를 입력하세요 (예: AAPL)", value=st.session_state['current_ticker']).upper()
if selected_ticker and selected_ticker != st.session_state['current_ticker']:
    st.session_state['current_ticker'] = selected_ticker
    st.session_state['show_stock_info'] = False # Reset info display on ticker change
    st.rerun()

# --- Main Stock Analysis Section ---
ticker_to_analyze = st.session_state['current_ticker']

st.header(f"📈 {ticker_to_analyze} 주식 분석")

# Fetch data with period
@st.cache_data
def get_stock_data(ticker_symbol, period="1y"):
    ticker = yf.Ticker(ticker_symbol)
    data = ticker.history(period=period)
    info = ticker.info
    recommendations = ticker.recommendations
    return data, info, recommendations

# 기간 선택 옵션
time_periods = {
    "1일": "1d", "5일": "5d", "1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y", "5년": "5y", "최대": "max"
}
selected_period_label = st.selectbox("기간 선택", options=list(time_periods.keys()), index=5) # 기본 1년 선택
selected_period = time_periods.get(selected_period_label, "1y")

data, info, recommendations = get_stock_data(ticker_to_analyze, selected_period)

if data.empty:
    st.error(f"'{ticker_to_analyze}' 종목의 데이터를 불러올 수 없습니다. 정확한 종목 코드인지 확인해주세요.")
else:
    # Display basic info
    st.subheader(f"{info.get('longName', ticker_to_analyze)} ({ticker_to_analyze})")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("현재가", f"${data['Close'].iloc[-1]:,.2f}")
    with col2:
        st.metric("거래량", f"{data['Volume'].iloc[-1]:,}")
    with col3:
        st.metric("시가총액", f"${info.get('marketCap', 0):,}" if info.get('marketCap') else "N/A")
    with col4:
        st.metric("52주 최고가", f"${info.get('fiftyTwoWeekHigh', 0):,.2f}" if info.get('fiftyTwoWeekHigh') else "N/A")

    # --- New Stock Info Section ---
    if st.button("종목정보↓"):
        st.session_state['show_stock_info'] = not st.session_state['show_stock_info'] # Toggle button state

    if st.session_state['show_stock_info']:
        st.subheader(f"✨ {ticker_to_analyze} 종목 상세 정보")

        st.markdown("##### 📝 종목 소개")
        long_business_summary = info.get('longBusinessSummary', '종목 소개 정보를 찾을 수 없습니다.')
        st.write(long_business_summary)

        st.markdown("##### 📍 섹터")
        sector = info.get('sector', '섹터 정보를 찾을 수 없습니다.')
        st.write(sector)

    # Interactive Candlestick and Volume Chart (Plotly Subplots)
    st.subheader("주가 및 거래량 추이")
    
    # 이동 평균선 계산
    data['SMA_20'] = data['Close'].rolling(window=20).mean()
    data['SMA_50'] = data['Close'].rolling(window=50).mean()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3]
    )

    # 캔들스틱 차트 추가
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='주가',
        increasing_line_color='red', # 양봉 색상
        decreasing_line_color='blue', # 음봉 색상
        hovertext=[f"날짜: {idx.strftime('%Y-%m-%d')}<br>시가: {o:.2f}<br>고가: {h:.2f}<br>저가: {l:.2f}<br>종가: {c:.2f}"
                   for idx, o, h, l, c in zip(data.index, data['Open'], data['High'], data['Low'], data['Close'])]
    ), row=1, col=1)

    # 20일 이동 평균선 추가
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['SMA_20'],
        mode='lines',
        name='SMA 20',
        line=dict(color='orange', width=1.5)
    ), row=1, col=1)

    # 50일 이동 평균선 추가
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['SMA_50'],
        mode='lines',
        name='SMA 50',
        line=dict(color='purple', width=1.5)
    ), row=1, col=1)

    # 거래량 차트 추가
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Volume'],
        name='거래량',
        marker_color='lightgray', # 거래량 바 색상
        hovertext=[f"날짜: {idx.strftime('%Y-%m-%d')}<br>거래량: {v:,}"
                   for idx, v in zip(data.index, data['Volume'])]
    ), row=2, col=1)

    fig.update_layout(
        title=f'{ticker_to_analyze} 주가 및 거래량 차트',
        height=500, # 모바일 가독성을 위한 높이 유지
        hovermode="x unified", # 마우스 오버 시 정보 통일
        xaxis_rangeslider_visible=False, # 상단 차트에서는 레인지 슬라이더 숨기기 (하단에만 표시)
        legend=dict( # 범례 위치 설정
            orientation="h", # 수평으로 배치
            yanchor="bottom",
            y=1.02, # 차트 상단 위쪽에 배치
            xanchor="right",
            x=1
        )
    )

    fig.update_xaxes(
        title_text="날짜",
        rangeslider_visible=False, # 상단 차트에서는 rangeslider 숨김
        row=1, col=1
    )
    fig.update_xaxes(
        title_text="날짜",
        rangeslider_visible=True, # 하단 차트(거래량)에 rangeslider 표시
        row=2, col=1
    )
    
    fig.update_yaxes(title_text="주가", row=1, col=1)
    fig.update_yaxes(title_text="거래량", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True) # 컨테이너 너비에 맞게 조절

    # Enhanced Financials
    st.subheader("📊 재무 핵심 지표")
    st.write("*(최신 보고서 기준)*") # Indicate data freshness

    # 1. 기업 가치 지표
    st.markdown("##### 1. 기업 가치 지표")
    col_val1, col_val2, col_val3, col_val4 = st.columns(4)
    with col_val1:
        st.metric("PER (Trailing)", f"{info.get('trailingPE', 'N/A'):.2f}" if isinstance(info.get('trailingPE'), (int, float)) else "N/A")
    with col_val2:
        st.metric("PER (Forward)", f"{info.get('forwardPE', 'N/A'):.2f}" if isinstance(info.get('forwardPE'), (int, float)) else "N/A")
    with col_val3:
        st.metric("PSR", f"{info.get('priceToSalesTrailing12Months', 'N/A'):.2f}" if isinstance(info.get('priceToSalesTrailing12Months'), (int, float)) else "N/A")
    with col_val4:
        if 'bookValue' in info and data['Close'].iloc[-1] > 0 and isinstance(info.get('bookValue'), (int, float)):
            pbr = data['Close'].iloc[-1] / info['bookValue']
            st.metric("PBR", f"{pbr:.2f}")
        else:
            st.metric("PBR", "N/A")
    
    col_val5, col_val6 = st.columns(2)
    with col_val5:
        st.metric("PEG Ratio", f"{info.get('pegRatio', 'N/A'):.2f}" if isinstance(info.get('pegRatio'), (int, float)) else "N/A")
    with col_val6:
        st.metric("EV/EBITDA", f"{info.get('enterpriseToEbitda', 'N/A'):.2f}" if isinstance(info.get('enterpriseToEbitda'), (int, float)) else "N/A")

    # 2. 수익성 지표
    st.markdown("##### 2. 수익성 지표")
    col_prof1, col_prof2, col_prof3 = st.columns(3)
    with col_prof1:
        st.metric("ROE", f"{info.get('returnOnEquity', 'N/A') * 100:.2f}%" if isinstance(info.get('returnOnEquity'), (int, float)) else "N/A")
    with col_prof2:
        st.metric("ROA", f"{info.get('returnOnAssets', 'N/A') * 100:.2f}%" if isinstance(info.get('returnOnAssets'), (int, float)) else "N/A")
    with col_prof3:
        st.metric("총이익률", f"{info.get('grossMargins', 'N/A') * 100:.2f}%" if isinstance(info.get('grossMargins'), (int, float)) else "N/A")

    col_prof4, col_prof5 = st.columns(2)
    with col_prof4:
        st.metric("영업이익률", f"{info.get('operatingMargins', 'N/A') * 100:.2f}%" if isinstance(info.get('operatingMargins'), (int, float)) else "N/A")
    with col_prof5:
        st.metric("순이익률", f"{info.get('profitMargins', 'N/A') * 100:.2f}%" if isinstance(info.get('profitMargins'), (int, float)) else "N/A")

    # 3. 부채 및 재무 건전성 지표
    st.markdown("##### 3. 부채 및 재무 건전성 지표")
    st.metric("부채비율", f"{info.get('debtToEquity', 'N/A'):.2f}" if isinstance(info.get('debtToEquity'), (int, float)) else "N/A")

    # 4. 배당 정보 (기존 유지)
    st.markdown("##### 4. 배당 정보")
    st.metric("배당 수익률", f"{info.get('dividendYield', 'N/A') * 100:.2f}%" if isinstance(info.get('dividendYield'), (int, float)) else "N/A")


    # Analyst Recommendations
    st.subheader("애널리스트 추천")
    if recommendations is not None and not recommendations.empty:
        st.dataframe(recommendations.tail(5)) # Show last 5 recommendations

    # Try to get target price from info or other attributes if analyst_price_target is gone
    target_mean_price = info.get('targetMeanPrice')
    target_high_price = info.get('targetHighPrice')
    target_low_price = info.get('targetLowPrice')

    if target_mean_price is not None or target_high_price is not None or target_low_price is not None:
        st.write("##### 애널리스트 목표주가:")
        st.write(f"- 평균 목표주가: ${target_mean_price:,.2f}" if target_mean_price is not None else "N/A")
        st.write(f"- 최고 목표주가: ${target_high_price:,.2f}" if target_high_price is not None else "N/A")
        st.write(f"- 최저 목표주가: ${target_low_price:,.2f}" if target_low_price is not None else "N/A")

        if not data.empty and target_mean_price is not None and data['Close'].iloc[-1] > 0:
            current_price = data['Close'].iloc[-1]
            potential_upside = ((target_mean_price - current_price) / current_price) * 100
            st.metric(label="평균 목표주가 대비 상승 여력", value=f"{potential_upside:.2f}%")
        else:
            st.info("현재 주가 또는 목표 주가 데이터가 유효하지 않아 상승 여력을 계산할 수 없습니다.")

    # News (simple example using feedparser for RSS/Atom feeds)
    st.subheader("📰 최신 뉴스")
    news_url = f"https://finance.yahoo.com/rss/headline?s={ticker_to_analyze}"
    try:
        feed = feedparser.parse(news_url)
        if feed.entries:
            for entry in feed.entries[:10]: # Display top 10 news articles
                st.markdown(f"**[{entry.title}]({entry.link})**")
                st.markdown(f"<small style='color: gray;'>_{entry.published}_</small>", unsafe_allow_html=True)
                st.write(entry.summary)
        else:
            st.info(f"'{ticker_to_analyze}' 관련 뉴스를 찾을 수 없습니다.")
    except Exception as e:
        st.error(f"뉴스를 불러오는 중 오류가 발생했습니다: {e}")
