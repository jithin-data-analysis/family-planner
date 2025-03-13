import sqlite3
import os
import bcrypt
from datetime import datetime, timedelta

def get_db_connection():
    """Create a database connection"""
    try:
        # Try to use the data directory in the project root
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    except:
        # If that fails, use the current directory
        data_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Use absolute path for database file
    db_path = os.path.join(data_dir, 'family_planner.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# User operations
def create_user(username, password, email):
    """Create a new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    try:
        cursor.execute(
            'INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
            (username, hashed, email)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def verify_user(username, password):
    """Verify user credentials"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user['password_hash']):
        return dict(user)
    return None

# Transaction operations
def add_transaction(user_id, amount, category, description, transaction_type):
    """Add a new transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO transactions 
           (user_id, amount, category, description, transaction_type)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, amount, category, description, transaction_type)
    )
    conn.commit()
    conn.close()

def get_transactions(user_id, start_date=None, end_date=None):
    """Get user transactions with optional date range"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM transactions WHERE user_id = ?'
    params = [user_id]
    
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    conn.close()
    return [dict(tx) for tx in transactions]

# Budget operations
def set_budget(user_id, category, amount, month, year):
    """Set or update budget for a category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''INSERT OR REPLACE INTO budgets 
           (user_id, category, amount, month, year)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, category, amount, month, year)
    )
    conn.commit()
    conn.close()

def get_budgets(user_id, month, year):
    """Get all budgets for a specific month and year"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM budgets WHERE user_id = ? AND month = ? AND year = ?',
        (user_id, month, year)
    )
    budgets = cursor.fetchall()
    conn.close()
    return [dict(budget) for budget in budgets]

# Shopping List operations
def create_shopping_list(user_id, name):
    """Create a new shopping list"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shopping_lists (user_id, name) VALUES (?, ?)',
        (user_id, name)
    )
    list_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return list_id

def get_shopping_lists(user_id):
    """Get all shopping lists for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shopping_lists WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    lists = cursor.fetchall()
    conn.close()
    return [dict(lst) for lst in lists]

def add_list_item(list_id, item_name, quantity=1):
    """Add an item to a shopping list"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shopping_list_items (list_id, item_name, quantity) VALUES (?, ?, ?)',
        (list_id, item_name, quantity)
    )
    conn.commit()
    conn.close()

def get_list_items(list_id):
    """Get all items in a shopping list"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shopping_list_items WHERE list_id = ?', (list_id,))
    items = cursor.fetchall()
    conn.close()
    return [dict(item) for item in items]

def update_item_status(item_id, completed):
    """Update the completion status of a shopping list item"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE shopping_list_items SET completed = ? WHERE id = ?',
        (completed, item_id)
    )
    conn.commit()
    conn.close()

def delete_shopping_list(list_id):
    """Delete a shopping list and all its items"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM shopping_list_items WHERE list_id = ?', (list_id,))
    cursor.execute('DELETE FROM shopping_lists WHERE id = ?', (list_id,))
    conn.commit()
    conn.close()

# Enhanced Budget operations
def get_budget_categories():
    """Get list of predefined budget categories"""
    return [
        "Groceries", "Utilities", "Rent/Mortgage", "Transportation",
        "Healthcare", "Entertainment", "Education", "Shopping",
        "Savings", "Investments", "Insurance", "Dining Out",
        "Travel", "Gifts", "Other"
    ]

def get_budget_summary(user_id, month, year):
    """Get budget summary with actual spending for each category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all budgets for the month
    budgets = get_budgets(user_id, month, year)
    
    # Get all transactions for the month
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    cursor.execute('''
        SELECT category, SUM(amount) as spent
        FROM transactions
        WHERE user_id = ? AND transaction_type = 'expense'
        AND date >= ? AND date < ?
        GROUP BY category
    ''', (user_id, start_date, end_date))
    
    spending = {row['category']: float(row['spent']) for row in cursor.fetchall()}
    
    # Combine budget and actual spending data
    summary = []
    for budget in budgets:
        category = budget['category']
        amount = float(budget['amount'])
        spent = spending.get(category, 0.0)
        remaining = amount - spent
        percent_used = (spent / amount * 100) if amount > 0 else 0
        
        summary.append({
            'category': category,
            'budget_amount': amount,
            'spent': spent,
            'remaining': remaining,
            'percent_used': percent_used
        })
    
    conn.close()
    return summary

def delete_budget(user_id, category, month, year):
    """Delete a budget category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM budgets WHERE user_id = ? AND category = ? AND month = ? AND year = ?',
        (user_id, category, month, year)
    )
    conn.commit()
    conn.close()

