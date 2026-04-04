import pandas as pd


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    interface.py から受け取った DataFrame を分析しやすい形に整える

    やること
    - 必須カラム確認
    - year, month, price を数値化
    - 欠損行を削除
    - 年月順に並び替え
    """
    required_columns = [
        "region_code",  # 地域コード
        "region_name",  # 地域名
        "item_code",    # 商品コード
        "item_name",    # 商品名
        "year",         # 年
        "month",        # 月
        "price",        # 価格
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"必要なカラムが不足しています: {missing_columns}")

    df = df.copy()

    # 数値型へ変換
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # year / month / price が欠けている行は削除
    df = df.dropna(subset=["year", "month", "price"])

    if df.empty:
        raise ValueError("有効なデータがありません")

    # int型に変換
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)

    # 年月順に並び替え
    df = df.sort_values(["year", "month"]).reset_index(drop=True)

    return df


def calculate_average_price(df: pd.DataFrame) -> float:
    """
    検索された期間全体の平均価格
    """
    return round(float(df["price"].mean()), 1)


def calculate_mom_diff(df: pd.DataFrame) -> float | None:
    """
    前月との差額（円）
    最新月 - 前月
    """
    if len(df) < 2:
        return None

    latest_price = df.iloc[-1]["price"]
    prev_price = df.iloc[-2]["price"]

    return round(float(latest_price - prev_price), 1)


def calculate_yoy_diff(df: pd.DataFrame) -> float | None:
    """
    前年同月との差額（円）
    最新月 - 前年同月
    前年同月データがなければ None
    """
    latest_row = df.iloc[-1]
    latest_price = latest_row["price"]
    latest_year = latest_row["year"]
    latest_month = latest_row["month"]

    same_month_last_year = df[
        (df["year"] == latest_year - 1) &
        (df["month"] == latest_month)
    ]

    if same_month_last_year.empty:
        return None

    last_year_price = same_month_last_year.iloc[-1]["price"]

    return round(float(latest_price - last_year_price), 1)


def calculate_period_change(df: pd.DataFrame) -> float | None:
    """
    表示期間内変動率（%）
    (最新価格 - 最初の価格) / 最初の価格 × 100
    """
    if len(df) < 2:
        return None

    first_price = df.iloc[0]["price"]
    latest_price = df.iloc[-1]["price"]

    if first_price == 0:
        return None

    period_change = ((latest_price - first_price) / first_price) * 100

    return round(float(period_change), 1)


def calculate_max_price(df: pd.DataFrame) -> float:
    """
    期間内で一番高い価格
    """
    return round(float(df["price"].max()), 1)


def calculate_min_price(df: pd.DataFrame) -> float:
    """
    期間内で一番低い価格
    """
    return round(float(df["price"].min()), 1)


def analyze_price(df: pd.DataFrame) -> dict:
    """
    interface.py から受け取った DataFrame を分析して、
    フロントで使う辞書形式で返す

    返す項目
    - region_code    : 地域コード
    - region_name    : 地域名
    - item_code      : 商品コード
    - item_name      : 商品名
    - latest_price   : 最新月の価格
    - average_price  : 検索された期間全体の平均価格
    - mom_diff       : 前月との差額（円）
    - yoy_diff       : 前年同月との差額（円）
    - period_change  : 表示期間内変動率（%）
    - max_price      : 期間内で一番高い価格
    - min_price      : 期間内で一番低い価格
    """
    df = preprocess_data(df)

    latest_row = df.iloc[-1]

    latest_price = round(float(latest_row["price"]), 1)
    average_price = calculate_average_price(df)
    mom_diff = calculate_mom_diff(df)
    yoy_diff = calculate_yoy_diff(df)
    period_change = calculate_period_change(df)
    max_price = calculate_max_price(df)
    min_price = calculate_min_price(df)

    result = {
        "region_code": str(latest_row["region_code"]),   # 地域コード
        "region_name": str(latest_row["region_name"]),   # 地域名
        "item_code": str(latest_row["item_code"]),       # 商品コード
        "item_name": str(latest_row["item_name"]),       # 商品名
        "latest_price": latest_price,                    # 最新月の価格
        "average_price": average_price,                  # 検索された期間全体の平均価格
        "mom_diff": mom_diff,                            # 前月との差額（円）
        "yoy_diff": yoy_diff,                            # 前年同月との差額（円）
        "period_change": period_change,                  # 表示期間内変動率（%）
        "max_price": max_price,                          # 期間内で一番高い価格
        "min_price": min_price,                          # 期間内で一番低い価格
    }

    return result