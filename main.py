import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

# Configure the Streamlit page layout and title
st.set_page_config(page_title="Simple Finance App", page_icon=":money_with_wings:", layout="wide")

# File name for storing categories
category_file = "categories.json"

# Initialize default categories in session state
if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": []
    }

# Load saved categories from file if it exists
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

# Save current categories to the JSON file
def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

# Categorize transactions based on keywords in the "Details" field
def categorize_transaction(df):
    df["Category"] = "Uncategorized"  # Default to Uncategorized

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        # Convert all keywords to lowercase for case-insensitive matching
        lowered_keywords = [keyword.lower() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category  # Assign category if matched

    df["Category"] = df["Category"].astype(str)  # Ensure all are strings
    return df

# Load and parse the uploaded CSV file
def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns]  # Strip spaces from column names
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)  # Clean and convert amount
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y", errors='coerce')  # Parse date

        return categorize_transaction(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

# Add a keyword to a category and save the updated category list
def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

# Main application logic
def main():
    st.title("Simple Finance Dashboard")

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

        if df is not None:
            # Separate debit and credit transactions
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()

            # Save debits to session state for editing
            st.session_state.debits_df = debits_df.copy()

            # Create two tabs: one for expenses, one for payments
            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])

            with tab1:
                # Input to add new category
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()  # Refresh app to update dropdown

                st.subheader("Your Expenses")

                # Clean invalid categories before showing editor
                valid_categories = list(st.session_state.categories.keys())
                st.session_state.debits_df["Category"] = st.session_state.debits_df["Category"].apply(
                    lambda x: x if x in valid_categories else "Uncategorized"
                )

                # Editable table for managing transaction categories
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=valid_categories,
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )

                # Apply changes from editor and update keywords
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

                # Expense summary table
                st.subheader("Expenses Summary")
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values(by="Amount", ascending=False)

                st.dataframe(
                    category_totals,
                    column_config={
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")
                    },
                    use_container_width=True,
                    hide_index=True
                )

                # Pie chart visualization
                fig = px.pie(
                    category_totals,
                    values="Amount",
                    names="Category",
                    title="Expenses by Category"
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                # Summary of credit transactions
                st.subheader("Payment Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} AED")
                st.write(credits_df)

# Run the app
main()
