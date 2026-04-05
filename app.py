
import streamlit as st
import pandas as pd
import interface as estat
import analysis as ana
import ai_comment as ai

# ==========================================
# 1. 初期設定
# ==========================================
st.set_page_config(page_title="物価水位", layout="wide")


# ==========================================
# 2. マスタ読み込み
# ==========================================
@st.cache_data
def load_masters():
    item_df = pd.read_csv("master_item.csv", dtype={"item_code": str})
    region_df = pd.read_csv("master_region.csv", dtype={"region_code": str})

    item_df.columns = item_df.columns.str.strip()
    region_df.columns = region_df.columns.str.strip()

    item_df["item_code"] = item_df["item_code"].astype(str).str.zfill(5)
    region_df["region_code"] = region_df["region_code"].astype(str).str.zfill(5)

    item_options = dict(zip(item_df["item_name"], item_df["item_code"]))
    region_options = dict(zip(region_df["region_name"], region_df["region_code"]))
    units = dict(zip(item_df["item_code"], item_df["unit"]))

    return region_options, item_options, units


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["month"] = pd.to_numeric(out["month"], errors="coerce")

    out = out.dropna(subset=["price", "year", "month"]).copy()

    out["year"] = out["year"].astype(int)
    out["month"] = out["month"].astype(int)

    out = out.sort_values(["year", "month"]).reset_index(drop=True)
    return out


def safe_analyze(plot_df: pd.DataFrame) -> dict:
    if plot_df.empty:
        raise ValueError("分析対象データが空です")

    if hasattr(ana, "analyze_price"):
        return ana.analyze_price(plot_df)

    latest_price = plot_df["price"].iloc[-1]
    average_price = plot_df["price"].mean()
    max_price = plot_df["price"].max()
    min_price = plot_df["price"].min()

    mom_diff = None
    yoy_diff = None
    period_change = None

    if len(plot_df) >= 2:
        mom_diff = plot_df["price"].iloc[-1] - plot_df["price"].iloc[-2]
        first_price = plot_df["price"].iloc[0]
        if first_price != 0:
            period_change = ((plot_df["price"].iloc[-1] / first_price) - 1) * 100

    if len(plot_df) >= 13:
        yoy_diff = plot_df["price"].iloc[-1] - plot_df["price"].iloc[-13]

    return {
        "latest_price": latest_price,
        "average_price": average_price,
        "mom_diff": mom_diff,
        "yoy_diff": yoy_diff,
        "max_price": max_price,
        "min_price": min_price,
        "period_change": period_change,
        "item_name": plot_df["item_name"].iloc[-1],
        "region_name": plot_df["region_name"].iloc[-1],
    }


# ==========================================
# 3. マスタ展開
# ==========================================
region_options, item_options, units = load_masters()

# ==========================================
# 4. UI
# ==========================================
st.title("🌊 物価水位")
st.caption("e-Stat API × OpenAI：リアルタイム物価分析ダッシュボード")

st.divider()

st.sidebar.header("検索条件")

selected_region_name = st.sidebar.selectbox("表示都市", list(region_options.keys()))
selected_item_name = st.sidebar.selectbox("表示製品", list(item_options.keys()))

selected_region_code = str(region_options[selected_region_name]).zfill(5)
selected_item_code = str(item_options[selected_item_name]).zfill(5)

selected_period = st.sidebar.slider("表示期間 (直近ヶ月)", 1, 60, 24)
update_clicked = st.sidebar.button("データを更新")

should_run = update_clicked or "initialized" not in st.session_state
st.session_state["initialized"] = True

# ==========================================
# 5. メイン処理
# ==========================================
if should_run:
    try:
        raw_df = estat.get_price_data(
            region_code=selected_region_code,
            item_code=selected_item_code
        )

        if raw_df.empty:
            st.error("該当データが取得できませんでした。地域コード・品目コード・API条件を確認してください。")
            st.stop()

        raw_df["region_name"] = selected_region_name
        raw_df["item_name"] = selected_item_name

        raw_df = prepare_dataframe(raw_df)

        if raw_df.empty:
            st.error("取得後のデータ整形で有効なデータが残りませんでした。")
            st.stop()

        plot_df = raw_df.tail(selected_period).copy()

        if plot_df.empty:
            st.error("表示期間に該当するデータがありません。")
            st.stop()

        res = safe_analyze(plot_df)
        unit_text = units.get(selected_item_code, "円")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            latest_price = res.get("latest_price")
            average_price = res.get("average_price")
            st.metric("最新価格", f"{latest_price:,.0f} {unit_text}" if pd.notna(latest_price) else "-")
            st.metric("期間平均", f"{average_price:,.0f} {unit_text}" if pd.notna(average_price) else "-")

        with col2:
            mom = res.get("mom_diff")
            yoy = res.get("yoy_diff")
            st.metric("前月との差額", f"{mom:+,.0f} {unit_text}" if pd.notna(mom) else "データなし")
            st.metric("前年同月との差額", f"{yoy:+,.0f} {unit_text}" if pd.notna(yoy) else "データなし")

        with col3:
            max_price = res.get("max_price")
            min_price = res.get("min_price")
            st.metric("期間最高額", f"{max_price:,.0f} {unit_text}" if pd.notna(max_price) else "-")
            st.metric("期間最低額", f"{min_price:,.0f} {unit_text}" if pd.notna(min_price) else "-")

        with col4:
            change = res.get("period_change")
            st.metric("表示期間内 変動率", f"{change:+.1f} %" if pd.notna(change) else "---")

        st.divider()

        col_chart, col_ai = st.columns([2, 1])

        with col_chart:
            st.subheader(f"📈 {selected_item_name} の価格推移 ({selected_region_name})")

            plot_df["date_label"] = (
                plot_df["year"].astype(str)
                + "/"
                + plot_df["month"].astype(str).str.zfill(2)
            )

            chart_data = plot_df.set_index("date_label")[["price"]]
            st.line_chart(chart_data, use_container_width=True)

        with col_ai:
            st.subheader("🤖 AI分析コメント")
            with st.spinner("AIが分析中..."):
                try:
                    ai_message = ai.generate_comment(res)
                    st.info(ai_message)
                except Exception as ai_err:
                    st.error(f"AIコメントの生成に失敗しました: {ai_err}")

            if hasattr(ai, "MODEL"):
                st.caption(f"Powered by {ai.MODEL}")

#        st.divider()

#        st.subheader("取得データ")

#        display_df = plot_df.copy()
#        display_df["年月"] = (
#            display_df["year"].astype(str)
#            + "/"
#            + display_df["month"].astype(str).str.zfill(2)
#        )

#        display_df = display_df[["年月", "region_name", "item_name", "price"]].rename(
#            columns={
#                "region_name": "地域",
#                "item_name": "品目",
#                "price": f"価格({unit_text})"
#            }
#        )

#        st.dataframe(display_df, use_container_width=True)

    except FileNotFoundError as e:
        st.error(f"CSVファイルが見つかりません: {e}")
        st.info("master_item.csv / master_region.csv が app.py と同じフォルダにあるか確認してください。")

    except Exception as e:
        st.error(f"データの取得または分析中にエラーが発生しました: {e}")
        st.info("APIキー、interface.py、analysis.py、ai_comment.py、CSVファイルの配置を確認してください。")

# ==========================================
# 6. フッター
# ==========================================
st.divider()
st.caption("Data Source: e-Stat (政府統計の総合窓口) / AI Analysis: OpenAI")