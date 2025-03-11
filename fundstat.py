import csv
import os
import re
import requests
import psycopg

def fetch_data(api_url, api_key):
    headers = {"X-CMC_PRO_API_KEY": api_key}
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None
def insert_space(s):

    # Chèn space trước các chữ cái in hoa, trừ chữ cái đầu tiên
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', s)   

def save_to_csv(data, filename):
    if not data:
        print("No data to save.")
        return
    
    # Sắp xếp dữ liệu theo biến count (số lượng tag chứa "portfolio") giảm dần
    sorted_data = sorted(
        data,
        key=lambda item: sum(1 for s in item.get("tags", []) if "portfolio" in s.lower()),
        reverse=True
    )
    
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
    
    with open(desktop_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Fullname", "Total", "Rank", "Since", "Volume", "Funds", "Tags"])
        db_data = []
        for item in sorted_data:
            year = item.get("date_added", "")[:4]
            # Tính số tag chứa "portfolio" (Total)
            count = sum(1 for s in item.get("tags", []) if "portfolio" in s.lower())
            # Lấy danh sách các tag chứa "portfolio" và loại bỏ phần '-portfolio'
            portfolio = [s.replace("-portfolio", "").strip() for s in item.get("tags", []) if "portfolio" in s.lower()]
            tags = [s for s in item.get("tags", []) if not "portfolio" in s.lower()]
            portfolio = [
                ''.join(word.capitalize() for word in tag.replace('-', ' ').split())
                for tag in portfolio
            ]
            portfolio = [insert_space(name) for name in portfolio]
            tags = [
                ''.join(word.capitalize() for word in tag.replace('-', ' ').split())
                for tag in tags
            ]
            tags = [insert_space(name) for name in tags]
            portfolio = ", ".join(portfolio)
            tags = ", ".join(tags)
            vol = item.get("quote", {}).get("USD", {}).get("volume_24h", 0)
            market_cap = item.get("quote", {}).get("USD", {}).get("market_cap", 0)
            volmar = 0
            if market_cap and vol:
                volmar = (vol / market_cap) * 100
                volmar = round(volmar, 2)
        
            writer.writerow([
                item.get("symbol", ""),
                item.get("name", ""),
                count,
                item.get("cmc_rank", ""),
                year,
                volmar,
                portfolio,
                tags
            ])
            db_data.append((item.get("symbol", ""),
                item.get("name", ""),
                count,
                item.get("cmc_rank", ""),
                year,
                volmar,
                portfolio,
                tags))
    save_to_db(db_data)
    
    print(f"Data saved to {desktop_path}")

def save_to_db(data):
    conn = psycopg.connect(
            dbname="an",
            user="postgres",
            password="root",
            host="localhost",
            port="5432"
        )
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO crypto_data (Name, Fullname, Total, Rank, Since, Volume, Funds, Tags)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    cursor.executemany(insert_query, data)
    conn.commit()

    cursor.close()
    conn.close()

print("Dữ liệu đã được lưu vào PostgreSQL database.")
    
def distinct_by_name(funds):
    seen = set()
    distinct_funds = []
    
    for fund in funds:
        name = fund.get("name")
        if name and name not in seen:
            seen.add(name)
            distinct_funds.append(fund)
    
    return distinct_funds

# Thay thế bằng API Key thật của bạn
API_KEY = "502a400a-5710-4aa0-8bb5-0aefa8954c65"
API_URL = "https://api.cryptorank.io"

coins = []
#funds = fetch_data(API_URL+"/v2/funds/map", API_KEY)
#for fund in funds.data:
funds = fetch_data("https://pro-api.coinmarketcap.com/v1/cryptocurrency/categories?limit=5000", API_KEY)
for fund in funds["data"]:
    if 'Portfolio' in fund.get('name'):
        fund_detail = fetch_data(f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/category?id={fund["id"]}", API_KEY)
        if fund_detail is not None and fund_detail["data"]["coins"] is not None:
            coins.extend(fund_detail["data"]["coins"]) 
coins_d = distinct_by_name(coins)
save_to_csv(coins_d, "crypto_funds.csv")


