from pathlib import Path

import streamlit as st
import pandas as pd
import altair as alt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

st.set_page_config(page_title="Simpsons Dashboard", layout="wide")

stopwords = {
    "the","a","an","i","you","he","she","it","we","they","is","was","to","of","and","in","that","my","me","do","not","on","be","no", "youve", "ill", 
    "im","its","this","have","are","at","for","but","so","what","his","her","your","just","dont","thats","were","with","all","oh","yeah", "weve", "ive",   
    "like", "get", "got", "know", "well", "gonna", "hey", "uh", "um", "right", "one", "go", "good", "see", "think", "look", "come", "say", "youre", "theyre", 
    "now", "up", "out", "about", "who", "as", "if", "how", "from", "can","cant", "wont", "didnt", "isnt", "arent", "wouldnt", "couldnt", "youd", "shouldnt"
}

@st.cache_data
def load_data():

    df1 = pd.read_csv(DATA_DIR / "simpsons-script-lines-clean.csv")
    df1 = df1.sort_values(by="id")
    df2 = pd.read_csv(DATA_DIR / "simpsons-episodes-clean.csv")
    df2 = df2.sort_values(by="ID")
    df = df1.merge(df2,left_on="episode_id",right_on="ID",how="left")
    df = df.drop(columns=["ID", "raw_text", "speaking_line","spoken_words", "Rating", "Votes", "Date", "Weekday", "Viewers", "character_id", "episode_id"])
    df = df.dropna()

    return df

