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

# Set page configuration
st.set_page_config(
    page_title="Family Planner",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Initialize database
conn = get_db_connection()
create_tables(conn)
conn.close()

def show_login():
    """Display login form"""
    st.header("Login")
    
    # Add tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                user = verify_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user['id']
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register")
            
            if submit:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    user_id = create_user(new_username, new_password, new_email)
                    if user_id:
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username or email already exists")

def show_home():
    """Display home dashboard"""
    st.header("Welcome to Family Planner")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Quick Stats")
        # Get current month's transactions
        current_month = datetime.now().month
        current_year = datetime.now().year
        transactions = get_transactions(st.session_state.user_id)
        
        # Calculate total income and expenses
        income = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'income')
        expenses = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'expense')
        
        st.metric(label="Total Income", value=f"${income:,.2f}")
        st.metric(label="Total Expenses", value=f"${expenses:,.2f}")
        st.metric(label="Balance", value=f"${income - expenses:,.2f}")
    
    with col2:
        st.subheader("📅 Quick Actions")
        if st.button("Add Transaction"):
            st.session_state.page = "Financial Dashboard"
            st.rerun()
        if st.button("Create Shopping List"):
            st.session_state.page = "Shopping Lists"
            st.rerun()

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
    
    # Display transactions
    st.subheader("Recent Transactions")
    transactions = get_transactions(st.session_state.user_id)
    if transactions:
        # Create a DataFrame for plotting
        import pandas as pd
        df = pd.DataFrame(transactions)
        
        # Plot expenses by category
        expenses_by_category = df[df['transaction_type'] == 'expense'].groupby('category')['amount'].sum()
        fig = px.pie(
            values=expenses_by_category.values,
            names=expenses_by_category.index,
            title="Expenses by Category"
        )
        st.plotly_chart(fig)
        
        # Display transaction list
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
        # Display goals in a kanban-style board
        status_cols = st.columns(len(get_goal_status_types()))
        
        for idx, status in enumerate(get_goal_status_types()):
            with status_cols[idx]:
                st.markdown(f"### {status}")
                status_goals = [g for g in goals if g['status'] == status]
                
                for goal in status_goals:
                    with st.container():
                        # Goal card
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
    st.title("👨‍👩‍👧‍👦 Family Planner")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Home", "Financial Dashboard", "Budget Planning", "Shopping Lists", 
         "Calendar", "Family Profiles", "Goals", "Settings"]
    )
    
    if not st.session_state.logged_in:
        show_login()
    else:
        if page == "Home":
            show_home()
        elif page == "Financial Dashboard":
            show_financial_dashboard()
        elif page == "Shopping Lists":
            show_shopping_lists()
        elif page == "Budget Planning":
            show_budget_planning()
        elif page == "Family Profiles":
            show_family_profiles()
        elif page == "Calendar":
            show_calendar()
        elif page == "Goals":
            show_goals()
        elif page == "Settings":
            show_settings()
        # Add other page conditions here

if __name__ == "__main__":
    main() 