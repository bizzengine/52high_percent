from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_stock', methods=['GET'])
def search_stock():
    return jsonify([]) # 빈 리스트 반환하여 자동 완성 비활성화


@app.route('/analyze_stock', methods=['POST'])
def analyze_stock():
    stock_symbol = request.form['stock_symbol'].upper()

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=365 * 2)

    try:
        df = yf.download(stock_symbol, start=start_date, end=end_date, progress=False, auto_adjust=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel('Ticker')

        if df.empty:
            return render_template('index.html', error=f"'{stock_symbol}' 종목의 데이터를 찾을 수 없거나 데이터가 부족합니다. 심볼을 확인해주세요.")

        if len(df) >= 252:
            high_52_week = df['High'].tail(252).max()
        else:
            high_52_week = df['High'].max()
        
        current_price = df['Close'].iloc[-1]

        ticker = yf.Ticker(stock_symbol)
        stock_info = ticker.info
        stock_name = stock_info.get('longName', stock_symbol)
        
    except Exception as e:
        print(f"Error fetching data for {stock_symbol}: {e}")
        return render_template('index.html', error=f"데이터를 가져오는 중 오류가 발생했습니다: {e}. 정확한 종목 심볼을 입력했는지 확인해주세요.")

    # 현재가 대비 52주 전고점 하락률 계산 (소수점 포함)
    actual_percent_drop = (1 - current_price / high_52_week) * 100

    # 테이블에 표시할 기준 하락률 값들을 생성
    standard_price_levels = []
    # 0% 전고점 라인 추가
    standard_price_levels.append({
        "percent_drop": 0,
        "target_price": high_52_week,
        "is_current": False # 현재가 라인이 아님을 표시
    })
    for percent_drop_val in range(5, 81, 5): # 5% 단위로 80%까지
        target_price = high_52_week * (1 - percent_drop_val / 100)
        standard_price_levels.append({
            "percent_drop": percent_drop_val,
            "target_price": round(target_price, 2),
            "is_current": False
        })
    
    # 현재가를 위한 데이터 생성
    current_price_data = {
        "percent_drop": actual_percent_drop,
        "target_price": current_price,
        "is_current": True # 현재가 라인임을 표시
    }

    # 현재가 데이터를 기존 price_levels 리스트에 삽입할 위치 찾기
    price_levels_to_display = []
    inserted = False
    
    # 현재가가 전고점보다 높거나 0% ~ -5% 사이에 있을 경우 0% 라인 바로 다음에 삽입
    if actual_percent_drop <= standard_price_levels[1]["percent_drop"]: # 0% ~ 5%
        price_levels_to_display.append(standard_price_levels[0]) # 0% 라인 추가
        price_levels_to_display.append(current_price_data) # 현재가 라인 추가
        inserted = True
        for i in range(1, len(standard_price_levels)): # 나머지 기준 레벨 추가
            price_levels_to_display.append(standard_price_levels[i])
    else: # 5%보다 더 많이 하락한 경우
        for i, level in enumerate(standard_price_levels):
            price_levels_to_display.append(level) # 기준 레벨 추가
            
            # 현재가가 다음 기준 레벨이 존재하고 그 사이에 삽입되어야 하는 경우
            if not inserted and i + 1 < len(standard_price_levels):
                if actual_percent_drop > level["percent_drop"] and \
                   actual_percent_drop < standard_price_levels[i+1]["percent_drop"]:
                    price_levels_to_display.append(current_price_data)
                    inserted = True
        
        # 만약 80%보다 더 많이 하락했는데 아직 삽입되지 않았다면 맨 마지막에 추가
        if not inserted and actual_percent_drop >= standard_price_levels[-1]["percent_drop"]:
            price_levels_to_display.append(current_price_data)
            
    # `current_price_status`는 이제 템플릿으로 보내지 않습니다.


    return render_template('index.html',
                           stock_name=stock_name,
                           stock_symbol=stock_symbol,
                           high_52_week=high_52_week,
                           current_price=current_price,
                           price_levels=price_levels_to_display) # 수정된 리스트 전달

if __name__ == '__main__':
    app.run(debug=True)