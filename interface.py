import os
import json
from dotenv import load_dotenv

import requests
import pandas as pd

print("=== interface.py start ===")

# =========================
# 1. 環境変数
# =========================
load_dotenv()

API_KEY = os.getenv("ESTAT_API_KEY")
if not API_KEY:
    raise ValueError("ESTAT_API_KEY が .env に設定されていません")

BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

# 小売物価統計
STATS_DATA_ID = "0003421913"


# =========================
# 2. パラメータ作成（★ここが修正ポイント）
# =========================
def build_params(region_code=None, item_code=None, limit=100):

    params = {
        "appId": API_KEY,
        "statsDataId": STATS_DATA_ID,
        "format": "json",
        "limit": limit,
    }

    if region_code:
        params["cdArea"] = str(region_code)

    # ★ここが重要（cat02に変更）
    if item_code:
        params["cdCat02"] = str(item_code).zfill(5)

    return params


# =========================
# 3. API取得
# =========================
def fetch_data(params):

    response = requests.get(BASE_URL, params=params)
    data = response.json()

    print("\n=== params ===")
    print(params)

    print("\n=== RESULT ===")
    print(data["GET_STATS_DATA"]["RESULT"])

    values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"].get("VALUE", [])

    if isinstance(values, dict):
        values = [values]

    print(f"\n=== 件数: {len(values)} ===")

    return values


# =========================
# 4. DataFrame変換（★time修正）
# =========================
def to_dataframe(values):

    rows = []

    for v in values:
        time_code = str(v["@time"])

        rows.append({
            "region_code": v.get("@area"),
            "region_name": v.get("@areaname"),
            "item_code": v.get("@cat02"),
            "item_name": v.get("@cat02name"),
            "year": time_code[:4],
            "month": time_code[-2:],   # ★修正ポイント
            "price": v.get("$")
        })

    df = pd.DataFrame(rows)

    return df


# =========================
# 5. メイン関数
# =========================
def get_price_data(region_code, item_code):

    params = build_params(region_code, item_code)
    values = fetch_data(params)

    if not values:
        print("⚠️ データなし")
        return pd.DataFrame()

    df = to_dataframe(values)

    return df


# =========================
# 6. 動作確認
# =========================
if __name__ == "__main__":

    print("\n=== テスト実行 ===")

    # 札幌 × うるち米
    df = get_price_data("01100", "01001")

    print("\n=== DataFrame ===")
    print(df.head())