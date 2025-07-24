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

    # end_date = datetime.today().date()
    start_date = datetime.today().date() - timedelta(days=365 * 2)

    try:
        df = yf.download(stock_symbol, start=start_date, progress=False, auto_adjust=False)

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
        return render_template('index.html', error=f"데이터를 가져오는 중 오류이 발생했습니다: {e}. 정확한 종목 심볼을 입력했는지 확인해주세요.")

    # 현재가 대비 52주 전고점 하락률 계산 (소수점 포함)
    actual_percent_drop = (1 - current_price / high_52_week) * 100

    # 1년 전고점 대비 최대 하락가 계산
    if len(df) >= 252:
        df_last_year = df.tail(252)
        high_1_year = df_last_year['High'].max()
        low_1_year = df_last_year['Close'].min() # 변경된 부분
        
        if high_1_year > 0:
            max_drop_1_year_val = (1 - low_1_year / high_1_year) * 100
            max_drop_1_year_price = high_1_year * (1 - max_drop_1_year_val / 100)
        else:
            max_drop_1_year_val = 0
            max_drop_1_year_price = high_1_year

    else:
        high_1_year = df['High'].max()
        low_1_year = df['Close'].min() # 변경된 부분
        if high_1_year > 0:
            max_drop_1_year_val = (1 - low_1_year / high_1_year) * 100
            max_drop_1_year_price = high_1_year * (1 - max_drop_1_year_val / 100)
        else:
            max_drop_1_year_val = 0
            max_drop_1_year_price = high_1_year

    # 테이블에 표시할 기준 하락률 값들을 생성
    standard_price_levels = []
    # 0% 전고점 라인 추가
    standard_price_levels.append({
        "percent_drop": 0,
        "target_price": high_52_week,
        "is_current": False
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
        "is_current": True
    }

    # 1년 전고점 대비 최대 하락률 데이터 생성
    max_drop_1_year_data = {
        "percent_drop": max_drop_1_year_val,
        "target_price": max_drop_1_year_price,
        "is_current": False,
        "is_max_drop_1_year": True # 1년 최대 하락률임을 식별하는 플래그
    }

    price_levels_to_display = []
    inserted_current = False
    inserted_max_drop = False

    # 0% 라인 추가
    price_levels_to_display.append(standard_price_levels[0])

    for i in range(1, len(standard_price_levels)):
        current_level = standard_price_levels[i]

        # 현재가 삽입 로직
        if not inserted_current and actual_percent_drop > standard_price_levels[i-1]["percent_drop"] and actual_percent_drop <= current_level["percent_drop"]:
            price_levels_to_display.append(current_price_data)
            inserted_current = True
        elif not inserted_current and i == 1 and actual_percent_drop <= standard_price_levels[0]["percent_drop"]: # 현재가가 0% 이하(전고점 이상)인 경우
            price_levels_to_display.insert(1, current_price_data) # 0% 라인 바로 뒤에 삽입
            inserted_current = True


        # 1년 전고점 대비 최대 하락률 삽입 로직
        if not inserted_max_drop and max_drop_1_year_data["percent_drop"] > standard_price_levels[i-1]["percent_drop"] and max_drop_1_year_data["percent_drop"] <= current_level["percent_drop"]:
            # 현재가와 1년 최대 하락률이 같은 구간에 있을 경우 삽입 순서 결정 (여기서는 1년 최대 하락률이 먼저)
            if current_price_data["percent_drop"] == max_drop_1_year_data["percent_drop"] and inserted_current:
                 # 현재가 다음에 삽입
                idx = price_levels_to_display.index(current_price_data)
                price_levels_to_display.insert(idx + 1, max_drop_1_year_data)
            else:
                price_levels_to_display.append(max_drop_1_year_data)
            inserted_max_drop = True

        price_levels_to_display.append(current_level)

    # 모든 기준 레벨을 다 추가한 후에도 현재가나 1년 최대 하락률이 삽입되지 않았다면 맨 마지막에 추가
    if not inserted_current:
        price_levels_to_display.append(current_price_data)
    if not inserted_max_drop:
        price_levels_to_display.append(max_drop_1_year_data)

    # percent_drop을 기준으로 오름차순 정렬하여 표시 순서를 제어
    price_levels_to_display.sort(key=lambda x: x['percent_drop'])


    return render_template('index.html',
                            stock_name=stock_name,
                            stock_symbol=stock_symbol,
                            high_52_week=high_52_week,
                            current_price=current_price,
                            price_levels=price_levels_to_display,
                           )

if __name__ == '__main__':
    app.run(debug=True)