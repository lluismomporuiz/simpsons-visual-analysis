##########################
#####LLUÍS MOMPÓ RUIZ#####
##########################

from pathlib import Path

import streamlit as st
import pandas as pd
import altair as alt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

st.set_page_config(layout="wide", page_title="The Simpsons — Visual Analysis")

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_DIR / "simpsons-episodes-clean.csv")
    return df[["ID","Season", "Number_season", "Rating", "Viewers", "Votes", "Weekday"]]

df = load_data()

season_avg_rating  = df.groupby("Season")["Rating"].mean().reset_index()
season_avg_viewers = df.groupby("Season")["Viewers"].mean().reset_index()
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

@st.cache_data
def get_outliers(df):
    results = []
    for col in ["Viewers", "Rating"]:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        out = df[(df[col] < lo) | (df[col] > hi)].copy()
        out["Outlier_direction"] = "High"
        out.loc[out[col] < lo, "Outlier_direction"] = "Low"
        out["Outlier_column"] = col
        results.append(out)
    return pd.concat(results).reset_index(drop=True)

outliers_df = get_outliers(df)

x_season  = alt.X("Season:O",  title="Season",          sort="ascending",   axis=alt.Axis(labelAngle=0))
x_weekday = alt.X("Weekday:O", title="Day of the Week",  sort=WEEKDAY_ORDER, axis=alt.Axis(labelAngle=0))

def chart_average_rating(w, h):
    base = alt.Chart(season_avg_rating).encode(
        x=x_season,
        y=alt.Y("Rating:Q", title="Average Rating", scale=alt.Scale(domain=[6, 9]))
    )
    return (
        base.mark_line(color="steelblue") +
        base.mark_circle(color="red", size=40) +
        base.mark_text(dy=-10, dx=1, fontSize=9).encode(text=alt.Text("Rating:Q", format=".1f"))
    ).properties(title="Average Rating per Season", width=w, height=h)

def chart_heatmap(w, h):
    base = alt.Chart(df).encode(
        x=alt.X("Season:O", title="Season", axis=alt.Axis(orient="top", labelAngle=0)),
        y=alt.Y("Number_season:O", title="Episode Number")
    )
    hmap = base.mark_rect(stroke="white", strokeWidth=0.5).encode(
        color=alt.Color("Rating:Q", title="Rating",
                        scale=alt.Scale(scheme="viridis"),
                        legend=alt.Legend(orient="right"))
    )
    txt = base.mark_text(baseline="middle", fontSize=7).encode(
        text=alt.Text("Rating:Q", format=".1f"),
        color=alt.condition(alt.datum.Rating >= 7.5, alt.value("black"), alt.value("white"))
    ).transform_filter((alt.datum.Rating >= 8.5) | (alt.datum.Rating <= 6.5))
    return (hmap + txt).properties(title="Individual Episode's Ratings", width=w, height=h)

def chart_average_season(w, h):
    base_avg = alt.Chart(season_avg_viewers).encode(
        x=x_season, y=alt.Y("Viewers:Q", title="Viewers (millions)")
    )
    base_pts = alt.Chart(df).encode(
        x=x_season, y=alt.Y("Viewers:Q", title="Viewers (millions)")
    )
    return (
        base_pts.mark_circle(color="steelblue", opacity=0.3) +
        base_avg.mark_line(color="steelblue") +
        base_avg.mark_circle(color="red", size=40) +
        base_avg.mark_text(dy=-8, dx=5, fontSize=9).encode(text=alt.Text("Viewers:Q", format=".1f"))
    ).properties(title="Viewership per Season (Distribution and Average)", width=w, height=h)


def chart_scatter(w, h):
    df_flagged = df.copy()
    df_flagged["Type"] = df_flagged["ID"].isin(outliers_df["ID"]).map(
        {True: "Outlier", False: "No outlier"}
    )

    base = alt.Chart(df_flagged).encode(
        x=alt.X("Rating:Q", title="Rating", scale=alt.Scale(zero=False)),
        y=alt.Y("Viewers:Q", title="Viewers (millions)", scale=alt.Scale(domain=[0, 35])),
        color=alt.Color(
            "Type:N",
            scale=alt.Scale(
                domain=["No outlier", "Outlier"],
                range=["steelblue", "darkorange"]
            )
        ),
        size=alt.Size("Votes:Q", title="Votes", scale=alt.Scale(range=[10, 400])),
    )

    scatter = base.mark_circle(stroke="white", strokeWidth=0.5, opacity=0.5)

    regression = alt.Chart(df).transform_regression(
        "Rating", "Viewers"
    ).mark_line(color="black", size=2, clip=True).encode(
        x=alt.X("Rating:Q"),
        y=alt.Y("Viewers:Q")
    )

    return (scatter + regression).properties(
        title="Ratings vs Viewers with Highlighted Outliers",
        width=w,
        height=h
    )
def chart_weekday(w, h):
    bar = alt.Chart(df).mark_bar(color="#9ECAE1").encode(
        x=x_weekday,
        y=alt.Y("count():Q", title="Number of Episodes")
    ).properties(title="Number of Episodes Aired per Weekday", width=w, height=h)

    box = alt.Chart(df).mark_boxplot(color="#9ECAE1").encode(
        x=x_weekday,
        y=alt.Y("Viewers:Q", title="Viewers (millions)")
    ).properties(title="Distribution of Viewers by Weekday", width=w, height=h)

    return alt.vconcat(bar, box).resolve_scale(
        x='shared'
    )

def chart_outlier(w, h_bar):
    bar = alt.Chart(outliers_df).mark_bar(
        color="darkorange",
        opacity=0.5
    ).encode(
        x=x_season,
        y=alt.Y("count():Q", title="Outlier Episodes"),
    ).properties(title="Outlier Episodes Count per Season", width=w, height=h_bar)
    return bar

st.title("The Simpsons — Visual Analysis")
with st.sidebar:
    st.header("About")
    st.markdown(
        """
        **The Simpsons — Visual Analysis**  

        ---

        **Author**  
        - Lluís Mompó Ruiz

        ---

        *Universitat Politècnica de Catalunya*  
        *2025*
        """
    )

final = (
    alt.vconcat(
        alt.hconcat(
            chart_average_rating(400, 250),
            chart_average_season(500, 250),
            chart_scatter(400, 250)
        ).resolve_scale(color="independent", size="independent"),
        alt.hconcat(
            chart_heatmap(700, 500),
            chart_weekday(300, 180),
            chart_outlier(250, 200)
        ).resolve_scale(color="independent"),
    ).resolve_scale(color="independent")
    .configure_view(stroke=None)
    .configure_axis(labelFontSize=9, titleFontSize=10)
    .configure_title(fontSize=11)
)

st.altair_chart(final, width="content")