# Family Member operations
def add_family_member(user_id, name, relationship, birth_date=None):
    """Add a new family member"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO family_members (user_id, name, relationship, birth_date) VALUES (?, ?, ?, ?)',
        (user_id, name, relationship, birth_date)
    )
    member_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return member_id

def get_family_members(user_id):
    """Get all family members for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM family_members WHERE user_id = ?', (user_id,))
    members = cursor.fetchall()
    conn.close()
    return [dict(member) for member in members]

def update_family_member(member_id, name, relationship, birth_date):
    """Update family member details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE family_members 
           SET name = ?, relationship = ?, birth_date = ?
           WHERE id = ?''',
        (name, relationship, birth_date, member_id)
    )
    conn.commit()
    conn.close()

def delete_family_member(member_id):
    """Delete a family member"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM family_members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()

def get_relationship_types():
    """Get list of predefined relationship types"""
    return [
        "Spouse/Partner", "Child", "Parent", "Sibling",
        "Grandparent", "Grandchild", "Uncle/Aunt",
        "Niece/Nephew", "Cousin", "Other"
    ]

# Event operations
def add_event(user_id, title, description, start_date, end_date=None, reminder=False, reminder_time=None):
    """Add a new event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO events 
           (user_id, title, description, start_date, end_date, reminder, reminder_time)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, title, description, start_date, end_date, reminder, reminder_time)
    )
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return event_id

def get_events(user_id, start_date=None, end_date=None):
    """Get events within a date range"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM events WHERE user_id = ?'
    params = [user_id]
    
    if start_date:
        query += ' AND start_date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND start_date <= ?'
        params.append(end_date)
    
    query += ' ORDER BY start_date ASC'
    cursor.execute(query, params)
    events = cursor.fetchall()
    conn.close()
    return [dict(event) for event in events]

def update_event(event_id, title, description, start_date, end_date=None, reminder=False, reminder_time=None):
    """Update event details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE events 
           SET title = ?, description = ?, start_date = ?, 
               end_date = ?, reminder = ?, reminder_time = ?
           WHERE id = ?''',
        (title, description, start_date, end_date, reminder, reminder_time, event_id)
    )
    conn.commit()
    conn.close()

def delete_event(event_id):
    """Delete an event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()

def get_upcoming_events(user_id, days=7):
    """Get upcoming events for the next N days"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute(
        '''SELECT * FROM events 
           WHERE user_id = ? AND start_date >= ? AND start_date <= ?
           ORDER BY start_date ASC''',
        (user_id, start_date, end_date)
    )
    events = cursor.fetchall()
    conn.close()
    return [dict(event) for event in events]

def get_events_by_month(user_id, year, month):
    """Get all events for a specific month"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    cursor.execute(
        '''SELECT * FROM events 
           WHERE user_id = ? AND start_date >= ? AND start_date < ?
           ORDER BY start_date ASC''',
        (user_id, start_date, end_date)
    )
    events = cursor.fetchall()
    conn.close()
    return [dict(event) for event in events]

def get_event_categories():
    """Get list of predefined event categories"""
    return [
        "Family Gathering", "Birthday", "Anniversary", "Doctor's Appointment",
        "School Event", "Sports/Activity", "Holiday", "Travel",
        "Bill Payment", "Shopping", "Other"
    ]

def get_goal_categories():
    """Get list of predefined goal categories"""
    return [
        "Financial", "Education", "Health", "Family", "Career",
        "Home", "Travel", "Personal Development", "Other"
    ]

def get_goal_status_types():
    """Get list of predefined goal status types"""
    return [
        "Not Started", "In Progress", "Completed", "On Hold"
    ]

