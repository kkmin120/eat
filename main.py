
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
    """
    메뉴 이름의 괄호와 괄호 안 내용을 제거한다.
    예: 부대찌개(사골) -> 부대찌개
    """

    menu = str(menu).strip()

    # 괄호 안의 내용 제거
    # 중첩된 괄호가 있어도 반복해서 제거
    while True:
        cleaned = re.sub(r"\([^()]*\)", "", menu)
        if cleaned == menu:
            break
        menu = cleaned

    # 앞뒤 공백 제거
    menu = menu.strip()

    return menu


# 하루의 식단을 하나의 장바구니로 구성
transactions = []

for menu_text in df["메뉴"]:

    menu_list = str(menu_text).split("|")

    cleaned_menus = []

    for menu in menu_list:
        menu = clean_menu(menu)

        if menu:
            cleaned_menus.append(menu)

    # 같은 날 같은 메뉴는 한 번만 계산
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

    # 하루에 함께 나온 모든 메뉴 조합
    for pair in combinations(basket, 2):

        pair_counter[pair] += 1


# 함께 나온 적이 있는 고유 메뉴 쌍의 수
total_pairs = len(pair_counter)


# --------------------------------------------------
# 6. 연관 규칙 생성
# --------------------------------------------------

rules = []

for (menu_a, menu_b), together_count in pair_counter.items():

    # A -> B
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

    # B -> A
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


rules_df = pd.DataFrame(rules)


# --------------------------------------------------
# 7. 데이터 요약
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
# 8. 정렬 및 메뉴 필터 설정
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
        "메뉴 선택",
        menu_options
    )


# 정렬 기준에 따른 정렬
if sort_option == "향상도 순":

    sorted_df = rules_df.sort_values(
        ["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    )

elif sort_option == "신뢰도 순":

    sorted_df = rules_df.sort_values(
        ["신뢰도", "향상도", "동시"],
        ascending=[False, False, False]
    )

else:

    sorted_df = rules_df.sort_values(
        ["동시", "향상도", "신뢰도"],
        ascending=[False, False, False]
    )


# 선택한 메뉴가 조건 또는 결과에 포함된 규칙만 표시
if selected_menu != "전체 메뉴":

    filtered_df = sorted_df[
        (sorted_df["조건"] == selected_menu) |
        (sorted_df["결과"] == selected_menu)
    ].copy()

else:

    filtered_df = sorted_df.copy()


# --------------------------------------------------
# 9. 연관 규칙 표
# --------------------------------------------------

st.subheader("📋 연관 규칙 전체 표")

st.caption(
    "조건 메뉴가 나왔을 때 결과 메뉴도 함께 나온 관계를 보여 줍니다."
)

display_df = filtered_df.copy()

# 소수점 표시
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

st.caption(
    f"현재 표시 중인 규칙: {len(filtered_df):,}개"
)


st.markdown("---")


# --------------------------------------------------
# 10. 향상도 상위 10개 그래프
# --------------------------------------------------

st.subheader("📈 향상도 TOP 10")

st.write(
    "향상도가 높은 메뉴 조합일수록 두 메뉴가 서로 관련되어 "
    "함께 등장하는 경향이 강하다는 뜻입니다."
)

# 메뉴 필터 적용
if selected_menu != "전체 메뉴":

    chart_source = rules_df[
        (rules_df["조건"] == selected_menu) |
        (rules_df["결과"] == selected_menu)
    ].copy()

else:

    chart_source = rules_df.copy()


# 향상도 기준 상위 10개
top10 = chart_source.sort_values(
    ["향상도", "신뢰도", "동시"],
    ascending=[False, False, False]
).head(10).copy()


if len(top10) == 0:

    st.info("선택한 메뉴에 해당하는 규칙이 없습니다.")

else:

    # 그래프에 표시할 규칙 이름
    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    # 가로 막대그래프
    fig = px.bar(
        top10.sort_values("향상도", ascending=True),
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
        margin=dict(l=20, r=60, t=60, b=30)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# --------------------------------------------------
# 11. 지표 설명
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

    조건 메뉴와 결과 메뉴가 서로 독립적이라고 가정했을 때보다
    실제로 얼마나 더 자주 함께 나오는지를 나타냅니다.

    향상도 = 신뢰도 ÷ 결과 메뉴의 등장 비율

    - 향상도 > 1 : 함께 나오는 경향이 있음
    - 향상도 = 1 : 특별한 연관성이 없음
    - 향상도 < 1 : 함께 나오는 경향이 적음

    **주의:** 연관성이 있다고 해서 한 메뉴가 다른 메뉴를
    나오게 만들었다는 뜻은 아닙니다.
    """)
