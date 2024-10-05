from typing import TYPE_CHECKING

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import streamlit as st

from webapp.helpers import switch_page

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator


def render_metric(
    column: "DeltaGenerator", title, value, title_color="#262730", value_color="#262730"
):
    column.markdown(
        f"""
        <div style="text-align:center;">
            <div style="font-size:16px; color:{title_color};">{title}</div>
            <div style="font-size:36px; color:{value_color};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def prepare_data_for_stacked_bar_chart(df: pd.DataFrame):
    df = df.copy()
    df.index = pd.to_datetime(df["date"])
    df["Bank"] = df["bank"]
    df["Income"] = df["amount"].apply(lambda x: x if x > 0 else 0)
    df["Expenses"] = df["amount"].apply(lambda x: abs(x) if x < 0 else 0)
    df = df.drop(columns=["description", "date"])
    df = df.resample("MS").sum()
    return df

def prepare_heatmap_data(df: pd.DataFrame):
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.groupby('date').agg({'amount': 'sum'}).reset_index()
    df = df.sort_values('date')
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    df['week'] = df['date'].dt.isocalendar().week
    df['day'] = df['date'].dt.dayofweek
    print(df)
    return df

def create_custom_colorscale(min_val, max_val):
    # Helper function to normalize values
    def normalize(x):
        return (x - min_val) / (max_val - min_val)

    custom_colorscale = [
        [normalize(-1000), 'rgb(139,0,0)'],    # Dark red
        [normalize(-100), 'rgb(255,0,0)'],     # Medium red
        [normalize(-10), 'rgb(255,200,200)'],  # Light red
        [normalize(0), 'rgb(255,255,255)'],    # White
        [normalize(10), 'rgb(200,255,200)'],   # Light green
        [normalize(100), 'rgb(0,255,0)'],      # Medium green
        [normalize(1000), 'rgb(0,100,0)']      # Dark green
    ]
    return custom_colorscale

def show_monthly_heatmaps(df: pd.DataFrame):
    all_days = pd.date_range(start=f"{df['year'].min()}-01-01", end=f"{df['year'].max()}-12-31", freq='D')
    all_days_df = pd.DataFrame({'date': all_days})
    all_days_df['year'] = all_days_df['date'].dt.year
    all_days_df['month'] = all_days_df['date'].dt.month
    all_days_df['day'] = all_days_df['date'].dt.dayofweek
    all_days_df['week'] = all_days_df['date'].dt.isocalendar().week
    all_days_df['amount'] = 0

    # merge with original data
    df = pd.merge(all_days_df, df, on=['date', 'year', 'month', 'day', 'week'], how='left', suffixes=('_all', '_orig'))
    df['amount'] = df['amount_orig'].fillna(df['amount_all'])
    df = df.drop(['amount_all', 'amount_orig'], axis=1)
    print(df[(df['month'] == 9)])

    years = sorted(df['year'].unique())
    months = range(1, 13)  # Assuming all months are present
    
    # create subplot for each month
    fig = make_subplots(
        rows=len(years), 
        cols=len(months), 
        subplot_titles=[f"{year}-{month:02d}" for year in years for month in months],
        vertical_spacing=0.05,
        horizontal_spacing=0.01
    )

    min_val = -1000
    max_val = 1000
    custom_colorscale = create_custom_colorscale(min_val, max_val)

    for i, year in enumerate(years, start=1):
        for j, month in enumerate(months, start=1):
            month_data = df[(df['year'] == year) & (df['month'] == month)]
            pivot_df = month_data.pivot(index='week', columns='day', values='amount').sort_index(ascending=False)
            pivot_df = pivot_df.reindex(columns=range(7), fill_value=0)

            heatmap = go.Heatmap(
                z=pivot_df.values,
                x=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                y=[f'Week {week}' for week in pivot_df.index],
                colorscale=custom_colorscale,
                zmin=min_val,
                zmax=max_val,
                xgap=1,
                ygap=1
            )
            
            fig.add_trace(heatmap, row=i, col=j)
            
            fig.update_xaxes(title_text='Day of Week', row=i, col=j)
            fig.update_yaxes(title_text='', row=i, col=j, showticklabels=False, showgrid=False)
            fig.update_yaxes(scaleanchor="x", scaleratio=1, row=i, col=j)


    fig.update_layout(
        height=300,
        width=300,
        title_text="Monthly Heatmaps",
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_stacked_bar_chart(df: pd.DataFrame):
    income_trace = go.Bar(
        x=df.index,
        y=df["Income"],
        name="Income",
        marker=dict(color="#00CEAA", cornerradius=10),
        hovertext=[f"${s:,.2f}" for s in df["Income"]],
        hoverinfo="text+name",
        offsetgroup=0,
    )

    expenses_trace = go.Bar(
        x=df.index,
        y=[-expense for expense in df["Expenses"]],
        name="Expenses",
        marker=dict(color="#F63366", cornerradius=10),
        hovertext=[f"${s:,.2f}" for s in df["Expenses"]],
        hoverinfo="text+name",
        offsetgroup=0,
    )

    savings_trace = go.Scatter(
        x=df.index,
        y=df["Income"] - df["Expenses"],
        name="Savings",
        mode="lines",
        line=dict(color="black", width=4),
        hoverinfo="text+name",
        text=[f"${s:,.2f}" for s in df["amount"]],
    )

    layout = go.Layout(
        title="Cash Flow",
        title_font=dict(size=26),
        xaxis=dict(title="Month", showgrid=False, dtick="M1"),
        yaxis=dict(
            title="Amount",
            showgrid=False,
            zeroline=True,
            zerolinecolor="#EFEFEF",
            zerolinewidth=2,
            tickformat="$,.1s",
        ),
        barmode="relative",
        hovermode="x unified",
        bargap=0.5,
        showlegend=False,
    )

    fig = go.Figure(data=[income_trace, expenses_trace, savings_trace], layout=layout)
    chart = st.plotly_chart(fig, use_container_width=True)

    total_income = round(df["Income"].sum())
    total_expenses = round(df["Expenses"].sum())
    total_savings = round(df["amount"].sum())
    if total_income > 0:  # Avoid division by zero
        savings_rate = (total_savings / total_income) * 100
    else:
        savings_rate = 0  # Handle case where income is zero

    formatted_savings_rate = f"{savings_rate:.2f}%"
    formatted_total_savings = f"${total_savings:,.0f}"
    if total_savings < 0:
        formatted_total_savings = f"-${abs(total_savings):,}"
    else:
        formatted_total_savings = f"${total_savings:,}"

    col1, col2, col3, col4 = st.columns(4)

    if chart:
        render_metric(col1, "Income", f"${total_income:,}", value_color="#00CEAA")
        render_metric(col2, "Expenses", f"${total_expenses:,}", value_color="#F63366")
        render_metric(col3, "Total Savings", formatted_total_savings)
        render_metric(col4, "Savings Rate", formatted_savings_rate)


st.markdown("# Visualizations")

if "df" in st.session_state.keys():
    show_stacked_bar_chart(prepare_data_for_stacked_bar_chart(st.session_state["df"]))
    show_monthly_heatmaps(prepare_heatmap_data(st.session_state["df"]))

if "df" not in st.session_state.keys():
    switch_page_button = st.button("Convert a bank statement")
    if switch_page_button:
        switch_page("app")