def add_goal(user_id, title, category, description, target_date, target_amount=None):
    """Add a new goal"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO goals 
           (user_id, title, category, description, target_date, target_amount, status, progress)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, title, category, description, target_date, target_amount, "Not Started", 0)
    )
    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return goal_id

def get_goals(user_id, category=None, status=None):
    """Get goals with optional filters"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM goals WHERE user_id = ?'
    params = [user_id]
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    query += ' ORDER BY target_date ASC'
    cursor.execute(query, params)
    goals = cursor.fetchall()
    conn.close()
    return [dict(goal) for goal in goals]

def update_goal(goal_id, title=None, category=None, description=None, 
                target_date=None, target_amount=None, status=None, progress=None):
    """Update goal details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if title is not None:
        updates.append('title = ?')
        params.append(title)
    if category is not None:
        updates.append('category = ?')
        params.append(category)
    if description is not None:
        updates.append('description = ?')
        params.append(description)
    if target_date is not None:
        updates.append('target_date = ?')
        params.append(target_date)
    if target_amount is not None:
        updates.append('target_amount = ?')
        params.append(target_amount)
    if status is not None:
        updates.append('status = ?')
        params.append(status)
    if progress is not None:
        updates.append('progress = ?')
        params.append(progress)
    
    if updates:
        query = f'''UPDATE goals SET {', '.join(updates)} WHERE id = ?'''
        params.append(goal_id)
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

def delete_goal(goal_id):
    """Delete a goal"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
    conn.commit()
    conn.close()

def add_goal_milestone(goal_id, title, target_date, completed=False):
    """Add a milestone for a goal"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO goal_milestones 
           (goal_id, title, target_date, completed)
           VALUES (?, ?, ?, ?)''',
        (goal_id, title, target_date, completed)
    )
    milestone_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return milestone_id

def get_goal_milestones(goal_id):
    """Get all milestones for a goal"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM goal_milestones WHERE goal_id = ? ORDER BY target_date ASC', (goal_id,))
    milestones = cursor.fetchall()
    conn.close()
    return [dict(milestone) for milestone in milestones]

def update_milestone_status(milestone_id, completed):
    """Update milestone completion status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE goal_milestones SET completed = ? WHERE id = ?',
        (completed, milestone_id)
    )
    conn.commit()
    conn.close()

def delete_milestone(milestone_id):
    """Delete a milestone"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM goal_milestones WHERE id = ?', (milestone_id,))
    conn.commit()
    conn.close()

# User Settings and Profile operations
def update_user_profile(user_id, email=None, password=None):
    """Update user profile information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if email is not None:
        updates.append('email = ?')
        params.append(email)
    if password is not None:
        updates.append('password_hash = ?')
        params.append(hash_password(password))
    
    if updates:
        query = f'''UPDATE users SET {', '.join(updates)} WHERE id = ?'''
        params.append(user_id)
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

def get_user_data(user_id):
    """Get all user data for export"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user profile
    cursor.execute('SELECT username, email, created_at FROM users WHERE id = ?', (user_id,))
    user_data = dict(cursor.fetchone())
    
    # Get transactions
    cursor.execute('SELECT * FROM transactions WHERE user_id = ?', (user_id,))
    user_data['transactions'] = [dict(tx) for tx in cursor.fetchall()]
    
    # Get budgets
    cursor.execute('SELECT * FROM budgets WHERE user_id = ?', (user_id,))
    user_data['budgets'] = [dict(budget) for budget in cursor.fetchall()]
    
    # Get family members
    cursor.execute('SELECT * FROM family_members WHERE user_id = ?', (user_id,))
    user_data['family_members'] = [dict(member) for member in cursor.fetchall()]
    
    # Get events
    cursor.execute('SELECT * FROM events WHERE user_id = ?', (user_id,))
    user_data['events'] = [dict(event) for event in cursor.fetchall()]
    
    # Get goals and their milestones
    cursor.execute('SELECT * FROM goals WHERE user_id = ?', (user_id,))
    goals = [dict(goal) for goal in cursor.fetchall()]
    for goal in goals:
        cursor.execute('SELECT * FROM goal_milestones WHERE goal_id = ?', (goal['id'],))
        goal['milestones'] = [dict(milestone) for milestone in cursor.fetchall()]
    user_data['goals'] = goals
    
    # Get shopping lists and their items
    cursor.execute('SELECT * FROM shopping_lists WHERE user_id = ?', (user_id,))
    lists = [dict(lst) for lst in cursor.fetchall()]
    for lst in lists:
        cursor.execute('SELECT * FROM shopping_list_items WHERE list_id = ?', (lst['id'],))
        lst['items'] = [dict(item) for item in cursor.fetchall()]
    user_data['shopping_lists'] = lists
    
    conn.close()
    return user_data

