import requests
import time
import hmac
import hashlib
import logging
import os
from binance.client import Client
from datetime import datetime

# ------------------- Cấu hình -------------------
API_KEY = 'dEDjg6ZLoFXWZy7KMjsRYGGczadZd8AI0WWQUHcGesKoUjYtOw9KC4gqnRbOYafk'
API_SECRET = '9w4NQ25fG0rHUQgqjNPJTfjukpL5tAbzjoqwlbvbVrRBZiilGXjk8zjxrPFPe8Gf'
SYMBOL = 'BTCUSDT'  # Cặp coin giao dịch
TIMEFRAME = '1m'  # Khung thời gian nến
NUM_CANDLES = 35  # Số nến lấy để tính giá trung bình
ORDER_AMOUNT_USD = 20  # Mỗi lần mua 20 USDT
BUY_THRESHOLD = 0.97  # Giá thấp hơn 2% sẽ mua
SELL_THRESHOLD = 1.03  # Giá cao hơn 2% sẽ bán
STOP_LOSS_THRESHOLD = 0.95  # Cắt lỗ nếu giảm 5%
TAKE_PROFIT_THRESHOLD = 1.05  # Chốt lời nếu tăng 5%
CHECK_INTERVAL = 15  # Kiểm tra mỗi 30 giây

# ========== KẾT NỐI API ==========
client = Client(API_KEY, API_SECRET)

# ========== GHI LOG ==========
log_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'crypto_bot_log.txt')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', handlers=[
    logging.FileHandler(log_path, encoding='utf-8'),
    logging.StreamHandler()
])

# ========== HÀM LẤY GIÁ HIỆN TẠI ==========
def get_current_price(symbol):
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        logging.error(f'Lỗi khi lấy giá hiện tại: {e}')
        return None

# ========== HÀM LẤY GIÁ TRUNG BÌNH ==========
def get_mean_price(symbol, interval, limit):
    try:
        candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        close_prices = [float(candle[4]) for candle in candles]
        return sum(close_prices) / len(close_prices)
    except Exception as e:
        logging.error(f'Lỗi khi lấy dữ liệu nến: {e}')
        return None

# ========== HÀM TÍNH SỐ LƯỢNG COIN ==========
def calculate_quantity(order_amount_usd, current_price):
    quantity = round(order_amount_usd / current_price, 6)  # Làm tròn theo chuẩn Binance
    return quantity

# ========== HÀM GIAO DỊCH ==========
def place_order(symbol, side, quantity):
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        logging.info(f'Đã {side} {quantity} {symbol[:-4]} thành công!')
        return order
    except Exception as e:
        logging.error(f'Lỗi khi đặt lệnh {side}: {e}')
        return None

# ========== BOT GIAO DỊCH CHÍNH ==========
def trading_bot():
    bought_price = None
    while True:
        current_price = get_current_price(SYMBOL)
        mean_price = get_mean_price(SYMBOL, TIMEFRAME, NUM_CANDLES)

        if current_price and mean_price:
            logging.info(f'Giá trung bình {NUM_CANDLES} nến: {mean_price:.2f}, Giá hiện tại: {current_price:.2f}')

            if not bought_price:
                if current_price < mean_price * BUY_THRESHOLD:
                    quantity = calculate_quantity(ORDER_AMOUNT_USD, current_price)
                    result = place_order(SYMBOL, 'BUY', quantity)
                    if result:
                        bought_price = current_price
                        logging.info(f'Đã mua ở giá: {bought_price:.2f}')
                else:
                    logging.info('Chưa có tín hiệu Mua.')
            else:
                if current_price > bought_price * TAKE_PROFIT_THRESHOLD:
                    quantity = calculate_quantity(ORDER_AMOUNT_USD, current_price)
                    place_order(SYMBOL, 'SELL', quantity)
                    logging.info(f'Chốt lời ở giá: {current_price:.2f}')
                    bought_price = None
                elif current_price < bought_price * STOP_LOSS_THRESHOLD:
                    quantity = calculate_quantity(ORDER_AMOUNT_USD, current_price)
                    place_order(SYMBOL, 'SELL', quantity)
                    logging.info(f'Cắt lỗ ở giá: {current_price:.2f}')
                    bought_price = None
                elif current_price > mean_price * SELL_THRESHOLD:
                    quantity = calculate_quantity(ORDER_AMOUNT_USD, current_price)
                    place_order(SYMBOL, 'SELL', quantity)
                    logging.info(f'Bán theo Mean Reversion ở giá: {current_price:.2f}')
                    bought_price = None
                else:
                    logging.info('Chưa có tín hiệu Bán.')
        else:
            logging.warning('Không lấy được dữ liệu giá.')

        time.sleep(CHECK_INTERVAL)

# ========== CHẠY BOT ==========
if __name__ == '__main__':
    logging.info('Khởi động Bot Mean Reversion Binance!')
    trading_bot()