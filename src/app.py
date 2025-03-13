import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import calendar
import sqlite3
import os
import time
import random
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
from utils import setup_logging, log_performance_summary, monitor_performance

# Initialize logging
setup_logging()

# Configure Streamlit
st.set_page_config(
    page_title="Family Planner by Jithin",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    with open('src/static/style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load CSS
load_css()

# Configure server settings
st.markdown("""
    <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .footer {
            position: fixed;
            bottom: 0;
            width: 100%;
            background-color: var(--surface-color);
            padding: 1rem;
            text-align: center;
            border-top: 1px solid var(--border-color);
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"

# Initialize database on startup
init_database()

# Add rate limiting settings
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT_MINUTES = 15

def check_login_attempts(username: str) -> bool:
    """Check if user has exceeded login attempts"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    
    if username not in st.session_state.login_attempts:
        st.session_state.login_attempts[username] = {
            'count': 0,
            'last_attempt': None
        }
    
    attempts = st.session_state.login_attempts[username]
    current_time = datetime.now()
    
    # Reset attempts if timeout has passed
    if attempts['last_attempt'] and (current_time - attempts['last_attempt']).total_seconds() > LOGIN_TIMEOUT_MINUTES * 60:
        attempts['count'] = 0
        attempts['last_attempt'] = None
    
    # Check if user is locked out
    if attempts['count'] >= MAX_LOGIN_ATTEMPTS:
        if attempts['last_attempt']:
            time_left = LOGIN_TIMEOUT_MINUTES - (current_time - attempts['last_attempt']).total_seconds() / 60
            if time_left > 0:
                return False
            else:
                attempts['count'] = 0
                attempts['last_attempt'] = None
                return True
        return False
    
    return True

def record_login_attempt(username: str, success: bool):
    """Record login attempt"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    
    if username not in st.session_state.login_attempts:
        st.session_state.login_attempts[username] = {
            'count': 0,
            'last_attempt': None
        }
    
    attempts = st.session_state.login_attempts[username]
    attempts['last_attempt'] = datetime.now()
    
    if success:
        attempts['count'] = 0
    else:
        attempts['count'] += 1

def validate_input(text: str, max_length: int = 255) -> str:
    """Validate and sanitize user input"""
    if not text:
        raise ValueError("Input cannot be empty")
    if len(text) > max_length:
        raise ValueError(f"Input cannot exceed {max_length} characters")
    return text.strip()

def validate_amount(amount: float) -> float:
    """Validate amount input"""
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
    if amount > 1000000000:  # 1 billion
        raise ValueError("Amount is too large")
    return round(amount, 2)

def validate_date(date_str: str) -> str:
    """Validate date input"""
    try:
        date = pd.to_datetime(date_str)
        if date > pd.Timestamp.now():
            raise ValueError("Date cannot be in the future")
        return date.strftime('%Y-%m-%d %H:%M:%S')
    except:
        raise ValueError("Invalid date format")

def get_time_of_day_icon():
    """Get sun or moon icon based on time of day"""
    current_hour = datetime.now().hour
    if 6 <= current_hour < 18:  # Daytime (6 AM to 5:59 PM)
        return "☀️"
    else:  # Nighttime (6 PM to 5:59 AM)
        return "🌙"

def get_dynamic_heading_style():
    """Get appropriate heading style based on time of day"""
    current_hour = datetime.now().hour
    
    if 5 <= current_hour < 12:  # Morning
        return {
            'background': 'linear-gradient(45deg, #FFD700, #FFA500)',
            'icon': '🌅',
            'title': 'Good Morning!'
        }
    elif 12 <= current_hour < 17:  # Afternoon
        return {
            'background': 'linear-gradient(45deg, #87CEEB, #4169E1)',
            'icon': '☀️',
            'title': 'Good Afternoon!'
        }
    elif 17 <= current_hour < 22:  # Evening
        return {
            'background': 'linear-gradient(45deg, #FF69B4, #FF1493)',
            'icon': '🌇',
            'title': 'Good Evening!'
        }
    else:  # Night
        return {
            'background': 'linear-gradient(45deg, #483D8B, #000080)',
            'icon': '🌙',
            'title': 'Good Night!'
        }

def get_greeting_and_quote():
    """Get appropriate greeting and funny quote based on time of day"""
    current_hour = datetime.now().hour
    time_icon = get_time_of_day_icon()
    
    # Define greetings based on time of day
    if 5 <= current_hour < 12:
        greeting = f"Good Morning {time_icon}"
    elif 12 <= current_hour < 17:
        greeting = f"Good Afternoon {time_icon}"
    else:
        greeting = f"Good Evening {time_icon}"
    
    # Funny quotes about family and life
    quotes = [
        "Family: where life begins and love never ends. And where the WiFi password is never remembered!",
        "My family is like a fine wine - they get better with age, but they also get more expensive!",
        "Family is like fudge - mostly sweet with a few nuts!",
        "Home is where the WiFi connects automatically!",
        "Family: where everyone is welcome, but no one leaves without doing the dishes!",
        "My family is like a box of chocolates - you never know what you're gonna get, but it's always sweet!",
        "Family is like a garden - it needs constant weeding, but the flowers make it all worthwhile!",
        "Home is where your story begins, and where your laundry never ends!",
        "Family: where life's messiest moments become your fondest memories!",
        "My family is like a fine-tuned orchestra - when we're in sync, it's beautiful; when we're not, it's still entertaining!"
    ]
    
    return greeting, random.choice(quotes)

@monitor_performance()
def show_login():
    """Display login form"""
    st.markdown("""
        <div style='text-align: center; padding: 2rem; background: linear-gradient(45deg, #FFD700, #FFA500); border-radius: 12px; margin-bottom: 2rem;'>
            <h1 style='color: white;'>Family Planner</h1>
            <p style='color: white; font-size: 1.2rem;'>Created by Jithin</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.header("Login")
    
    # Add tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if not check_login_attempts(username):
                    time_left = LOGIN_TIMEOUT_MINUTES - (datetime.now() - st.session_state.login_attempts[username]['last_attempt']).total_seconds() / 60
                    st.error(f"Too many login attempts. Please try again in {time_left:.1f} minutes.")
                else:
                    user = verify_user(username, password)
                    if user:
                        record_login_attempt(username, True)
                        st.session_state.logged_in = True
                        st.session_state.user_id = user['id']
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        record_login_attempt(username, False)
                        st.error("Invalid username or password")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register")
            
            if submit:
                try:
                    new_username = validate_input(new_username)
                    new_email = validate_input(new_email)
                    
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        user_id = create_user(new_username, new_password, new_email)
                        if user_id:
                            st.success("Registration successful! Please login.")
                        else:
                            st.error("Username or email already exists")
                except ValueError as e:
                    st.error(str(e))

@monitor_performance()
def show_main_app():
    """Display main application interface"""
    # Add dynamic heading bar with time-based styling
    heading_style = get_dynamic_heading_style()
    st.markdown(f"""
        <div style='
            text-align: center; 
            padding: 2rem; 
            background: {heading_style['background']}; 
            border-radius: 12px; 
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            color: white;
        '>
            <h1 style='font-size: 2.5rem; margin-bottom: 0.5rem;'>
                {heading_style['icon']} Family Planner {heading_style['icon']}
            </h1>
            <p style='font-size: 1.2rem; margin: 0; opacity: 0.9;'>
                {heading_style['title']} Let's organize your family life!
            </p>
            <p style='font-size: 1rem; margin-top: 1rem; opacity: 0.8;'>
                Created by Jithin
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Add breadcrumbs
    st.markdown("""
        <div style='padding: 0.5rem; background-color: var(--surface-color); border-radius: 4px; margin-bottom: 1rem;'>
            <span style='color: var(--text-secondary);'>Home</span> / 
            <span style='color: var(--text-primary);'>{}</span>
        </div>
    """.format(st.session_state.current_page), unsafe_allow_html=True)
    
    # Sidebar navigation with icons
    with st.sidebar:
        st.markdown("""
            <div style='text-align: center; padding: 1rem;'>
                <h2>👨‍👩‍👧‍👦 Family Planner</h2>
            </div>
        """, unsafe_allow_html=True)
        
        # Navigation menu with icons
        menu_items = [
            ("🏠", "Home"),
            ("💰", "Financial Dashboard"),
            ("📊", "Budget Planning"),
            ("🛒", "Shopping Lists"),
            ("📅", "Calendar"),
            ("👥", "Family Profiles"),
            ("🎯", "Goals"),
            ("⚙️", "Settings")
        ]
        
        for icon, page in menu_items:
            if st.button(icon + " " + page, key=f"nav_{page}", use_container_width=True):
                st.session_state.current_page = page
                st.rerun()
        
        st.markdown("---")
        
        # User profile section
        user_data = get_user_data(st.session_state.user_id)
        if user_data:
            st.markdown(f"""
                <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px;'>
                    <p><strong>👤 {user_data['username']}</strong></p>
                    <p style='color: var(--text-secondary);'>{user_data['email']}</p>
                </div>
            """, unsafe_allow_html=True)
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.rerun()
    
    # Lazy load page content
    if st.session_state.current_page == "Home":
        show_home()
    elif st.session_state.current_page == "Financial Dashboard":
        show_financial_dashboard()
    elif st.session_state.current_page == "Shopping Lists":
        show_shopping_lists()
    elif st.session_state.current_page == "Budget Planning":
        show_budget_planning()
    elif st.session_state.current_page == "Family Profiles":
        show_family_profiles()
    elif st.session_state.current_page == "Calendar":
        show_calendar()
    elif st.session_state.current_page == "Goals":
        show_goals()
    elif st.session_state.current_page == "Settings":
        show_settings()

@monitor_performance()
def show_home():
    """Display home dashboard"""
    # Get dynamic greeting and quote
    greeting, quote = get_greeting_and_quote()
    
    # Display greeting with animation
    st.markdown(f"""
        <div style='text-align: center; padding: 2rem; background-color: var(--surface-color); border-radius: 8px; margin-bottom: 2rem;'>
            <h1 style='color: var(--primary-color);'>{greeting}!</h1>
            <p style='font-style: italic; color: var(--text-secondary);'>{quote}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.header("Welcome to Family Planner")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Quick Stats")
        # Get current month's transactions
        current_month = datetime.now().month
        current_year = datetime.now().year
        transactions_data = get_transactions(st.session_state.user_id)
        transactions = transactions_data['transactions']
        
        # Calculate total income and expenses
        income = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'income')
        expenses = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'expense')
        
        st.metric(label="Total Income", value=f"₹{income:,.2f}")
        st.metric(label="Total Expenses", value=f"₹{expenses:,.2f}")
        st.metric(label="Balance", value=f"₹{income - expenses:,.2f}")
        
        # Add funny comment about finances
        if income < expenses:
            st.markdown("""
                <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-top: 1rem;'>
                    <p style='color: var(--error-color);'>💰 Your wallet is looking a bit thin! Time to start a lemonade stand?</p>
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("📅 Quick Actions")
        if st.button("Add Transaction"):
            st.session_state.current_page = "Financial Dashboard"
            st.rerun()
        if st.button("Create Shopping List"):
            st.session_state.current_page = "Shopping Lists"
            st.rerun()
        
        # Add funny comment about shopping
        st.markdown("""
            <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-top: 1rem;'>
                <p>🛒 Remember: Shopping is like a sport - the more you practice, the better you get at finding deals!</p>
            </div>
        """, unsafe_allow_html=True)

def show_financial_dashboard():
    """Display financial dashboard"""
    st.header("Financial Dashboard")
    
    # Add filters for date range
    col1, col2, col3 = st.columns(3)
    with col1:
        date_range = st.selectbox(
            "Date Range",
            ["Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "This Year", "All Time"]
        )
    with col2:
        category_filter = st.multiselect(
            "Categories",
            ["Groceries", "Utilities", "Rent", "Entertainment", "Income", "Other"],
            default=["Groceries", "Utilities", "Rent", "Entertainment", "Income", "Other"]
        )
    with col3:
        transaction_type_filter = st.multiselect(
            "Transaction Type",
            ["income", "expense"],
            default=["income", "expense"]
        )
    
    # Add transaction form with auto-refresh
    with st.expander("Add New Transaction", expanded=False):
        with st.form("transaction_form"):
            col1, col2 = st.columns(2)
            with col1:
                try:
                    amount = validate_amount(st.number_input("Amount", min_value=0.01, step=0.01))
                except ValueError as e:
                    st.error(str(e))
                    amount = None
                
                category = st.selectbox(
                    "Category",
                    ["Groceries", "Utilities", "Rent", "Entertainment", "Income", "Other"]
                )
            with col2:
                try:
                    description = validate_input(st.text_input("Description"))
                except ValueError as e:
                    st.error(str(e))
                    description = None
                
                transaction_type = st.selectbox(
                    "Type",
                    ["expense", "income"]
                )
            
            if st.form_submit_button("Add Transaction"):
                if amount is not None and description is not None:
                    try:
                        add_transaction(
                            st.session_state.user_id,
                            amount,
                            category,
                            description,
                            transaction_type
                        )
                        st.success("Transaction added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding transaction: {str(e)}")
                else:
                    st.error("Please fix the validation errors before submitting")
    
    # Display transactions with real-time updates
    st.subheader("Recent Transactions")
    try:
        transactions_data = get_transactions(st.session_state.user_id)
        transactions = transactions_data['transactions']
        
        if transactions:
            # Create a DataFrame for plotting
            df = pd.DataFrame(transactions)
            
            # Apply filters
            if date_range != "All Time":
                days = int(date_range.split()[1])
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df = df[df['date'] >= pd.Timestamp.now() - pd.Timedelta(days=days)]
            
            if category_filter:
                df = df[df['category'].isin(category_filter)]
            
            if transaction_type_filter:
                df = df[df['transaction_type'].isin(transaction_type_filter)]
            
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["Summary", "Charts", "Transactions"])
            
            with tab1:
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_income = df[df['transaction_type'] == 'income']['amount'].sum()
                    st.metric("Total Income", f"₹{total_income:,.2f}")
                with col2:
                    total_expenses = df[df['transaction_type'] == 'expense']['amount'].sum()
                    st.metric("Total Expenses", f"₹{total_expenses:,.2f}")
                with col3:
                    balance = total_income - total_expenses
                    st.metric("Balance", f"₹{balance:,.2f}")
            
            with tab2:
                # Interactive charts
                col1, col2 = st.columns(2)
                with col1:
                    # Expenses by category
                    expenses_by_category = df[df['transaction_type'] == 'expense'].groupby('category')['amount'].sum()
                    fig = px.pie(
                        values=expenses_by_category.values,
                        names=expenses_by_category.index,
                        title="Expenses by Category"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Monthly trend
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    monthly_data = df.groupby(df['date'].dt.to_period('M')).agg({
                        'amount': lambda x: x[df['transaction_type'] == 'income'].sum(),
                        'amount': lambda x: x[df['transaction_type'] == 'expense'].sum()
                    }).reset_index()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name="Income",
                        x=monthly_data['date'].astype(str),
                        y=monthly_data['amount']
                    ))
                    fig.add_trace(go.Bar(
                        name="Expenses",
                        x=monthly_data['date'].astype(str),
                        y=monthly_data['amount']
                    ))
                    fig.update_layout(
                        title="Monthly Income vs Expenses",
                        barmode='group',
                        xaxis_title="Month",
                        yaxis_title="Amount (₹)"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                # Interactive transaction list
                for tx in transactions:
                    try:
                        tx_date = pd.to_datetime(tx['date'], errors='coerce')
                        date_str = tx_date.strftime('%Y-%m-%d %H:%M') if pd.notnull(tx_date) else 'Unknown Date'
                    except:
                        date_str = 'Unknown Date'
                    
                    with st.expander(f"{date_str} - {tx['description']} (₹{float(tx['amount']):,.2f})"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"Category: {tx['category']}")
                            st.write(f"Type: {tx['transaction_type']}")
                        with col2:
                            if st.button("Edit", key=f"edit_{tx['id']}"):
                                st.session_state[f"editing_{tx['id']}"] = True
                        with col3:
                            if st.button("Delete", key=f"delete_{tx['id']}"):
                                try:
                                    delete_transaction(tx['id'])
                                    st.success("Transaction deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting transaction: {str(e)}")
                        
                        # Edit form
                        if st.session_state.get(f"editing_{tx['id']}", False):
                            with st.form(f"edit_transaction_{tx['id']}"):
                                new_amount = st.number_input("Amount", value=float(tx['amount']), min_value=0.01, step=0.01)
                                new_category = st.selectbox(
                                    "Category",
                                    ["Groceries", "Utilities", "Rent", "Entertainment", "Income", "Other"],
                                    index=["Groceries", "Utilities", "Rent", "Entertainment", "Income", "Other"].index(tx['category'])
                                )
                                new_description = st.text_input("Description", value=tx['description'])
                                new_type = st.selectbox(
                                    "Type",
                                    ["expense", "income"],
                                    index=0 if tx['transaction_type'] == 'expense' else 1
                                )
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("Save"):
                                        try:
                                            update_transaction(
                                                tx['id'],
                                                new_amount,
                                                new_category,
                                                new_description,
                                                new_type
                                            )
                                            st.session_state[f"editing_{tx['id']}"] = False
                                            st.success("Transaction updated!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error updating transaction: {str(e)}")
                                with col2:
                                    if st.form_submit_button("Cancel"):
                                        st.session_state[f"editing_{tx['id']}"] = False
                                        st.rerun()
        else:
            st.info("No transactions found. Add your first transaction above!")
    except Exception as e:
        st.error(f"Error loading transactions: {str(e)}")

def show_shopping_lists():
    """Display shopping lists interface"""
    st.header("📝 Shopping Lists")
    
    # Add filters and quick actions
    col1, col2 = st.columns([3, 1])
    with col1:
        view_type = st.selectbox(
            "View Lists By",
            ["All Lists", "Active Lists", "Completed Lists"]
        )
    with col2:
        if st.button("Create New List", type="primary"):
            st.session_state.show_new_list_form = True
    
    # Create new shopping list with improved UI
    if st.session_state.get("show_new_list_form", False):
        with st.expander("Create New Shopping List", expanded=True):
            with st.form("new_list_form"):
                col1, col2 = st.columns(2)
                with col1:
                    list_name = st.text_input("List Name")
                    description = st.text_area("Description (Optional)")
                with col2:
                    priority = st.selectbox(
                        "Priority",
                        ["Low", "Medium", "High"],
                        index=1
                    )
                    due_date = st.date_input("Due Date (Optional)")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Create List"):
                        if list_name:
                            create_shopping_list(
                                st.session_state.user_id,
                                list_name,
                                description,
                                priority,
                                due_date.strftime("%Y-%m-%d") if due_date else None
                            )
                            st.success(f"Created new list: {list_name}")
                            st.session_state.show_new_list_form = False
                            st.rerun()
                with col2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_new_list_form = False
                        st.rerun()
    
    # Display existing lists with improved organization
    shopping_lists = get_shopping_lists(st.session_state.user_id)
    
    if not shopping_lists:
        st.info("No shopping lists yet. Create your first list above!")
    else:
        # Filter lists based on view type
        if view_type == "Active Lists":
            shopping_lists = [l for l in shopping_lists if not l.get('completed', False)]
        elif view_type == "Completed Lists":
            shopping_lists = [l for l in shopping_lists if l.get('completed', False)]
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["Lists", "Statistics"])
        
        with tab1:
            # Display lists in a grid layout
            for shopping_list in shopping_lists:
                with st.expander(
                    f"📋 {shopping_list['name']} ({shopping_list['created_at']})",
                    expanded=not shopping_list.get('completed', False)
                ):
                    # List header with metadata
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        if shopping_list.get('description'):
                            st.markdown(f"*{shopping_list['description']}*")
                    with col2:
                        if shopping_list.get('priority'):
                            priority_color = {
                                "Low": "green",
                                "Medium": "orange",
                                "High": "red"
                            }.get(shopping_list['priority'], "grey")
                            st.markdown(f"**Priority:** <span style='color: {priority_color}'>{shopping_list['priority']}</span>", 
                                      unsafe_allow_html=True)
                    with col3:
                        if shopping_list.get('due_date'):
                            st.markdown(f"**Due:** {shopping_list['due_date']}")
                    
                    # Add new item form with improved UI
                    with st.form(f"add_item_form_{shopping_list['id']}"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            item_name = st.text_input("Item Name", key=f"item_name_{shopping_list['id']}")
                        with col2:
                            quantity = st.number_input("Quantity", min_value=1, value=1, key=f"quantity_{shopping_list['id']}")
                        with col3:
                            estimated_price = st.number_input(
                                "Est. Price (₹)",
                                min_value=0.0,
                                value=0.0,
                                key=f"price_{shopping_list['id']}"
                            )
                        
                        submit = st.form_submit_button("Add Item")
                        if submit and item_name:
                            add_list_item(
                                shopping_list['id'],
                                item_name,
                                quantity,
                                estimated_price
                            )
                            st.success(f"Added {item_name} to the list")
                            st.rerun()
                    
                    # Display items with improved organization
                    items = get_list_items(shopping_list['id'])
                    if items:
                        # Calculate list statistics
                        total_items = len(items)
                        completed_items = sum(1 for item in items if item['completed'])
                        total_estimated_cost = sum(float(item.get('estimated_price', 0)) * item['quantity'] for item in items)
                        
                        # Show progress bar
                        progress = (completed_items / total_items * 100) if total_items > 0 else 0
                        st.progress(
                            min(progress / 100, 1.0),
                            text=f"Progress: {completed_items}/{total_items} items ({progress:.1f}%)"
                        )
                        
                        # Show estimated total
                        st.markdown(f"**Estimated Total:** ₹{total_estimated_cost:,.2f}")
                        
                        # Display items in a table format
                        for item in items:
                            with st.container():
                                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                                with col1:
                                    st.write(f"• {item['item_name']}")
                                with col2:
                                    st.write(f"Qty: {item['quantity']}")
                                with col3:
                                    if item.get('estimated_price'):
                                        st.write(f"₹{float(item['estimated_price']):,.2f}")
                                with col4:
                                    if st.checkbox("Done", value=item['completed'], key=f"item_{item['id']}"):
                                        update_item_status(item['id'], True)
                                        st.rerun()
                                    else:
                                        update_item_status(item['id'], False)
                    else:
                        st.info("No items in this list yet")
                    
                    # List actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Edit List", key=f"edit_list_{shopping_list['id']}"):
                            st.session_state[f"editing_list_{shopping_list['id']}"] = True
                    with col2:
                        if st.button("Mark Complete", key=f"complete_list_{shopping_list['id']}"):
                            for item in items:
                                update_item_status(item['id'], True)
                            st.success("List marked as complete!")
                            st.rerun()
                    with col3:
                        if st.button("Delete List", key=f"delete_{shopping_list['id']}"):
                            delete_shopping_list(shopping_list['id'])
                            st.success("List deleted")
                            st.rerun()
        
        with tab2:
            # Shopping List Statistics
            col1, col2 = st.columns(2)
            
            with col1:
                # List completion status
                total_lists = len(shopping_lists)
                completed_lists = sum(1 for l in shopping_lists if l.get('completed', False))
                active_lists = total_lists - completed_lists
                
                fig = px.pie(
                    values=[active_lists, completed_lists],
                    names=["Active Lists", "Completed Lists"],
                    title="List Completion Status"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Priority distribution
                priority_counts = {}
                for l in shopping_lists:
                    priority = l.get('priority', 'Not Set')
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
                fig = px.bar(
                    x=list(priority_counts.keys()),
                    y=list(priority_counts.values()),
                    title="Lists by Priority",
                    labels={'x': 'Priority', 'y': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Items statistics
            st.subheader("Items Statistics")
            all_items = []
            for l in shopping_lists:
                items = get_list_items(l['id'])
                all_items.extend(items)
            
            if all_items:
                # Completion rate by list
                completion_data = []
                for l in shopping_lists:
                    items = get_list_items(l['id'])
                    if items:
                        completed = sum(1 for item in items if item['completed'])
                        completion_data.append({
                            'list_name': l['name'],
                            'completion_rate': (completed / len(items)) * 100
                        })
                
                df = pd.DataFrame(completion_data)
                fig = px.bar(
                    df,
                    x='list_name',
                    y='completion_rate',
                    title="Completion Rate by List",
                    labels={'completion_rate': 'Completion Rate (%)', 'list_name': 'List Name'}
                )
                st.plotly_chart(fig, use_container_width=True)

def show_budget_planning():
    """Display budget planning interface"""
    st.header("💰 Budget Planning")
    
    # Add filters and quick actions
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        current_month = datetime.now().month
        month = st.selectbox("Month", range(1, 13), index=current_month - 1,
                           format_func=lambda x: datetime(2024, x, 1).strftime("%B"))
    with col2:
        current_year = datetime.now().year
        year = st.selectbox("Year", range(current_year - 1, current_year + 2), index=1)
    with col3:
        if st.button("Copy Last Month's Budget"):
            copy_previous_month_budget(st.session_state.user_id, month, year)
            st.success("Budget copied from previous month!")
            st.rerun()
    
    # Add/Edit Budget Form with auto-refresh
    with st.expander("Set Budget", expanded=False):
        with st.form("budget_form"):
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox("Category", get_budget_categories())
            with col2:
                amount = st.number_input("Budget Amount (₹)", min_value=0.01, step=10.0)
            
            submit = st.form_submit_button("Set Budget")
            if submit:
                set_budget(st.session_state.user_id, category, amount, month, year)
                st.success(f"Budget set for {category}")
                st.rerun()
    
    # Display Budget Summary with real-time updates
    st.subheader(f"Budget Summary for {datetime(year, month, 1).strftime('%B %Y')}")
    
    # Get budget summary
    summary = get_budget_summary(st.session_state.user_id, month, year)
    
    if not summary:
        st.info("No budgets set for this month. Add your first budget above!")
    else:
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Overview", "Details", "Analysis"])
        
        with tab1:
            # Summary metrics
            total_budget = sum(item['budget_amount'] for item in summary)
            total_spent = sum(item['spent'] for item in summary)
            total_remaining = total_budget - total_spent
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Budget", f"₹{total_budget:,.2f}")
            with col2:
                st.metric("Total Spent", f"₹{total_spent:,.2f}")
            with col3:
                st.metric("Total Remaining", f"₹{total_remaining:,.2f}")
            
            # Overall progress bar
            overall_progress = (total_spent / total_budget * 100) if total_budget > 0 else 0
            st.progress(
                min(overall_progress / 100, 1.0),
                text=f"Overall Progress: {overall_progress:.1f}%"
            )
        
        with tab2:
            # Detailed budget breakdown
            for item in summary:
                with st.expander(f"{item['category']} - ₹{item['budget_amount']:,.2f}"):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        progress = item['percent_used']
                        color = "normal" if progress <= 80 else "warning" if progress <= 100 else "error"
                        st.progress(
                            min(progress / 100, 1.0),
                            text=f"Spent: ₹{item['spent']:,.2f} / Budget: ₹{item['budget_amount']:,.2f}"
                        )
                    with col2:
                        st.write(f"Remaining: ₹{item['remaining']:,.2f}")
                    with col3:
                        if st.button("Edit", key=f"edit_budget_{item['category']}"):
                            st.session_state[f"editing_budget_{item['category']}"] = True
                    
                    # Edit budget form
                    if st.session_state.get(f"editing_budget_{item['category']}", False):
                        with st.form(f"edit_budget_form_{item['category']}"):
                            new_amount = st.number_input(
                                "New Budget Amount (₹)",
                                value=float(item['budget_amount']),
                                min_value=0.01,
                                step=10.0
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Save"):
                                    set_budget(st.session_state.user_id, item['category'], new_amount, month, year)
                                    st.session_state[f"editing_budget_{item['category']}"] = False
                                    st.success("Budget updated!")
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("Cancel"):
                                    st.session_state[f"editing_budget_{item['category']}"] = False
                                    st.rerun()
        
        with tab3:
            # Budget analysis and visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                # Budget vs. Actual Spending
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name="Budget",
                    x=[item['category'] for item in summary],
                    y=[item['budget_amount'] for item in summary],
                    marker_color='lightgrey'
                ))
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
            
            with col2:
                # Spending Distribution
                fig = px.pie(
                    values=[item['spent'] for item in summary],
                    names=[item['category'] for item in summary],
                    title="Spending Distribution by Category"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Budget utilization analysis
            st.subheader("Budget Utilization Analysis")
            utilization_data = []
            for item in summary:
                utilization_data.append({
                    'category': item['category'],
                    'utilization': item['percent_used'],
                    'status': 'Under Budget' if item['percent_used'] <= 80 else
                             'Warning' if item['percent_used'] <= 100 else
                             'Over Budget'
                })
            
            df = pd.DataFrame(utilization_data)
            fig = px.bar(
                df,
                x='category',
                y='utilization',
                color='status',
                title="Budget Utilization by Category",
                labels={'utilization': 'Utilization (%)', 'category': 'Category'}
            )
            st.plotly_chart(fig, use_container_width=True)

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
    
    # Add funny comment about time management
    st.markdown("""
        <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-bottom: 1rem;'>
            <p>⏰ Time flies like an arrow, but family events fly like a boomerang - they always come back!</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Calendar Navigation and Filters
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        current_month = datetime.now().month
        month = st.selectbox("Month", range(1, 13), index=current_month - 1,
                           format_func=lambda x: datetime(2024, x, 1).strftime("%B"))
    with col2:
        current_year = datetime.now().year
        year = st.selectbox("Year", range(current_year - 1, current_year + 3), index=1)
    with col3:
        view_type = st.selectbox("View", ["Month", "Week", "Upcoming"])
    with col4:
        if st.button("Add Event", type="primary"):
            st.session_state.show_new_event_form = True
    
    # Add New Event with improved UI
    if st.session_state.get("show_new_event_form", False):
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
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Add Event"):
                        if title:
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
                            st.session_state.show_new_event_form = False
                            st.rerun()
                with col2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_new_event_form = False
                        st.rerun()
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Calendar", "Statistics"])
    
    with tab1:
        # Display Calendar View
        if view_type == "Month":
            # Get all events for the month
            events_data = get_events_by_month(st.session_state.user_id, year, month)
            events = events_data['events']
            
            # Create calendar grid
            cal = calendar.monthcalendar(year, month)
            
            # Create calendar table with improved styling
            st.markdown(f"""
                <div style='text-align: center; padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-bottom: 1rem;'>
                    <h2>{calendar.month_name[month]} {year}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            # Create week header with improved styling
            week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            cols = st.columns(7)
            for i, col in enumerate(cols):
                col.markdown(f"""
                    <div style='text-align: center; padding: 0.5rem; background-color: var(--surface-color); border-radius: 4px;'>
                        <strong>{week_days[i]}</strong>
                    </div>
                """, unsafe_allow_html=True)
            
            # Create calendar grid with improved styling
            for week in cal:
                cols = st.columns(7)
                for i, day in enumerate(cols):
                    with day:
                        if week[i] != 0:
                            date = datetime(year, month, week[i])
                            day_events = [e for e in events if datetime.strptime(e['start_date'], '%Y-%m-%d %H:%M:%S').date() == date.date()]
                            
                            # Display day and events with improved styling
                            st.markdown(f"""
                                <div style='padding: 0.5rem; background-color: var(--surface-color); border-radius: 4px; min-height: 100px;'>
                                    <strong>{week[i]}</strong>
                            """, unsafe_allow_html=True)
                            
                            for event in day_events:
                                event_time = datetime.strptime(event['start_date'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')
                                st.markdown(f"""
                                    <div style='padding: 0.25rem; background-color: var(--primary-color-light); border-radius: 4px; margin: 0.25rem 0;'>
                                        <small><strong>{event_time}</strong> - {event['title']}</small>
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            st.markdown("</div>", unsafe_allow_html=True)
        
        elif view_type == "Week":
            # Get current week's start and end dates
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            events_data = get_events(
                st.session_state.user_id,
                week_start.strftime('%Y-%m-%d'),
                week_end.strftime('%Y-%m-%d')
            )
            events = events_data['events']
            
            # Display week view with improved styling
            st.markdown(f"""
                <div style='text-align: center; padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-bottom: 1rem;'>
                    <h2>Week of {week_start.strftime('%B %d, %Y')}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            for i in range(7):
                current_date = week_start + timedelta(days=i)
                day_events = [e for e in events if datetime.strptime(e['start_date'], '%Y-%m-%d %H:%M:%S').date() == current_date.date()]
                
                with st.expander(f"{current_date.strftime('%A, %B %d')}", expanded=True):
                    if day_events:
                        for event in day_events:
                            event_time = datetime.strptime(event['start_date'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')
                            st.markdown(f"""
                                <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin: 0.5rem 0;'>
                                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                                        <div>
                                            <strong>{event_time}</strong> - {event['title']}<br>
                                            <small>{event['description']}</small>
                                        </div>
                                        <div>
                                            <button onclick="deleteEvent('{event['id']}')" style='padding: 0.25rem 0.5rem; background-color: var(--error-color); color: white; border: none; border-radius: 4px; cursor: pointer;'>
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No events scheduled")
        
        else:  # Upcoming view
            events = get_upcoming_events(st.session_state.user_id)
            
            st.markdown("""
                <div style='text-align: center; padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-bottom: 1rem;'>
                    <h2>Upcoming Events</h2>
                </div>
            """, unsafe_allow_html=True)
            
            if events:
                for event in events:
                    event_date = datetime.strptime(event['start_date'], '%Y-%m-%d %H:%M:%S')
                    with st.expander(
                        f"{event_date.strftime('%A, %B %d')} - {event['title']}", 
                        expanded=True
                    ):
                        st.markdown(f"""
                            <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px;'>
                                <p><strong>Time:</strong> {event_date.strftime('%I:%M %p')}</p>
                                <p><strong>Description:</strong> {event['description']}</p>
                                {f"<p><strong>Reminder:</strong> {datetime.strptime(event['reminder_time'], '%Y-%m-%d %H:%M:%S').strftime('%B %d, %I:%M %p')}</p>" if event['reminder'] else ""}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("Delete", key=f"del_upcoming_{event['id']}"):
                            delete_event(event['id'])
                            st.success("Event deleted")
                            st.rerun()
            else:
                st.info("No upcoming events in the next 7 days")
    
    with tab2:
        # Calendar Statistics
        col1, col2 = st.columns(2)
        
        with col1:
            # Events by category
            all_events_data = get_events(st.session_state.user_id)
            all_events = all_events_data['events']
            category_counts = {}
            for event in all_events:
                category = event['description'].split(':')[0]
                category_counts[category] = category_counts.get(category, 0) + 1
            
            fig = px.pie(
                values=list(category_counts.values()),
                names=list(category_counts.keys()),
                title="Events by Category"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Events by month
            monthly_counts = {}
            for event in all_events:
                event_date = datetime.strptime(event['start_date'], '%Y-%m-%d %H:%M:%S')
                month_key = event_date.strftime('%B %Y')
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
            
            # Create DataFrame for the bar chart
            df_monthly = pd.DataFrame({
                'Month': list(monthly_counts.keys()),
                'Count': list(monthly_counts.values())
            })
            
            fig = px.bar(
                df_monthly,
                x='Month',
                y='Count',
                title="Events by Month"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Upcoming events timeline
        st.subheader("Upcoming Events Timeline")
        upcoming_events = get_upcoming_events(st.session_state.user_id, days=30)
        if upcoming_events:
            timeline_data = []
            for event in upcoming_events:
                event_date = datetime.strptime(event['start_date'], '%Y-%m-%d %H:%M:%S')
                timeline_data.append({
                    'date': event_date,
                    'title': event['title'],
                    'category': event['description'].split(':')[0]
                })
            
            df = pd.DataFrame(timeline_data)
            fig = px.scatter(
                df,
                x='date',
                y='category',
                text='title',
                title="Upcoming Events Timeline"
            )
            fig.update_traces(textposition='top center')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No upcoming events in the next 30 days")

def show_goals():
    """Display goals tracking interface"""
    st.header("🎯 Goals & Milestones")
    
    # Add funny comment about goal setting
    st.markdown("""
        <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-bottom: 1rem;'>
            <p>🎯 Setting goals is like making a sandwich - the more layers you add, the better it gets!</p>
        </div>
    """, unsafe_allow_html=True)
    
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
                    target_amount = st.number_input("Target Amount (₹)", min_value=0.0, step=100.0)
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
        # Display goals in a kanban-style board
        status_cols = st.columns(len(get_goal_status_types()))

def show_settings():
    """Display settings and user profile interface"""
    st.header("⚙️ Settings")
    
    # Add funny comment about settings
    st.markdown("""
        <div style='padding: 1rem; background-color: var(--surface-color); border-radius: 8px; margin-bottom: 1rem;'>
            <p>⚙️ Settings are like a family photo - they need to be updated every once in a while!</p>
        </div>
    """, unsafe_allow_html=True)
    
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
    # Show login/register page if not logged in
    if not st.session_state.user_id:
        show_login()
    else:
        # Show main application
        show_main_app()
        
        # Add footer
        st.markdown("""
            <div class='footer'>
                <p style='margin: 0; color: var(--text-secondary);'>
                    Family Planner - Created by Jithin
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Log performance summary at the end of each session
        log_performance_summary()

if __name__ == "__main__":
    main() 