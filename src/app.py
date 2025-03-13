import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
import sqlite3
import os
from db_utils import (
    get_db_connection, create_user, verify_user,
    add_transaction, get_transactions, set_budget, get_budgets,
    create_shopping_list, get_shopping_lists, add_list_item,
    get_list_items, update_item_status, delete_shopping_list,
    get_budget_categories, get_budget_summary, delete_budget,
    add_family_member, get_family_members, update_family_member,
    delete_family_member, get_relationship_types,
    add_event, get_events, update_event, delete_event,
    get_upcoming_events, get_events_by_month, get_event_categories,
    add_goal, get_goals, update_goal, delete_goal,
    get_goal_categories, get_goal_status_types,
    add_goal_milestone, get_goal_milestones,
    update_milestone_status, delete_milestone,
    update_user_profile, get_user_data, import_user_data, delete_user_data
)
from models import create_tables
from init_db import init_database

# Set page configuration
st.set_page_config(
    page_title="Family Planner",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/jithin-data-analysis/family-planner',
        'Report a bug': "https://github.com/jithin-data-analysis/family-planner/issues",
        'About': """
        # Family Planner
        A comprehensive family management application that helps you:
        - Track finances and budgets
        - Manage family events and schedules
        - Set and track goals
        - Organize shopping lists
        - Maintain family profiles
        """
    }
)

