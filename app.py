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
    return jsonify([])  # 자동 완성 비활성화

@app.route('/analyze_stock', methods=['POST'])
def analyze_stock():
    stock_symbol = request.form['stock_symbol'].upper()
    start_date = datetime.today().date() - timedelta(days=365 * 2)

    try:
        df = yf.download(stock_symbol, start=start_date, progress=False, auto_adjust=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel('Ticker')

        # 가장 최근 영업일 기준으로 필터링
        df = df[df['Close'].notna()]
        df = df.sort_index()
        current_price = df['Close'].iloc[-1]

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

    # 현재가 대비 52주 전고점 하락률 계산
    actual_percent_drop = (1 - current_price / high_52_week) * 100

    # (수정된 부분) 최근 52주 전고점 - 올해 최저 종가 기준 최대 하락률 계산
    try:
        this_year = datetime.today().year
        start_of_year = datetime(this_year, 1, 1)
        df_this_year = df[df.index >= pd.to_datetime(start_of_year)]

        if not df_this_year.empty:
            low_this_year = df_this_year['Close'].min()
            max_drop_1_year_val = (1 - low_this_year / high_52_week) * 100
            max_drop_1_year_price = high_52_week * (1 - max_drop_1_year_val / 100)
        else:
            max_drop_1_year_val = 0
            max_drop_1_year_price = high_52_week
    except:
        max_drop_1_year_val = 0
        max_drop_1_year_price = high_52_week

    # 테이블에 표시할 기준 하락률 값 생성
    standard_price_levels = [{
        "percent_drop": 0,
        "target_price": high_52_week,
        "is_current": False
    }]
    for percent_drop_val in range(5, 81, 5):
        target_price = high_52_week * (1 - percent_drop_val / 100)
        standard_price_levels.append({
            "percent_drop": percent_drop_val,
            "target_price": round(target_price, 2),
            "is_current": False
        })

    current_price_data = {
        "percent_drop": actual_percent_drop,
        "target_price": current_price,
        "is_current": True
    }

    max_drop_1_year_data = {
        "percent_drop": max_drop_1_year_val,
        "target_price": max_drop_1_year_price,
        "is_current": False,
        "is_max_drop_1_year": True
    }

    price_levels_to_display = []
    inserted_current = False
    inserted_max_drop = False

    # 0% 라인 먼저 추가
    price_levels_to_display.append(standard_price_levels[0])

    for i in range(1, len(standard_price_levels)):
        current_level = standard_price_levels[i]

        # 현재가 삽입
        if not inserted_current and actual_percent_drop > standard_price_levels[i-1]["percent_drop"] and actual_percent_drop <= current_level["percent_drop"]:
            price_levels_to_display.append(current_price_data)
            inserted_current = True
        elif not inserted_current and i == 1 and actual_percent_drop <= standard_price_levels[0]["percent_drop"]:
            price_levels_to_display.insert(1, current_price_data)
            inserted_current = True

        # 최대 하락 삽입
        if not inserted_max_drop and max_drop_1_year_data["percent_drop"] > standard_price_levels[i-1]["percent_drop"] and max_drop_1_year_data["percent_drop"] <= current_level["percent_drop"]:
            if current_price_data["percent_drop"] == max_drop_1_year_data["percent_drop"] and inserted_current:
                idx = price_levels_to_display.index(current_price_data)
                price_levels_to_display.insert(idx + 1, max_drop_1_year_data)
            else:
                price_levels_to_display.append(max_drop_1_year_data)
            inserted_max_drop = True

        price_levels_to_display.append(current_level)

    if not inserted_current:
        price_levels_to_display.append(current_price_data)
    if not inserted_max_drop:
        price_levels_to_display.append(max_drop_1_year_data)

    price_levels_to_display.sort(key=lambda x: x['percent_drop'])

    return render_template('index.html',
                           stock_name=stock_name,
                           stock_symbol=stock_symbol,
                           high_52_week=high_52_week,
                           current_price=current_price,
                           price_levels=price_levels_to_display)

if __name__ == '__main__':
    app.run(debug=True)
