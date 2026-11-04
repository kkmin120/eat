

import re
from itertools import combinations
from collections import Counter

import streamlit as st
import pandas as pd
import plotly.express as px


# --------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.caption("송탄고 중식 메뉴의 연관 규칙 분석")
st.markdown("---")


# --------------------------------------------------
# 2. 데이터 불러오기
# --------------------------------------------------

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "it-teacher-go/data-share-/main/songtan_meals_184.csv"
)


@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8")

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV에 '{col}' 열이 없습니다.")

    df = df.dropna(subset=["메뉴"]).copy()

    return df


try:
    df = load_data()

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# --------------------------------------------------
# 3. 메뉴 전처리
# --------------------------------------------------

def clean_menu(menu):

    menu = str(menu).strip()

    # 괄호와 괄호 안의 내용 제거
    while True:
        cleaned = re.sub(
            r"\([^()]*\)|（[^（）]*）",
            "",
            menu
        )

        if cleaned == menu:
            break

        menu = cleaned

    return menu.strip()


# 하루의 식단을 하나의 장바구니로 구성
transactions = []

for menu_text in df["메뉴"]:

    menu_list = str(menu_text).split("|")

    cleaned_menus = []

    for menu in menu_list:

        menu = clean_menu(menu)

        if menu:
            cleaned_menus.append(menu)

    # 하루에 같은 메뉴가 여러 번 있어도 한 번만 계산
    cleaned_menus = sorted(set(cleaned_menus))

    transactions.append(cleaned_menus)


# --------------------------------------------------
# 4. 메뉴별 등장 횟수 계산
# --------------------------------------------------

menu_counter = Counter()

for basket in transactions:
    menu_counter.update(basket)

total_days = len(transactions)
total_menus = len(menu_counter)


# --------------------------------------------------
# 5. 함께 나온 메뉴 쌍 계산
# --------------------------------------------------

pair_counter = Counter()

for basket in transactions:

    for pair in combinations(basket, 2):

        pair_counter[pair] += 1


# 함께 나온 적이 있는 고유 메뉴 쌍
total_pairs = len(pair_counter)


# --------------------------------------------------
# 6. 연관 규칙 생성
# --------------------------------------------------

rules = []

for (menu_a, menu_b), together_count in pair_counter.items():

    # A → B
    support = together_count / total_days

    confidence_ab = (
        together_count / menu_counter[menu_a]
    )

    lift_ab = (
        confidence_ab /
        (menu_counter[menu_b] / total_days)
    )

    rules.append({
        "조건": menu_a,
        "결과": menu_b,
        "동시": together_count,
        "지지도": support,
        "신뢰도": confidence_ab,
        "향상도": lift_ab
    })

    # B → A
    confidence_ba = (
        together_count / menu_counter[menu_b]
    )

    lift_ba = (
        confidence_ba /
        (menu_counter[menu_a] / total_days)
    )

    rules.append({
        "조건": menu_b,
        "결과": menu_a,
        "동시": together_count,
        "지지도": support,
        "신뢰도": confidence_ba,
        "향상도": lift_ba
    })


rules_df = pd.DataFrame(
    rules,
    columns=[
        "조건", "결과", "동시",
        "지지도", "신뢰도", "향상도"
    ]
)


# --------------------------------------------------
# 7. 전체 데이터 요약
# --------------------------------------------------

st.subheader("📊 전체 급식 데이터")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("급식 일수", f"{total_days:,}일")

with col2:
    st.metric("메뉴 종류 수", f"{total_menus:,}개")

with col3:
    st.metric("함께 나온 메뉴 쌍", f"{total_pairs:,}쌍")

st.markdown("---")


# --------------------------------------------------
# 8. 최소 동시 일수 설정
# --------------------------------------------------

st.subheader("⚙️ 분석 조건")

min_together = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 규칙은 분석에서 제외합니다."
)


# 최소 동시 일수 적용
filtered_rules = rules_df[
    rules_df["동시"] >= min_together
].copy()


# --------------------------------------------------
# 9. 정렬 및 메뉴 필터
# --------------------------------------------------

st.subheader("🔍 연관 규칙 탐색")

col1, col2 = st.columns(2)

with col1:

    sort_option = st.selectbox(
        "정렬 기준",
        [
            "향상도 순",
            "신뢰도 순",
            "동시 순"
        ]
    )

with col2:

    menu_options = ["전체 메뉴"] + sorted(menu_counter.keys())

    selected_menu = st.selectbox(
        "규칙 좁혀 보기",
        menu_options
    )


# 정렬
if sort_option == "향상도 순":

    sorted_df = filtered_rules.sort_values(
        ["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    )

elif sort_option == "신뢰도 순":

    sorted_df = filtered_rules.sort_values(
        ["신뢰도", "향상도", "동시"],
        ascending=[False, False, False]
    )

else:

    sorted_df = filtered_rules.sort_values(
        ["동시", "향상도", "신뢰도"],
        ascending=[False, False, False]
    )


# 선택한 메뉴 필터
if selected_menu != "전체 메뉴":

    display_rules = sorted_df[
        (sorted_df["조건"] == selected_menu) |
        (sorted_df["결과"] == selected_menu)
    ].copy()

else:

    display_rules = sorted_df.copy()


# --------------------------------------------------
# 10. 연관 규칙 표
# --------------------------------------------------

st.subheader("📋 연관 규칙 전체 표")

# 남은 규칙 수 표시
st.markdown(
    f"**현재 조건에 해당하는 규칙: {len(display_rules):,}개**"
)

st.caption(
    f"최소 동시 일수 {min_together}일 이상인 규칙만 표시합니다."
)

display_df = display_rules.copy()

# 소수점 표시
if not display_df.empty:

    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x:.4f}"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x:.4f}"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.4f}"
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=450
)


