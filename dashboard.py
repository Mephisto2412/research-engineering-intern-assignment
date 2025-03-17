import streamlit as st 
import pandas as pd
import plotly.express as px
from collections import Counter
import ast
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
from wordcloud import WordCloud
import matplotlib.pyplot as plt

nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()

# Load Data
df = pd.read_csv("final_df.csv")
df["created_utc"] = pd.to_datetime(df["created_utc"], errors="coerce")

# Clean Named Entities
def process_named_entities(named_entities):
    try:
        entities = ast.literal_eval(named_entities)
        return [ent for ent in entities if len(ent) > 2]  # Remove short words
    except:
        return []
df["cleaned_entities"] = df["named_entities"].apply(process_named_entities)

# Sentiment Analysis
df["sentiment_score"] = df["selftext"].fillna("").apply(lambda text: sia.polarity_scores(text)["compound"])
df["sentiment_label"] = df["sentiment_score"].apply(lambda score: "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral")

# Streamlit App Setup
st.set_page_config(page_title="Reddit Misinformation Dashboard", layout="wide")
st.title(" Reddit Misinformation & Trend Analysis Dashboard")

# Sidebar Filters
selected_subreddits = st.sidebar.multiselect("Select Subreddits:", options=df["subreddit"].unique(), default=["politics"])
date_range = st.sidebar.date_input("Select Date Range:", [df["created_utc"].min(), df["created_utc"].max()])
search_query = st.sidebar.text_input("Search posts:", "")

# Apply Filters
filtered_df = df[df["subreddit"].isin(selected_subreddits)]
filtered_df = filtered_df[(filtered_df["created_utc"] >= pd.to_datetime(date_range[0])) & (filtered_df["created_utc"] <= pd.to_datetime(date_range[1]))]
if search_query:
    filtered_df = filtered_df[filtered_df["selftext"].str.contains(search_query, case=False, na=False)]

# Create a tabbed layout to make the UI more interactive
tabs = st.tabs(["Misinformation Analysis", "Subreddit Engagement", "Topic Analysis", "Sentiment Analysis"])

#  Misinformation Analysis
tabs[0].subheader("Misinformation Trends")
misinfo_counts = filtered_df.groupby(["subreddit", "misinformation_label"]).size().reset_index(name="count")
fig_misinfo = px.bar(misinfo_counts, x="subreddit", y="count", color="misinformation_label", barmode="group", title="Misinformation Trends by Subreddit")
tabs[0].plotly_chart(fig_misinfo)


# Aggregate mean engagement metrics per misinformation label
engagement_metrics = filtered_df.groupby("misinformation_label")[["num_comments", "ups"]].mean().reset_index()

# Bar chart for engagement comparison
fig_engagement = px.bar(
    engagement_metrics,
    x="misinformation_label",
    y=["num_comments", "ups"],
    barmode="group",
    title="Engagement Metrics Across Misinformation Labels",
    labels={"value": "Average Engagement", "variable": "Engagement Type"}
)

tabs[0].plotly_chart(fig_engagement)


#  Subreddit Engagement
tabs[1].subheader("Subreddit Activity & User Engagement")
engagement = filtered_df.groupby("subreddit").agg({"num_comments": "sum", "ups": "sum"}).reset_index()
fig_activity = px.bar(engagement, x="subreddit", y=["num_comments", "ups"], title="Subreddit Activity: Comments & Upvotes")
tabs[1].plotly_chart(fig_activity)

author_counts = filtered_df.groupby("subreddit")["author"].nunique().reset_index()
fig_authors = px.bar(author_counts, x="subreddit", y="author", title="Unique Authors per Subreddit")
tabs[1].plotly_chart(fig_authors)

# Adding User Activity here
tabs[1].subheader("Top Users Analysis")
top_users = filtered_df["author"].value_counts().reset_index()
top_users.columns = ["author", "post_count"]
fig_users = px.bar(top_users.head(min(10, len(top_users))), x="author", y="post_count", title="Most Active Users")
tabs[1].plotly_chart(fig_users)

#  Topic Analysis
# Count the number of posts for each topic
topic_counts = filtered_df["dominant_topic"].value_counts().reset_index()
topic_counts.columns = ["Topic", "Count"]
# Mapping Topic Labels
topic_labels  = {
    0: "Art, Social Movements & Radical Politics",
    1: "Global Politics & Business",
    2: "US Political Discussions",
    3: "Online News & Video Content",
    4: "Anarchism, Socialism & Ideological Debates"
}
topic_counts["Topic"] = topic_counts["Topic"].map(topic_labels)

tabs[2].subheader("Topic Distribution")
# Create a pie chart
fig_topic_pie = px.pie(
    topic_counts, 
    names="Topic", 
    values="Count", 
    title="Distribution of Posts by Topic", 
    color_discrete_sequence=px.colors.qualitative.Set3
)

# Display the pie chart
tabs[2].plotly_chart(fig_topic_pie)


tabs[2].write("### Top Named Entities:")
# Flatten the list of named entities
all_entities = [ent for entities in filtered_df["cleaned_entities"] for ent in entities]

# Generate word frequency dictionary
entity_counts = Counter(all_entities)
wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(entity_counts)

# Display the word cloud
fig, ax = plt.subplots(figsize=(10, 5))
ax.imshow(wordcloud, interpolation="bilinear")
ax.axis("off")  # Hide axes

# Show the word cloud in Streamlit
tabs[2].pyplot(fig)

#  Sentiment Analysis
tabs[3].subheader("Sentiment Trends")
sentiment_counts = filtered_df.groupby(["subreddit", "sentiment_label"]).size().reset_index(name="count")
fig_sentiment = px.bar(sentiment_counts, x="subreddit", y="count", color="sentiment_label", barmode="group", title="Sentiment Distribution by Subreddit")
tabs[3].plotly_chart(fig_sentiment)

# Aggregate sentiment counts per week
filtered_df["week"] = filtered_df["created_utc"].dt.to_period("W").astype(str)
sentiment_trend = filtered_df.groupby(["week", "sentiment_label"]).size().reset_index(name="count")

# Stacked Area Chart for better visualization
fig_sentiment_trend = px.area(
    sentiment_trend, 
    x="week", 
    y="count", 
    color="sentiment_label", 
    title="Sentiment Trends Over Time (Aggregated Weekly)",
    labels={"week": "Week", "count": "Number of Posts"},
    color_discrete_map={"Positive": "green", "Negative": "red", "Neutral": "gray"}
)

# Display updated visualization
tabs[3].plotly_chart(fig_sentiment_trend)

#  Summary & Insights
st.sidebar.write("### Summary & Insights")
st.sidebar.write("- **Misinformation trends** vary significantly across subreddits.")
st.sidebar.write("- **Engagement levels** help identify how misinformation spreads.")
st.sidebar.write("- **Topic Trends** show key discussion topics and figures.")
st.sidebar.write("- **Sentiment analysis** helps understand public opinion trends.")
