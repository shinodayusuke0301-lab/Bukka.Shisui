from dotenv import load_dotenv
import os
from openai import OpenAI

# =========================
# 設定
# =========================
# .env読み込み
load_dotenv()

# openAI APIキー取得
api_key = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# エラーチェック
if not api_key:
    raise ValueError("OPENAI_API_KEYが.envに設定されていません")

client = OpenAI(api_key=api_key)

# =========================
# AIコメント生成
#=========================
def generate_comment(analysis_result: dict) -> str:
    """
    analysis.py の結果をもとにAIコメント生成
    """

    period_change = analysis_result.get("period_change")
    yoy_diff = analysis_result.get("yoy_diff")
    item_name = analysis_result.get("item_name")
    region_name = analysis_result.get("region_name")

    prompt = f"""
あなたは経済アナリストです。
以下のデータをもとに、消費者向けに分かりやすいアドバイスを日本語で作成してください。

条件：
・専門用語は使わずカジュアル
・150文字程度
・最近の価格変動を説明
・今後の価格予想から、買うべきか待つべきか具体的にアドバイス
・絵文字OK

データ：
商品：{item_name}
地域：{region_name}
期間変動率：{period_change}%
前年同月差：{yoy_diff}円
"""

    response = client.chat.completions.create(
        model=MODEL,  
        messages=[
            {"role": "system", "content": "あなたは優秀な経済アナリストです。"},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content