def character_dashboard(df, width=800, height=400):
    alt.data_transformers.disable_max_rows()
    df_word_counts = df.groupby("raw_character_text")["word_count"].sum().reset_index().sort_values("word_count", ascending=False)[:20]
    top20_chars = df_word_counts["raw_character_text"].tolist()
    
    df_sentences = df[df["raw_character_text"].isin(top20_chars)].dropna(subset=["normalized_text"]).query("normalized_text != ''"
        ).groupby(["raw_character_text", "normalized_text"]).size().reset_index(name="count").rename(columns={"normalized_text": "sentence"})
    df_sentences["display_sentence"] = df_sentences["sentence"].str[:50] + "..."
    df_char_sentences = df_sentences.groupby("raw_character_text")["count"].sum().reset_index(name="total_sentences")
    
    df_char_season = df[df["raw_character_text"].isin(top20_chars)].groupby(["raw_character_text", "Season"])["word_count"
        ].sum().reset_index(name="word_count")
        
    df_words_by_char = df[df["raw_character_text"].isin(top20_chars)].assign(word=lambda x: x["normalized_text"].str.lower().str.split()).explode("word"
        ).assign(word=lambda x: x["word"].str.replace(r"[^\w]", "", regex=True)).query("word != ''").loc[lambda x: ~x["word"].isin(stopwords)
        ].groupby(["raw_character_text", "word"]).size().reset_index(name="count")
        
    df_bar = pd.concat([df_word_counts[["raw_character_text", "word_count"]].rename(columns={"word_count": "value"}).assign(type="Words"),
            df_char_sentences[["raw_character_text", "total_sentences"]].rename(columns={"total_sentences": "value"}
            ).assign(type="Sentences")], ignore_index=True)
            
    df_lollipop = pd.concat([
        df_words_by_char.rename(columns={"word": "item"}).assign(type="Words")[["raw_character_text", "item", "count", "type"]],
        df_sentences.assign(item=lambda x: x["sentence"].str[:50]).assign(type="Sentences")[["raw_character_text", "item", "count", "type"]]
        ], ignore_index=True)
    # The chart only ever shows the top 20 items of one character, so ship only those
    # (cuts the embedded spec from tens of MB to a few MB without changing the visuals).
    df_lollipop = (df_lollipop.sort_values("count", ascending=False)
                   .groupby(["raw_character_text", "type"]).head(20))

    select_point = alt.selection_point(fields=["raw_character_text"], empty=False, value=top20_chars[0])
    mode_select = alt.param(name="Mode", bind=alt.binding_radio(options=["Words", "Sentences"], name="Display: "), value="Words")
    select_labels = alt.selection_point(on='mouseover', nearest=True, empty=False)
    select_lollipop = alt.selection_point(fields=["item"], empty=False)

    # Bars
    words_max = int(df_word_counts["word_count"].max() * 1.1) 
    sentences_max = 30000
    words_lollipop_max = 2000
    sentences_lollipop_max = 140
    
    bars = alt.Chart(df_bar).mark_bar().encode(
        x=alt.X("raw_character_text:N", sort="-y", title="Character", axis=alt.Axis(labelAngle=-45, labelOverlap=False, labelFontSize=9)),
        y=alt.Y("value:Q", title="Count", scale=alt.Scale(domainMin=0, domainMax={"expr": f"Mode == 'Words' ? {words_max} : {sentences_max}"})),
        color=alt.condition(select_point, alt.value("#f07000"), alt.value("#0094f0")),
        tooltip=[alt.Tooltip("raw_character_text:N", title="Character"),alt.Tooltip("value:Q", format=",", title="Count")]
        ).transform_filter("datum.type == Mode").add_params(select_point, mode_select)

    bar_labels = alt.Chart(df_bar).mark_text(dy=-6, fontSize=8).encode(
        x=alt.X("raw_character_text:N", sort="-y"),
        y=alt.Y("value:Q"),
        text=alt.condition(select_point, alt.Text("value:Q", format=","), alt.value(""))
        ).transform_filter("datum.type == Mode").add_params(select_point)

    detail = (bars + bar_labels).properties(width=int(width*2/5), height=int(height/2),
        title=alt.TitleParams({"expr": "Mode == 'Words' ? "
        "'Top 20 Characters by Total Word Count' : "
        "'Top 20 Characters by Total Sentence Count'"},
        subtitle="Select Words/Sentences in the display button below · Click a bar to explore a character"))

    # Lollipops
    def make_lollipop_layer(mark):
        return alt.Chart(df_lollipop).encode(
            y=alt.Y("sum_count:Q", title="Count", scale=alt.Scale(domainMin=0, domainMax={"expr": f"Mode == 'Words' ? {words_lollipop_max} : {sentences_lollipop_max}"})),
            x=alt.X("item:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-25, labelOverlap=False, labelFontSize=9)),
            tooltip=[alt.Tooltip("item:N", title="Item"),alt.Tooltip("sum_count:Q", title="Count")]
        ).transform_filter("datum.type == Mode").transform_filter(select_point
        ).transform_aggregate(sum_count="sum(count)", groupby=["item"]
        ).transform_window(rank="row_number()", sort=[alt.SortField("sum_count", order="descending")]
        ).transform_filter("datum.rank <= 20")

    lollipop_bars   = make_lollipop_layer(None).mark_bar(color="#f07000", width=2)
    lollipop_dots   = make_lollipop_layer(None).mark_point(color="#f07000", size=100, filled=True).add_params(select_lollipop)
    lollipop_labels = make_lollipop_layer(None).mark_text(dy=-14, fontSize=10).encode(
        text=alt.condition(select_lollipop, alt.Text("sum_count:Q"), alt.value("")))
        
    lollipop = (lollipop_bars + lollipop_dots + lollipop_labels).properties(width=int(width*2/5), height=int(height/2),
        title=alt.TitleParams({"expr": "Mode == 'Words' ? "
        "'Most Frequent Words of the Selected Character' : "
        "'Most Frequent Sentences of the Selected Character'"},
        subtitle="Select a lollipop to see the count"))   

    # Lines
    season_domain = [df_char_season["Season"].min(), df_char_season["Season"].max()]
    count_rule = alt.Chart(df_char_season).mark_rule(opacity=0).encode(
        x=alt.X("Season:Q", scale=alt.Scale(domain=season_domain))
        ).add_params(select_labels).transform_filter(select_point)

    line = alt.Chart(df_char_season).mark_line(color="#f07000", point=alt.OverlayMarkDef(color="#f07000", size=80, filled=True)).encode(
        x=alt.X("Season:Q", title="Season", axis=alt.Axis(labelAngle=0), scale=alt.Scale(domain=season_domain)),
        y=alt.Y("word_count:Q", title="Count", scale=alt.Scale(domain=[0, 16000])),
        ).transform_filter(select_point)

    season_labels = alt.Chart(df_char_season).mark_text(dy=-10).encode(
        x=alt.X("Season:Q", scale=alt.Scale(domain=season_domain)),
        y=alt.Y("word_count:Q"),
        text=alt.condition(select_labels, alt.Text("word_count:Q", format=","), alt.value(""))
        ).transform_filter(select_point)

    chart = (line + season_labels + count_rule).properties(
        width=(width*3/5), height=int(2*height),
        title=alt.TitleParams(
            "Evolution of Character Word Counts Across Seasons",
            subtitle="Hover to display word count per season"))
    
    return alt.hconcat(alt.vconcat(detail, lollipop, spacing=10), chart)


def episode_comparison(df, width=900, height=400):
    df_word_counts = df.groupby("raw_character_text")["word_count"].sum().reset_index().sort_values("word_count", ascending=False)[:20]
    top20_chars = df_word_counts["raw_character_text"].tolist()
    alt.data_transformers.disable_max_rows()
    
    df_words_episode = df[df["raw_character_text"].isin(top20_chars)].assign(word=lambda x: x["normalized_text"].str.lower().str.split()
        ).explode("word").assign(word=lambda x: x["word"].str.replace(r"[^\w]", "", regex=True)).query("word != ''").loc[lambda x: ~x["word"].isin(stopwords)
        ].groupby(["raw_character_text", "Season", "word", "Number_season"]).size().reset_index(name="count")
    # Only the top 20 words per character and episode are ever drawn
    df_words_episode = (df_words_episode.sort_values("count", ascending=False)
                        .groupby(["raw_character_text", "Season", "Number_season"]).head(20))

    seasons = sorted(df_words_episode["Season"].unique().tolist())
    episodes = sorted(df_words_episode["Number_season"].unique().tolist())
    
    char_a_select = alt.param(name="Char_A", bind=alt.binding_select(options=top20_chars, name="Character A: "), value=top20_chars[0])
    char_b_select = alt.param(name="Char_B",bind=alt.binding_select(options=top20_chars, name="Character B: "), value=top20_chars[1])
    season_select = alt.param(name="Season", bind=alt.binding_select(options=seasons, name="Season: "), value=seasons[0])
    episode_select = alt.param(name="Episode", bind=alt.binding_select(options=episodes, name="Episode: "), value=episodes[0])

    bars = alt.Chart(df_words_episode).mark_bar().encode(
        y=alt.Y("word:N", sort=alt.EncodingSortField(field="count", op="max", order="descending"), title="Word", axis=alt.Axis(labelOverlap=False, labelFontSize=8)),
        x=alt.X("signed_count:Q", title="Word count of character A | Word count of Character B", scale=alt.Scale(domain=[-33,33]),axis=alt.Axis(labelExpr="abs(datum.value)")),
        color=alt.Color("raw_character_text:N", legend=alt.Legend(title="Character"), scale=alt.Scale(range=["#A0BCDB", "#A177BE"])),
        tooltip=[ alt.Tooltip("raw_character_text:N", title="Character"), alt.Tooltip("word:N", title="Word"), alt.Tooltip("count:Q", title="Count")]
        ).add_params(char_a_select, char_b_select, season_select, episode_select
        ).transform_filter("datum.raw_character_text == Char_A || datum.raw_character_text == Char_B"
        ).transform_filter("datum.Season == Season").transform_filter("datum.Number_season == Episode"
        ).transform_window(rank="row_number()", sort=[alt.SortField("count", order="descending")], groupby=["raw_character_text"]
        ).transform_filter("datum.rank <= 20").transform_calculate(signed_count="datum.raw_character_text == Char_A ? -datum.count : datum.count")

    labels_a = alt.Chart(df_words_episode).mark_text(align='right', dx=-4, fontSize=9, fontWeight="bold").encode(
        y=alt.Y("word:N", sort=alt.EncodingSortField(field="count", op="max", order="descending")), 
        x=alt.X("signed_count:Q"),
        text=alt.Text("count:Q"), 
        color=alt.Color("raw_character_text:N", legend=None)
        ).transform_filter("datum.raw_character_text == Char_A").transform_filter("datum.Season == Season"
        ).transform_filter("datum.Number_season == Episode" 
        ).transform_window(rank="row_number()", sort=[alt.SortField("count", order="descending")], groupby=["raw_character_text"]
        ).transform_filter("datum.rank <= 20").transform_calculate(signed_count="-datum.count")

    labels_b = alt.Chart(df_words_episode).mark_text(align='left', dx=4, fontSize=9, fontWeight="bold").encode(
        y=alt.Y("word:N", sort=alt.EncodingSortField(field="count", op="max", order="descending")),
        x=alt.X("signed_count:Q"),
        text=alt.Text("count:Q"), 
        color=alt.Color("raw_character_text:N", legend=None)
        ).transform_filter("datum.raw_character_text == Char_B" ).transform_filter("datum.Season == Season"
        ).transform_filter("datum.Number_season == Episode" 
        ).transform_window(rank="row_number()", sort=[alt.SortField("count", order="descending")], groupby=["raw_character_text"]
        ).transform_filter("datum.rank <= 20").transform_calculate(signed_count="datum.count")

    zero_line = alt.Chart(pd.DataFrame({'x': [0]})).mark_rule(color='black', strokeWidth=1).encode(x='x')

    final_chart_4 = (zero_line + bars + labels_a + labels_b).properties(
        width=width, height=height,
        title=alt.TitleParams("Contrasting Character Vocabularies Per Episode",
        subtitle="Select an episode and a season and compare the most frequent words of the two characters")
    )
    return final_chart_4

def season_comparison(df, width=900, height=400):
    alt.data_transformers.disable_max_rows()
    df_word_counts = df.groupby("raw_character_text")["word_count"].sum().reset_index().sort_values("word_count", ascending=False)[:20]
    top20_chars = df_word_counts["raw_character_text"].tolist()
    
    df_episode_totals = df[df["raw_character_text"].isin(top20_chars)].groupby(["raw_character_text", "Season", "Number_season"])["word_count"].sum().reset_index(name="total_words")
    background_df = df_episode_totals[["Season"]].drop_duplicates()
    seasons = sorted(df_episode_totals["Season"].unique().tolist())
    
    char_a_select = alt.param(name="Char_A", bind=alt.binding_select(options=top20_chars, name="Character A: "), value=top20_chars[0])
    char_b_select = alt.param(name="Char_B",bind=alt.binding_select(options=top20_chars, name="Character B: "), value=top20_chars[1])
    season_select = alt.param(name="Season", bind=alt.binding_select(options=seasons, name="Season: "), value=seasons[0])

    hover = alt.selection_point(fields=["Number_season"], nearest=True, on="mouseover", empty=False)

    background = alt.Chart(background_df).mark_text(
        baseline='middle', fontSize=96, opacity=0.2
        ).encode(text='Season:O').transform_filter("datum.Season == Season")

    line = alt.Chart(df_episode_totals).mark_line(point=True).transform_filter("datum.raw_character_text == Char_A || datum.raw_character_text == Char_B"
        ).transform_filter("datum.Season == Season").encode(
        x=alt.X("Number_season:Q", title="Episode", axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("total_words:Q", title="Word Count", scale=alt.Scale(domain=[0, 1400])),
        color=alt.Color("raw_character_text:N", legend=alt.Legend(title="Character"), scale=alt.Scale(range=["#A0BCDB", "#A177BE"])),
        tooltip=[alt.Tooltip("raw_character_text:N", title="Character"), alt.Tooltip("total_words:Q", title="Count")])

    selectors = alt.Chart(df_episode_totals).mark_point(size=200, opacity=0
        ).add_params(char_a_select, char_b_select, season_select, hover
        ).transform_filter("datum.raw_character_text == Char_A || datum.raw_character_text == Char_B"
        ).transform_filter("datum.Season == Season").encode(
        x=alt.X("Number_season:Q"),
        y=alt.Y("total_words:Q"),
        color=alt.Color("raw_character_text:N"))

    labels = alt.Chart(df_episode_totals).mark_text(align='left', dx=15, dy=-15, fontWeight='bold'
        ).transform_filter("datum.raw_character_text == Char_A || datum.raw_character_text == Char_B"
        ).transform_filter("datum.Season == Season").encode(
        x=alt.X("Number_season:Q"),
        y=alt.Y("total_words:Q"),
        color=alt.Color("raw_character_text:N", legend=None),
        text=alt.condition(hover, alt.Text("total_words:Q"), alt.value(" ")))

    rules = alt.Chart(df_episode_totals).mark_rule(color='gray', strokeDash=[4, 4]
        ).transform_filter("datum.raw_character_text == Char_A || datum.raw_character_text == Char_B"
        ).transform_filter("datum.Season == Season").transform_filter(hover).encode(
        x=alt.X("Number_season:Q"))

    chart = (line + selectors + labels + rules + background).properties(
        width=width, height=height,
        title=alt.TitleParams(
        "Episode-by-Episode Evolution of Character Word Counts",
        subtitle="Select two characters, a season below and hover over the points to display word counts"))

    return chart

def main():

    st.title("The Simpsons: Scripts Analysis Dashboard")
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

    df = load_data()

    final_vis = alt.vconcat(
        character_dashboard(df, width=1200, height=180),
        alt.hconcat(
            season_comparison(df, width=600, height=280), 
            episode_comparison(df, width=600, height=280)
        )).configure_view(stroke=None).configure_axis(grid=True
        ).resolve_scale(color='independent').configure_legend(orient="bottom")

    st.altair_chart(final_vis, width='content')

if __name__ == "__main__":
    main()