st.markdown("---")


# --------------------------------------------------
# 11. 함께 나온 적 없는 짝
# --------------------------------------------------

st.subheader("🚫 함께 나온 적 없는 짝")

st.write(
    "선택한 메뉴와 같은 날 한 번도 함께 나오지 않았지만, "
    "혼자서는 10일 이상 등장한 메뉴를 찾아봅니다."
)

# 위의 규칙 필터와 별도로 메뉴 선택
absent_menu = st.selectbox(
    "함께 나온 적 없는 짝을 찾을 기준 메뉴",
    sorted(menu_counter.keys()),
    key="absent_menu_select"
)

# 선택한 메뉴가 등장한 날짜 수
selected_menu_days = menu_counter[absent_menu]

# 선택한 메뉴와 함께 나온 적이 있는 메뉴 모음
cooccurring_menus = set()

for (menu_a, menu_b), count in pair_counter.items():

    if menu_a == absent_menu:
        cooccurring_menus.add(menu_b)

    elif menu_b == absent_menu:
        cooccurring_menus.add(menu_a)


# 등장 횟수가 10일 이상이고,
# 선택한 메뉴와 함께 나온 적이 없는 메뉴 찾기
absent_results = []

for menu, count in menu_counter.items():

    if menu == absent_menu:
        continue

    if count < 10:
        continue

    if menu in cooccurring_menus:
        continue

    absent_results.append({
        "메뉴": menu,
        "등장 일수": count
    })


# 등장 일수가 많은 순으로 정렬
absent_df = pd.DataFrame(
    absent_results,
    columns=["메뉴", "등장 일수"]
)

if not absent_df.empty:

    absent_df = absent_df.sort_values(
        "등장 일수",
        ascending=False
    ).reset_index(drop=True)


# 선택한 메뉴의 등장 일수 표시
st.markdown(
    f"**선택한 메뉴: {absent_menu} | 등장 일수: {selected_menu_days}일**"
)

st.caption(
    "아래 메뉴는 선택한 메뉴와 함께 나온 기록이 없으며, "
    "각각 10일 이상 등장한 메뉴입니다."
)

if absent_df.empty:

    st.info(
        "조건에 맞는 메뉴가 없습니다. 다른 메뉴를 선택해 보세요."
    )

else:

    st.markdown(
        f"**함께 나온 적 없는 메뉴: {len(absent_df):,}개**"
    )

    st.dataframe(
        absent_df,
        use_container_width=True,
        hide_index=True,
        height=350
    )


st.markdown("---")


# --------------------------------------------------
# 12. 향상도 TOP 10 그래프
# --------------------------------------------------

st.subheader("📈 향상도 TOP 10")

st.write(
    "향상도가 높은 메뉴 조합일수록 두 메뉴가 서로 관련되어 "
    "함께 등장하는 경향이 강하다는 뜻입니다."
)

# 최소 동시 일수와 메뉴 필터 모두 적용
if selected_menu != "전체 메뉴":

    chart_source = filtered_rules[
        (filtered_rules["조건"] == selected_menu) |
        (filtered_rules["결과"] == selected_menu)
    ].copy()

else:

    chart_source = filtered_rules.copy()


# 향상도 기준 상위 10개
top10 = chart_source.sort_values(
    ["향상도", "신뢰도", "동시"],
    ascending=[False, False, False]
).head(10).copy()


if top10.empty:

    st.info(
        "현재 조건에 해당하는 그래프 데이터가 없습니다."
    )

else:

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    fig = px.bar(
        top10.sort_values(
            "향상도",
            ascending=True
        ),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        color="향상도",
        color_continuous_scale="Blues",
        labels={
            "향상도": "향상도",
            "규칙": "연관 규칙"
        },
        title="연관 규칙 향상도 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside"
    )

    fig.update_layout(
        height=500,
        xaxis_title="향상도",
        yaxis_title="메뉴 규칙",
        showlegend=False,
        coloraxis_showscale=False,
        margin=dict(
            l=20,
            r=60,
            t=60,
            b=30
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# --------------------------------------------------
# 13. 지표 설명
# --------------------------------------------------

st.markdown("---")

st.subheader("💡 연관 규칙 지표 알아보기")

with st.expander("지지도, 신뢰도, 향상도란?"):

    st.markdown("""
    **1. 지지도 (Support)**

    전체 급식 일수 중 두 메뉴가 함께 나온 날의 비율입니다.

    지지도 = 두 메뉴가 함께 나온 일수 ÷ 전체 급식 일수

    **2. 신뢰도 (Confidence)**

    조건 메뉴가 나온 날 중 결과 메뉴도 함께 나온 비율입니다.

    신뢰도 = 두 메뉴가 함께 나온 일수 ÷ 조건 메뉴가 나온 일수

    **3. 향상도 (Lift)**

    두 메뉴가 서로 독립적이라고 가정했을 때보다
    실제로 얼마나 더 자주 함께 나오는지를 나타냅니다.

    향상도 = 신뢰도 ÷ 결과 메뉴의 등장 비율

    - 향상도 > 1 : 함께 나오는 경향이 있음
    - 향상도 = 1 : 특별한 연관성이 없음
    - 향상도 < 1 : 함께 나오는 경향이 적음

    **4. 함께 나온 적 없는 짝**

    선택한 메뉴와 같은 날 한 번도 함께 나오지 않은 메뉴 중
    혼자서 10일 이상 등장한 메뉴를 보여 줍니다.

    **주의:** 연관성이 있다고 해서 한 메뉴가 다른 메뉴를
    나오게 만들었다는 뜻은 아닙니다.
    """)