def import_user_data(user_id, data):
    """Import user data from a backup"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Import transactions
        for tx in data.get('transactions', []):
            cursor.execute(
                '''INSERT INTO transactions 
                   (user_id, amount, category, description, transaction_type, date)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, tx['amount'], tx['category'], tx['description'],
                 tx['transaction_type'], tx['date'])
            )
        
        # Import budgets
        for budget in data.get('budgets', []):
            cursor.execute(
                '''INSERT INTO budgets 
                   (user_id, category, amount, month, year)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, budget['category'], budget['amount'],
                 budget['month'], budget['year'])
            )
        
        # Import family members
        for member in data.get('family_members', []):
            cursor.execute(
                '''INSERT INTO family_members 
                   (user_id, name, relationship, birth_date)
                   VALUES (?, ?, ?, ?)''',
                (user_id, member['name'], member['relationship'], member['birth_date'])
            )
        
        # Import events
        for event in data.get('events', []):
            cursor.execute(
                '''INSERT INTO events 
                   (user_id, title, description, start_date, end_date, reminder, reminder_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, event['title'], event['description'], event['start_date'],
                 event['end_date'], event['reminder'], event['reminder_time'])
            )
        
        # Import goals and milestones
        for goal in data.get('goals', []):
            cursor.execute(
                '''INSERT INTO goals 
                   (user_id, title, category, description, target_date, target_amount, status, progress)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, goal['title'], goal['category'], goal['description'],
                 goal['target_date'], goal['target_amount'], goal['status'], goal['progress'])
            )
            goal_id = cursor.lastrowid
            
            for milestone in goal.get('milestones', []):
                cursor.execute(
                    '''INSERT INTO goal_milestones 
                       (goal_id, title, target_date, completed)
                       VALUES (?, ?, ?, ?)''',
                    (goal_id, milestone['title'], milestone['target_date'], milestone['completed'])
                )
        
        # Import shopping lists and items
        for lst in data.get('shopping_lists', []):
            cursor.execute(
                '''INSERT INTO shopping_lists 
                   (user_id, name, created_at)
                   VALUES (?, ?, ?)''',
                (user_id, lst['name'], lst['created_at'])
            )
            list_id = cursor.lastrowid
            
            for item in lst.get('items', []):
                cursor.execute(
                    '''INSERT INTO shopping_list_items 
                       (list_id, item_name, quantity, completed)
                       VALUES (?, ?, ?, ?)''',
                    (list_id, item['item_name'], item['quantity'], item['completed'])
                )
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_user_data(user_id):
    """Delete all user data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Delete all user-related data
        cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM budgets WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM family_members WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM events WHERE user_id = ?', (user_id,))
        
        # Delete goals and their milestones
        cursor.execute('SELECT id FROM goals WHERE user_id = ?', (user_id,))
        goal_ids = [row['id'] for row in cursor.fetchall()]
        for goal_id in goal_ids:
            cursor.execute('DELETE FROM goal_milestones WHERE goal_id = ?', (goal_id,))
        cursor.execute('DELETE FROM goals WHERE user_id = ?', (user_id,))
        
        # Delete shopping lists and their items
        cursor.execute('SELECT id FROM shopping_lists WHERE user_id = ?', (user_id,))
        list_ids = [row['id'] for row in cursor.fetchall()]
        for list_id in list_ids:
            cursor.execute('DELETE FROM shopping_list_items WHERE list_id = ?', (list_id,))
        cursor.execute('DELETE FROM shopping_lists WHERE user_id = ?', (user_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close() 