# Custom CSS for modern UI
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-1px);
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .stExpander {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .stSelectbox {
        background-color: white;
        border-radius: 4px;
        padding: 0.5rem;
    }
    .stTextInput>div>div>input {
        background-color: white;
        border-radius: 4px;
        padding: 0.5rem;
    }
    .stTextArea>div>div>textarea {
        background-color: white;
        border-radius: 4px;
        padding: 0.5rem;
    }
    .stProgress .st-bo {
        background-color: #e0e0e0;
        border-radius: 10px;
    }
    .stProgress .st-bo > div {
        background-color: #4CAF50;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# Initialize database on startup
init_database()

def show_login():
    """Display login form"""
    # Add a welcoming header
    st.markdown("""
        <div style='text-align: center; margin-bottom: 2rem;'>
            <h1 style='color: #4CAF50;'>👨‍👩‍👧‍👦 Family Planner</h1>
            <p style='color: #666; font-size: 1.2rem;'>Your personal family management assistant</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Create a centered container for the login/register forms
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Add tabs for login and registration
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.markdown("""
                <div style='background-color: white; padding: 2rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <h2 style='color: #4CAF50; margin-bottom: 1.5rem;'>Welcome Back!</h2>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    user = verify_user(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user['id']
                        st.success("Login successful! Welcome back!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tab2:
            st.markdown("""
                <div style='background-color: white; padding: 2rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <h2 style='color: #4CAF50; margin-bottom: 1.5rem;'>Create Account</h2>
            """, unsafe_allow_html=True)
            
            with st.form("register_form"):
                new_username = st.text_input("Username", placeholder="Choose a username")
                new_email = st.text_input("Email", placeholder="Enter your email")
                new_password = st.text_input("Password", type="password", placeholder="Choose a password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                submit = st.form_submit_button("Register", use_container_width=True)
                
                if submit:
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        user_id = create_user(new_username, new_password, new_email)
                        if user_id:
                            st.success("Registration successful! Please login.")
                            st.rerun()
                        else:
                            st.error("Username or email already exists")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Add features section
        st.markdown("""
            <div style='margin-top: 2rem; text-align: center;'>
                <h3 style='color: #4CAF50;'>Features</h3>
                <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1rem;'>
                    <div style='background-color: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <h4 style='color: #4CAF50;'>💰 Finance</h4>
                        <p style='color: #666;'>Track expenses and manage budgets</p>
                    </div>
                    <div style='background-color: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <h4 style='color: #4CAF50;'>📅 Calendar</h4>
                        <p style='color: #666;'>Organize family events</p>
                    </div>
                    <div style='background-color: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <h4 style='color: #4CAF50;'>🎯 Goals</h4>
                        <p style='color: #666;'>Set and track family goals</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def show_home():
    """Display home dashboard"""
    # Welcome message with user's name
    st.markdown("""
        <div style='background-color: #4CAF50; color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='margin: 0;'>Welcome to Family Planner</h1>
            <p style='margin: 0.5rem 0 0; font-size: 1.2rem;'>Your personal family management assistant</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Quick Stats Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Get current month's transactions
        current_month = datetime.now().month
        current_year = datetime.now().year
        transactions = get_transactions(st.session_state.user_id)
        
        # Calculate total income and expenses
        income = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'income')
        expenses = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'expense')
        balance = income - expenses
        
        st.metric(
            label="Total Income",
            value=f"${income:,.2f}",
            delta=f"${income - expenses:,.2f}",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="Total Expenses",
            value=f"${expenses:,.2f}",
            delta=f"${expenses - income:,.2f}",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            label="Current Balance",
            value=f"${balance:,.2f}",
            delta=f"{'Positive' if balance >= 0 else 'Negative'}",
            delta_color="normal" if balance >= 0 else "inverse"
        )
    
    with col4:
        # Get upcoming events
        upcoming_events = get_upcoming_events(st.session_state.user_id, days=7)
        st.metric(
            label="Upcoming Events",
            value=str(len(upcoming_events)),
            delta="This Week"
        )
    
    # Main Content Area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Financial Overview")
        # Create a line chart for income vs expenses
        fig = go.Figure()
        
        # Add income line
        fig.add_trace(go.Scatter(
            y=[income],
            name="Income",
            line=dict(color='#4CAF50', width=2),
            mode='lines+markers'
        ))
        
        # Add expenses line
        fig.add_trace(go.Scatter(
            y=[expenses],
            name="Expenses",
            line=dict(color='#f44336', width=2),
            mode='lines+markers'
        ))
        
        fig.update_layout(
            title="Income vs Expenses",
            height=300,
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📅 Quick Actions")
        action_buttons = [
            ("Add Transaction", "Financial Dashboard"),
            ("Create Shopping List", "Shopping Lists"),
            ("Add Family Member", "Family Profiles"),
            ("Set New Goal", "Goals"),
            ("Add Event", "Calendar")
        ]
        
        for label, page in action_buttons:
            if st.button(label, use_container_width=True):
                st.session_state.page = page
                st.rerun()
    
    # Upcoming Events and Goals
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 Upcoming Events")
        if upcoming_events:
            for event in upcoming_events:
                st.markdown(f"""
                    <div style='background-color: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <h4 style='margin: 0;'>{event['title']}</h4>
                        <p style='margin: 0.5rem 0; color: #666;'>{event['description']}</p>
                        <p style='margin: 0; color: #4CAF50;'>📅 {event['start_date']}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No upcoming events for the next 7 days.")
    
    with col2:
        st.subheader("🎯 Active Goals")
        goals = get_goals(st.session_state.user_id, status="In Progress")
        if goals:
            for goal in goals:
                st.markdown(f"""
                    <div style='background-color: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <h4 style='margin: 0;'>{goal['title']}</h4>
                        <p style='margin: 0.5rem 0; color: #666;'>{goal['description']}</p>
                        <div style='margin: 0.5rem 0;'>
                            <div style='height: 8px; background-color: #e0e0e0; border-radius: 4px;'>
                                <div style='width: {goal['progress']}%; height: 100%; background-color: #4CAF50; border-radius: 4px;'></div>
                            </div>
                            <p style='margin: 0; text-align: right; color: #666;'>{goal['progress']}% Complete</p>
                        </div>
                        <p style='margin: 0; color: #4CAF50;'>🎯 Target: {goal['target_date']}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No active goals. Set your first goal to start tracking your progress!")

def show_financial_dashboard():
    """Display financial dashboard"""
    st.header("Financial Dashboard")
    
    # Add transaction form
    with st.expander("Add New Transaction"):
        with st.form("transaction_form"):
            amount = st.number_input("Amount", min_value=0.01, step=0.01)
            category = st.selectbox(
                "Category",
                ["Groceries", "Utilities", "Rent", "Entertainment", "Income", "Other"]
            )
            description = st.text_input("Description")
            transaction_type = st.selectbox(
                "Type",
                ["expense", "income"]
            )
            
            if st.form_submit_button("Add Transaction"):
                add_transaction(
                    st.session_state.user_id,
                    amount,
                    category,
                    description,
                    transaction_type
                )
                st.success("Transaction added successfully!")
    
    # Get transactions
    transactions = get_transactions(st.session_state.user_id)
    
    if transactions:
        # Create a DataFrame for analysis
        import pandas as pd
        df = pd.DataFrame(transactions)
        
        # Calculate key metrics
        total_income = df[df['transaction_type'] == 'income']['amount'].sum()
        total_expenses = df[df['transaction_type'] == 'expense']['amount'].sum()
        current_balance = total_income - total_expenses
        
        # Display metrics in a row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Income", f"${total_income:,.2f}")
        with col2:
            st.metric("Total Expenses", f"${total_expenses:,.2f}")
        with col3:
            st.metric("Current Balance", f"${current_balance:,.2f}")
        
        # AI-Powered Insights
        st.subheader("🤖 AI Insights")
        insights_container = st.container()
        
        # Analyze spending patterns
        expenses_by_category = df[df['transaction_type'] == 'expense'].groupby('category')['amount'].sum()
        top_categories = expenses_by_category.nlargest(3)
        
        with insights_container:
            st.markdown("""
                <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0;'>
                    <h4 style='color: #4CAF50;'>Spending Analysis</h4>
            """, unsafe_allow_html=True)
            
            # Generate insights based on spending patterns
            if len(top_categories) > 0:
                top_category = top_categories.index[0]
                top_amount = top_categories.values[0]
                st.markdown(f"""
                    - Your highest spending category is **{top_category}** (${top_amount:,.2f})
                    - This represents {top_amount/total_expenses*100:.1f}% of your total expenses
                """)
            
            # Savings rate analysis
            if total_income > 0:
                savings_rate = (total_income - total_expenses) / total_income * 100
                st.markdown(f"""
                    - Your current savings rate is **{savings_rate:.1f}%**
                    - {'This is good!' if savings_rate >= 20 else 'Consider increasing your savings rate'}
                """)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Expenses by category pie chart
            fig = px.pie(
                values=expenses_by_category.values,
                names=expenses_by_category.index,
                title="Expenses by Category"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Monthly trend line chart
            df['date'] = pd.to_datetime(df['date'])
            monthly_data = df.groupby(df['date'].dt.to_period('M')).agg({
                'amount': lambda x: x[df['transaction_type'] == 'income'].sum(),
                'amount': lambda x: x[df['transaction_type'] == 'expense'].sum()
            }).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=monthly_data['date'].astype(str),
                y=monthly_data['amount'],
                mode='lines+markers',
                name='Monthly Expenses'
            ))
            fig.update_layout(title="Monthly Expense Trend")
            st.plotly_chart(fig, use_container_width=True)
        
        # AI Recommendations
        st.subheader("💡 Smart Recommendations")
        recommendations = []
        
        # Analyze spending patterns and generate recommendations
        if total_expenses > 0:
            # Check for high spending in specific categories
            for category, amount in expenses_by_category.items():
                if amount / total_expenses > 0.3:  # If category represents more than 30% of expenses
                    recommendations.append(f"Consider reviewing your spending in the **{category}** category")
            
            # Check for savings rate
            if (total_income - total_expenses) / total_income < 0.2:
                recommendations.append("Your savings rate is below 20%. Consider reducing expenses or increasing income")
        
        if recommendations:
            for rec in recommendations:
                st.markdown(f"- {rec}")
        else:
            st.info("Your financial health looks good! Keep up the good work!")
        
        # Display transaction list
        st.subheader("Recent Transactions")
        for tx in transactions:
            with st.expander(f"{tx['date']} - {tx['description']} (${float(tx['amount']):,.2f})"):
                st.write(f"Category: {tx['category']}")
                st.write(f"Type: {tx['transaction_type']}")
    else:
        st.info("No transactions found. Add your first transaction above!")

def show_shopping_lists():
    """Display shopping lists interface"""
    st.header("📝 Shopping Lists")
    
    # Create new shopping list
    with st.expander("Create New Shopping List", expanded=True):
        with st.form("new_list_form"):
            list_name = st.text_input("List Name")
            submit = st.form_submit_button("Create List")
            if submit and list_name:
                create_shopping_list(st.session_state.user_id, list_name)
                st.success(f"Created new list: {list_name}")
                st.rerun()
    
    # Display existing lists
    shopping_lists = get_shopping_lists(st.session_state.user_id)
    
    if not shopping_lists:
        st.info("No shopping lists yet. Create your first list above!")
    else:
        for shopping_list in shopping_lists:
            with st.expander(f"📋 {shopping_list['name']} ({shopping_list['created_at']})"):
                # Add new item form
                with st.form(f"add_item_form_{shopping_list['id']}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        item_name = st.text_input("Item Name", key=f"item_name_{shopping_list['id']}")
                    with col2:
                        quantity = st.number_input("Quantity", min_value=1, value=1, key=f"quantity_{shopping_list['id']}")
                    submit = st.form_submit_button("Add Item")
                    if submit and item_name:
                        add_list_item(shopping_list['id'], item_name, quantity)
                        st.success(f"Added {item_name} to the list")
                        st.rerun()
                
                # Display items
                items = get_list_items(shopping_list['id'])
                if items:
                    for item in items:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"• {item['item_name']}")
                        with col2:
                            st.write(f"Qty: {item['quantity']}")
                        with col3:
                            if st.checkbox("Done", value=item['completed'], key=f"item_{item['id']}"):
                                update_item_status(item['id'], True)
                            else:
                                update_item_status(item['id'], False)
                else:
                    st.info("No items in this list yet")
                
                # Delete list button
                if st.button("Delete List", key=f"delete_{shopping_list['id']}"):
                    delete_shopping_list(shopping_list['id'])
                    st.success("List deleted")
                    st.rerun()

def show_budget_planning():
    """Display budget planning interface"""
    st.header("💰 Budget Planning")
    
    # Month and Year Selection
    col1, col2 = st.columns(2)
    with col1:
        current_month = datetime.now().month
        month = st.selectbox("Month", range(1, 13), index=current_month - 1,
                           format_func=lambda x: datetime(2024, x, 1).strftime("%B"))
    with col2:
        current_year = datetime.now().year
        year = st.selectbox("Year", range(current_year - 1, current_year + 2), index=1)
    
    # Add/Edit Budget Form
    with st.expander("Set Budget", expanded=True):
        with st.form("budget_form"):
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox("Category", get_budget_categories())
            with col2:
                amount = st.number_input("Budget Amount ($)", min_value=0.01, step=10.0)
            
            submit = st.form_submit_button("Set Budget")
            if submit:
                set_budget(st.session_state.user_id, category, amount, month, year)
                st.success(f"Budget set for {category}")
                st.rerun()
    
    # Display Budget Summary
    st.subheader(f"Budget Summary for {datetime(year, month, 1).strftime('%B %Y')}")
    
    # Get budget summary
    summary = get_budget_summary(st.session_state.user_id, month, year)
    
    if not summary:
        st.info("No budgets set for this month. Add your first budget above!")
    else:
        # Create a progress chart for each category
        for item in summary:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                progress = item['percent_used']
                color = "normal" if progress <= 80 else "warning" if progress <= 100 else "error"
                st.progress(min(progress / 100, 1.0), text=f"{item['category']}: ${item['spent']:,.2f} / ${item['budget_amount']:,.2f}")
            with col2:
                st.write(f"Remaining: ${item['remaining']:,.2f}")
            with col3:
                if st.button("Delete", key=f"del_budget_{item['category']}"):
                    delete_budget(st.session_state.user_id, item['category'], month, year)
                    st.rerun()
        
        # Create visualization
        fig = go.Figure()
        
        # Add bars for budget amount
        fig.add_trace(go.Bar(
            name="Budget",
            x=[item['category'] for item in summary],
            y=[item['budget_amount'] for item in summary],
            marker_color='lightgrey'
        ))
        
        # Add bars for actual spending
        fig.add_trace(go.Bar(
            name="Spent",
            x=[item['category'] for item in summary],
            y=[item['spent'] for item in summary],
            marker_color='rgba(58, 71, 80, 0.6)'
        ))
        
        fig.update_layout(
            title="Budget vs. Actual Spending by Category",
            barmode='overlay',
            xaxis_tickangle=-45,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary statistics
        total_budget = sum(item['budget_amount'] for item in summary)
        total_spent = sum(item['spent'] for item in summary)
        total_remaining = total_budget - total_spent
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Budget", f"${total_budget:,.2f}")
        with col2:
            st.metric("Total Spent", f"${total_spent:,.2f}")
        with col3:
            st.metric("Total Remaining", f"${total_remaining:,.2f}")

def show_family_profiles():
    """Display family profiles interface"""
    st.header("👨‍👩‍👧‍👦 Family Profiles")
    
    # Add new family member
    with st.expander("Add Family Member", expanded=True):
        with st.form("add_member_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name")
                relationship = st.selectbox("Relationship", get_relationship_types())
            with col2:
                birth_date = st.date_input("Birth Date", min_value=datetime(1900, 1, 1))
            
            submit = st.form_submit_button("Add Family Member")
            if submit and name:
                add_family_member(
                    st.session_state.user_id,
                    name,
                    relationship,
                    birth_date.strftime("%Y-%m-%d")
                )
                st.success(f"Added {name} to family members")
                st.rerun()
    
    # Display family members
    st.subheader("Family Members")
    members = get_family_members(st.session_state.user_id)
    
    if not members:
        st.info("No family members added yet. Add your first family member above!")
    else:
        # Create columns for the family tree visualization
        cols = st.columns(min(len(members), 4))  # Maximum 4 columns
        
        for idx, member in enumerate(members):
            with cols[idx % 4]:
                with st.container():
                    # Member card
                    st.markdown(f"""
                    <div style='padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin: 5px;'>
                        <h3>{member['name']} 👤</h3>
                        <p><strong>Relationship:</strong> {member['relationship']}</p>
                        <p><strong>Birth Date:</strong> {member['birth_date']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Edit member
                    if st.button("Edit", key=f"edit_{member['id']}"):
                        st.session_state[f"editing_{member['id']}"] = True
                    
                    # Delete member
                    if st.button("Delete", key=f"delete_{member['id']}"):
                        delete_family_member(member['id'])
                        st.success(f"Removed {member['name']} from family members")
                        st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"editing_{member['id']}", False):
                        with st.form(f"edit_member_form_{member['id']}"):
                            new_name = st.text_input("Name", value=member['name'])
                            new_relationship = st.selectbox(
                                "Relationship",
                                get_relationship_types(),
                                index=get_relationship_types().index(member['relationship'])
                            )
                            new_birth_date = st.date_input(
                                "Birth Date",
                                datetime.strptime(member['birth_date'], "%Y-%m-%d").date()
                                if member['birth_date'] else datetime.now()
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Save"):
                                    update_family_member(
                                        member['id'],
                                        new_name,
                                        new_relationship,
                                        new_birth_date.strftime("%Y-%m-%d")
                                    )
                                    st.session_state[f"editing_{member['id']}"] = False
                                    st.success("Updated family member details")
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("Cancel"):
                                    st.session_state[f"editing_{member['id']}"] = False
                                    st.rerun()
        
        # Family Statistics
        st.subheader("Family Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            # Relationship distribution pie chart
            relationship_counts = {}
            for member in members:
                relationship_counts[member['relationship']] = relationship_counts.get(member['relationship'], 0) + 1
            
            fig = px.pie(
                values=list(relationship_counts.values()),
                names=list(relationship_counts.keys()),
                title="Family Composition"
            )
            st.plotly_chart(fig)
        
        with col2:
            # Age distribution
            ages = []
            for member in members:
                if member['birth_date']:
                    birth_date = datetime.strptime(member['birth_date'], "%Y-%m-%d")
                    age = (datetime.now() - birth_date).days // 365
                    ages.append(age)
            
            if ages:
                fig = px.histogram(
                    x=ages,
                    nbins=10,
                    title="Age Distribution",
                    labels={'x': 'Age', 'y': 'Count'}
                )
                st.plotly_chart(fig)

def show_calendar():
    """Display calendar and events interface"""
    st.header("📅 Calendar & Events")
    
    # Calendar Navigation
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        current_month = datetime.now().month
        month = st.selectbox("Month", range(1, 13), index=current_month - 1,
                           format_func=lambda x: datetime(2024, x, 1).strftime("%B"))
    with col2:
        current_year = datetime.now().year
        year = st.selectbox("Year", range(current_year - 1, current_year + 3), index=1)
    with col3:
        view_type = st.selectbox("View", ["Month", "Week", "Upcoming"])
    
    # Add New Event
    with st.expander("Add New Event", expanded=True):
        with st.form("add_event_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Event Title")
                category = st.selectbox("Category", get_event_categories())
                description = st.text_area("Description")
            with col2:
                start_date = st.date_input("Start Date")
                start_time = st.time_input("Start Time")
                end_date = st.date_input("End Date")
                end_time = st.time_input("End Time")
                reminder = st.checkbox("Set Reminder")
                if reminder:
                    reminder_time = st.datetime_input("Reminder Time")
                else:
                    reminder_time = None
            
            submit = st.form_submit_button("Add Event")
            if submit and title:
                start_datetime = datetime.combine(start_date, start_time)
                end_datetime = datetime.combine(end_date, end_time)
                add_event(
                    st.session_state.user_id,
                    title,
                    f"{category}: {description}",
                    start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    reminder,
                    reminder_time.strftime('%Y-%m-%d %H:%M:%S') if reminder_time else None
                )
                st.success("Event added successfully!")
                st.rerun()
    
    # Display Calendar View
    if view_type == "Month":
        # Get all events for the month
        events = get_events_by_month(st.session_state.user_id, year, month)
        
        # Create calendar grid
        cal = calendar.monthcalendar(year, month)
        
        # Create calendar table
        st.markdown(f"### {calendar.month_name[month]} {year}")
        
        # Create week header
        week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for i, col in enumerate(cols):
            col.markdown(f"**{week_days[i]}**")
        
        # Create calendar grid
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day != 0:
                        date = datetime(year, month, day)
                        day_events = [e for e in events if datetime.strptime(e['start_date'], '%Y-%m-%d %H:%M:%S').date() == date.date()]
                        
                        # Display day and events
                        st.markdown(f"**{day}**")
                        for event in day_events:
                            with st.container():
                                st.markdown(f"""
                                <div style='padding: 5px; background-color: #f0f2f6; border-radius: 5px; margin: 2px;'>
                                    {event['title']}
                                </div>
                                """, unsafe_allow_html=True)
    
    elif view_type == "Week":
        # Get current week's start and end dates
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        events = get_events(
            st.session_state.user_id,
            week_start.strftime('%Y-%m-%d'),
            week_end.strftime('%Y-%m-%d')
        )
        
        # Display week view
        st.markdown(f"### Week of {week_start.strftime('%B %d, %Y')}")
        
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            day_events = [e for e in events if datetime.strptime(e['start_date'], '%Y-%m-%d %H:%M:%S').date() == current_date.date()]
            
            with st.expander(f"{current_date.strftime('%A, %B %d')}", expanded=True):
                if day_events:
                    for event in day_events:
                        event_time = datetime.strptime(event['start_date'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')
                        st.markdown(f"""
                        <div style='padding: 10px; background-color: #f0f2f6; border-radius: 5px; margin: 5px;'>
                            <strong>{event_time}</strong> - {event['title']}<br>
                            <small>{event['description']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns([4, 1])
                        with col2:
                            if st.button("Delete", key=f"del_event_{event['id']}"):
                                delete_event(event['id'])
                                st.success("Event deleted")
                                st.rerun()
                else:
                    st.info("No events scheduled")
    
    else:  # Upcoming view
        events = get_upcoming_events(st.session_state.user_id)
        
        st.markdown("### Upcoming Events")
        if events:
            for event in events:
                event_date = datetime.strptime(event['start_date'], '%Y-%m-%d %H:%M:%S')
                with st.expander(
                    f"{event_date.strftime('%A, %B %d')} - {event['title']}", 
                    expanded=True
                ):
                    st.markdown(f"""
                    **Time:** {event_date.strftime('%I:%M %p')}  
                    **Description:** {event['description']}  
                    """)
                    
                    if event['reminder']:
                        reminder_time = datetime.strptime(event['reminder_time'], '%Y-%m-%d %H:%M:%S')
                        st.info(f"Reminder set for {reminder_time.strftime('%B %d, %I:%M %p')}")
                    
                    if st.button("Delete", key=f"del_upcoming_{event['id']}"):
                        delete_event(event['id'])
                        st.success("Event deleted")
                        st.rerun()
        else:
            st.info("No upcoming events in the next 7 days")

def show_goals():
    """Display goals tracking interface"""
    st.header("🎯 Goals & Milestones")
    
    # Add new goal
    with st.expander("Add New Goal", expanded=True):
        with st.form("add_goal_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Goal Title")
                category = st.selectbox("Category", get_goal_categories())
                description = st.text_area("Description")
            with col2:
                target_date = st.date_input("Target Date")
                if category == "Financial":
                    target_amount = st.number_input("Target Amount ($)", min_value=0.0, step=100.0)
                else:
                    target_amount = None
            
            submit = st.form_submit_button("Add Goal")
            if submit and title:
                add_goal(
                    st.session_state.user_id,
                    title,
                    category,
                    description,
                    target_date.strftime("%Y-%m-%d"),
                    target_amount
                )
                st.success("Goal added successfully!")
                st.rerun()
    
    # Filter goals
    col1, col2 = st.columns(2)
    with col1:
        filter_category = st.selectbox("Filter by Category", ["All"] + get_goal_categories())
    with col2:
        filter_status = st.selectbox("Filter by Status", ["All"] + get_goal_status_types())
    
    # Get goals with filters
    goals = get_goals(
        st.session_state.user_id,
        category=filter_category if filter_category != "All" else None,
        status=filter_status if filter_status != "All" else None
    )
    
    if not goals:
        st.info("No goals added yet. Create your first goal above!")
    else:
        # AI-Powered Goal Analysis
        st.subheader("🤖 Goal Analysis")
        analysis_container = st.container()
        
        with analysis_container:
            # Calculate overall progress
            total_goals = len(goals)
            completed_goals = len([g for g in goals if g['status'] == 'Completed'])
            in_progress_goals = len([g for g in goals if g['status'] == 'In Progress'])
            
            # Calculate average progress
            avg_progress = sum(float(g['progress']) for g in goals) / total_goals
            
            st.markdown("""
                <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0;'>
                    <h4 style='color: #4CAF50;'>Progress Overview</h4>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                - Total Goals: **{total_goals}**
                - Completed: **{completed_goals}** ({completed_goals/total_goals*100:.1f}%)
                - In Progress: **{in_progress_goals}** ({in_progress_goals/total_goals*100:.1f}%)
                - Average Progress: **{avg_progress:.1f}%**
            """)
            
            # Analyze goal completion patterns
            if completed_goals > 0:
                completed_goals_data = [g for g in goals if g['status'] == 'Completed']
                avg_completion_time = sum(
                    (datetime.strptime(g['target_date'], "%Y-%m-%d") - datetime.now()).days
                    for g in completed_goals_data
                ) / completed_goals
                
                st.markdown(f"""
                    - Average Time to Complete: **{abs(avg_completion_time):.0f} days**
                """)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Smart Recommendations
        st.subheader("💡 Smart Recommendations")
        recommendations = []
        
        # Analyze goals and generate recommendations
        for goal in goals:
            if goal['status'] == 'In Progress':
                # Check for goals approaching deadline
                target_date = datetime.strptime(goal['target_date'], "%Y-%m-%d")
                days_remaining = (target_date - datetime.now()).days
                
                if 0 < days_remaining < 7:
                    recommendations.append(
                        f"**{goal['title']}** is due in {days_remaining} days. "
                        f"Current progress: {goal['progress']}%"
                    )
                
                # Check for stalled goals
                if float(goal['progress']) < 30 and days_remaining < 30:
                    recommendations.append(
                        f"**{goal['title']}** might need attention. "
                        f"Consider breaking it down into smaller milestones."
                    )
        
        if recommendations:
            for rec in recommendations:
                st.markdown(f"- {rec}")
        else:
            st.info("Your goals are on track! Keep up the good work!")
        
        # Display goals in a kanban-style board
        status_cols = st.columns(len(get_goal_status_types()))
        
        for idx, status in enumerate(get_goal_status_types()):
            with status_cols[idx]:
                st.markdown(f"### {status}")
                status_goals = [g for g in goals if g['status'] == status]
                
                for goal in status_goals:
                    with st.container():
                        # Goal card with enhanced visualization
                        st.markdown(f"""
                        <div style='padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin: 5px;'>
                            <h4>{goal['title']}</h4>
                            <p><strong>Category:</strong> {goal['category']}</p>
                            <p><strong>Target Date:</strong> {goal['target_date']}</p>
                            {f"<p><strong>Target Amount:</strong> ${goal['target_amount']:,.2f}</p>" if goal['target_amount'] else ""}
                            <div style="margin: 10px 0;">
                                <div style="height: 20px; background-color: #f0f2f6; border-radius: 10px;">
                                    <div style="width: {goal['progress']}%; height: 100%; background-color: #00c853; border-radius: 10px;"></div>
                                </div>
                                <p style="text-align: center;">{goal['progress']}% Complete</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Goal actions
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("Update", key=f"update_{goal['id']}"):
                                st.session_state[f"editing_goal_{goal['id']}"] = True
                        with col2:
                            if st.button("Milestones", key=f"milestones_{goal['id']}"):
                                st.session_state[f"show_milestones_{goal['id']}"] = True
                        with col3:
                            if st.button("Delete", key=f"delete_goal_{goal['id']}"):
                                delete_goal(goal['id'])
                                st.success("Goal deleted")
                                st.rerun()
                        
                        # Edit goal form
                        if st.session_state.get(f"editing_goal_{goal['id']}", False):
                            with st.form(f"edit_goal_form_{goal['id']}"):
                                new_title = st.text_input("Title", value=goal['title'])
                                new_category = st.selectbox(
                                    "Category",
                                    get_goal_categories(),
                                    index=get_goal_categories().index(goal['category'])
                                )
                                new_description = st.text_area("Description", value=goal['description'])
                                new_target_date = st.date_input(
                                    "Target Date",
                                    datetime.strptime(goal['target_date'], "%Y-%m-%d").date()
                                )
                                if new_category == "Financial":
                                    new_target_amount = st.number_input(
                                        "Target Amount ($)",
                                        value=float(goal['target_amount']) if goal['target_amount'] else 0.0,
                                        min_value=0.0,
                                        step=100.0
                                    )
                                else:
                                    new_target_amount = None
                                
                                new_status = st.selectbox(
                                    "Status",
                                    get_goal_status_types(),
                                    index=get_goal_status_types().index(goal['status'])
                                )
                                new_progress = st.slider(
                                    "Progress (%)",
                                    min_value=0,
                                    max_value=100,
                                    value=int(goal['progress'])
                                )
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("Save"):
                                        update_goal(
                                            goal['id'],
                                            title=new_title,
                                            category=new_category,
                                            description=new_description,
                                            target_date=new_target_date.strftime("%Y-%m-%d"),
                                            target_amount=new_target_amount,
                                            status=new_status,
                                            progress=new_progress
                                        )
                                        st.session_state[f"editing_goal_{goal['id']}"] = False
                                        st.success("Goal updated successfully!")
                                        st.rerun()
                                with col2:
                                    if st.form_submit_button("Cancel"):
                                        st.session_state[f"editing_goal_{goal['id']}"] = False
                                        st.rerun()
                        
                        # Milestones section
                        if st.session_state.get(f"show_milestones_{goal['id']}", False):
                            st.markdown("#### Milestones")
                            
                            # Add milestone form
                            with st.form(f"add_milestone_form_{goal['id']}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    milestone_title = st.text_input("Milestone Title", key=f"milestone_title_{goal['id']}")
                                with col2:
                                    milestone_date = st.date_input("Target Date", key=f"milestone_date_{goal['id']}")
                                
                                if st.form_submit_button("Add Milestone"):
                                    add_goal_milestone(
                                        goal['id'],
                                        milestone_title,
                                        milestone_date.strftime("%Y-%m-%d")
                                    )
                                    st.success("Milestone added!")
                                    st.rerun()
                            
                            # Display milestones
                            milestones = get_goal_milestones(goal['id'])
                            for milestone in milestones:
                                col1, col2, col3 = st.columns([3, 1, 1])
                                with col1:
                                    st.write(f"• {milestone['title']} ({milestone['target_date']})")
                                with col2:
                                    if st.checkbox("Completed", value=milestone['completed'], key=f"milestone_{milestone['id']}"):
                                        update_milestone_status(milestone['id'], True)
                                    else:
                                        update_milestone_status(milestone['id'], False)
                                with col3:
                                    if st.button("Delete", key=f"delete_milestone_{milestone['id']}"):
                                        delete_milestone(milestone['id'])
                                        st.success("Milestone deleted")
                                        st.rerun()
                            
                            if st.button("Close Milestones", key=f"close_milestones_{goal['id']}"):
                                st.session_state[f"show_milestones_{goal['id']}"] = False
                                st.rerun()
        
        # Goals Statistics
        st.subheader("Goals Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            # Category distribution
            category_counts = {}
            for goal in goals:
                category_counts[goal['category']] = category_counts.get(goal['category'], 0) + 1
            
            fig = px.pie(
                values=list(category_counts.values()),
                names=list(category_counts.keys()),
                title="Goals by Category"
            )
            st.plotly_chart(fig)
        
        with col2:
            # Status distribution
            status_counts = {}
            for goal in goals:
                status_counts[goal['status']] = status_counts.get(goal['status'], 0) + 1
            
            fig = px.bar(
                x=list(status_counts.keys()),
                y=list(status_counts.values()),
                title="Goals by Status",
                labels={'x': 'Status', 'y': 'Count'}
            )
            st.plotly_chart(fig)

def show_ai_assistant():
    """Display AI Assistant interface"""
    st.header("🤖 AI Assistant")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about family management..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            response = generate_ai_response(prompt)
            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Quick action buttons
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💡 Get Budget Advice"):
            prompt = "What are some tips for creating and sticking to a family budget?"
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                response = generate_ai_response(prompt)
                st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    with col2:
        if st.button("🎯 Goal Planning"):
            prompt = "How can I set and achieve family goals effectively?"
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                response = generate_ai_response(prompt)
                st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    with col3:
        if st.button("📅 Event Planning"):
            prompt = "What are some tips for organizing family events and activities?"
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                response = generate_ai_response(prompt)
                st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})

def generate_ai_response(prompt):
    """Generate AI response based on user input"""
    # This is a placeholder for actual AI integration
    # In a real application, you would integrate with an AI service
    responses = {
        "budget": [
            "Here are some tips for creating and sticking to a family budget:\n\n"
            "1. Track all income and expenses\n"
            "2. Set realistic goals\n"
            "3. Use the 50/30/20 rule\n"
            "4. Review and adjust regularly\n"
            "5. Involve the whole family"
        ],
        "goals": [
            "To set and achieve family goals effectively:\n\n"
            "1. Make goals specific and measurable\n"
            "2. Break down large goals into smaller steps\n"
            "3. Set deadlines\n"
            "4. Celebrate progress\n"
            "5. Review and adjust as needed"
        ],
        "events": [
            "Tips for organizing family events:\n\n"
            "1. Use a shared calendar\n"
            "2. Plan ahead\n"
            "3. Delegate tasks\n"
            "4. Set reminders\n"
            "5. Keep a checklist"
        ]
    }
    
    # Simple response generation based on keywords
    if "budget" in prompt.lower():
        return responses["budget"][0]
    elif "goal" in prompt.lower():
        return responses["goals"][0]
    elif "event" in prompt.lower():
        return responses["events"][0]
    else:
        return "I'm here to help with your family management needs. You can ask me about budgeting, goal setting, event planning, and more!"

def show_settings():
    """Display settings and user profile interface"""
    st.header("⚙️ Settings")
    
    # User Profile Settings
    st.subheader("Profile Settings")
    with st.form("profile_settings"):
        email = st.text_input("Email")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("Update Profile"):
            if new_password:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    update_user_profile(st.session_state.user_id, email=email, password=new_password)
                    st.success("Profile updated successfully!")
            elif email:
                update_user_profile(st.session_state.user_id, email=email)
                st.success("Email updated successfully!")
    
    # Data Management
    st.subheader("Data Management")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Export Data")
        if st.button("Export All Data"):
            user_data = get_user_data(st.session_state.user_id)
            # Convert to JSON for download
            import json
            from datetime import datetime
            
            # Convert datetime objects to strings
            def datetime_handler(x):
                if isinstance(x, datetime):
                    return x.isoformat()
                return str(x)
            
            json_str = json.dumps(user_data, default=datetime_handler, indent=2)
            
            st.download_button(
                label="Download Data (JSON)",
                data=json_str,
                file_name=f"family_planner_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        st.markdown("### Import Data")
        uploaded_file = st.file_uploader("Choose a backup file", type=['json'])
        if uploaded_file is not None:
            try:
                import json
                data = json.loads(uploaded_file.getvalue())
                if st.button("Import Data"):
                    if import_user_data(st.session_state.user_id, data):
                        st.success("Data imported successfully!")
                    else:
                        st.error("Error importing data. Please check the file format.")
            except Exception as e:
                st.error("Invalid file format. Please upload a valid JSON backup file.")
    
    # Danger Zone
    st.subheader("Danger Zone", divider="red")
    with st.expander("Delete Account Data"):
        st.warning("This action will delete all your data and cannot be undone!")
        delete_confirmation = st.text_input("Type 'DELETE' to confirm")
        if st.button("Delete All Data", type="primary"):
            if delete_confirmation == "DELETE":
                if delete_user_data(st.session_state.user_id):
                    st.success("All data deleted successfully!")
                    st.session_state.logged_in = False
                    st.rerun()
                else:
                    st.error("Error deleting data. Please try again.")
            else:
                st.error("Please type 'DELETE' to confirm")

def main():
    # Custom CSS for sidebar
    st.markdown("""
        <style>
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        .css-1d391kg .sidebar-content {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 1rem;
        }
        .css-1d391kg .sidebar-content .block-container {
            padding-top: 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation with icons
    with st.sidebar:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h2 style='color: #4CAF50;'>Family Planner</h2>
            </div>
        """, unsafe_allow_html=True)
        
        # Navigation menu with icons
        menu_items = [
            ("🏠 Home", "Home"),
            ("💰 Financial Dashboard", "Financial Dashboard"),
            ("📊 Budget Planning", "Budget Planning"),
            ("🛒 Shopping Lists", "Shopping Lists"),
            ("📅 Calendar", "Calendar"),
            ("👨‍👩‍👧‍👦 Family Profiles", "Family Profiles"),
            ("🎯 Goals", "Goals"),
            ("🤖 AI Assistant", "AI Assistant"),
            ("⚙️ Settings", "Settings")
        ]
        
        for icon, label in menu_items:
            if st.button(f"{icon} {label}", use_container_width=True, key=f"nav_{label}"):
                st.session_state.page = label
                st.rerun()
        
        # Theme selector
        st.markdown("---")
        st.markdown("### Theme")
        theme = st.selectbox(
            "Choose theme",
            ["Light", "Dark"],
            key="theme_selector",
            label_visibility="collapsed"
        )
        if theme != st.session_state.theme:
            st.session_state.theme = theme.lower()
            st.rerun()
        
        # User info and logout
        st.markdown("---")
        st.markdown("### Account")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.rerun()
    
    # Main content area
    if not st.session_state.logged_in:
        show_login()
    else:
        # Page title with icon
        page_icons = {
            "Home": "🏠",
            "Financial Dashboard": "💰",
            "Budget Planning": "📊",
            "Shopping Lists": "🛒",
            "Calendar": "📅",
            "Family Profiles": "👨‍👩‍👧‍👦",
            "Goals": "🎯",
            "AI Assistant": "🤖",
            "Settings": "⚙️"
        }
        
        st.markdown(f"""
            <div style='background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <h1 style='margin: 0; color: #4CAF50;'>{page_icons.get(st.session_state.page, '')} {st.session_state.page}</h1>
            </div>
        """, unsafe_allow_html=True)
        
        # Show the appropriate page
        if st.session_state.page == "Home":
            show_home()
        elif st.session_state.page == "Financial Dashboard":
            show_financial_dashboard()
        elif st.session_state.page == "Shopping Lists":
            show_shopping_lists()
        elif st.session_state.page == "Budget Planning":
            show_budget_planning()
        elif st.session_state.page == "Family Profiles":
            show_family_profiles()
        elif st.session_state.page == "Calendar":
            show_calendar()
        elif st.session_state.page == "Goals":
            show_goals()
        elif st.session_state.page == "AI Assistant":
            show_ai_assistant()
        elif st.session_state.page == "Settings":
            show_settings()

if __name__ == "__main__":
    main() 