import sqlite3
import os
import bcrypt
from datetime import datetime, timedelta
from contextlib import contextmanager
import time
from functools import lru_cache
import threading
from utils import monitor_performance, record_cache_hit, record_cache_miss, log_performance_summary
import logging
from typing import Optional, Dict, List, Any
from config import DATABASE_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection pool settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
MAX_CONNECTIONS = 5

# Cache settings
CACHE_TTL = 300  # 5 minutes in seconds
MAX_CACHE_SIZE = 1000

# Add pagination settings
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'family_planner.db')

class DatabaseError(Exception):
    """Custom exception for database errors"""
    pass

class Cache:
    def __init__(self, ttl=CACHE_TTL):
        self.ttl = ttl
        self.cache = {}
        self.lock = threading.Lock()
    
    def get(self, key):
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                del self.cache[key]
            return None
    
    def set(self, key, value):
        with self.lock:
            if len(self.cache) >= MAX_CACHE_SIZE:
                # Remove oldest entry
                oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
                del self.cache[oldest_key]
            self.cache[key] = (value, time.time())
    
    def clear(self):
        with self.lock:
            self.cache.clear()

# Global cache instance
_cache = Cache()

def clear_cache():
    """Clear the cache"""
    _cache.clear()

class DatabaseConnectionPool:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connections = []
        self.in_use = set()
        self.lock = threading.Lock()
    
    def get_connection(self):
        with self.lock:
            # Try to reuse an existing connection
            for conn in self.connections:
                if conn not in self.in_use:
                    try:
                        # Test if connection is still valid
                        conn.execute("SELECT 1")
                        self.in_use.add(conn)
                        return conn
                    except sqlite3.Error:
                        self.connections.remove(conn)
            
            # Create new connection if pool is not full
            if len(self.connections) < MAX_CONNECTIONS:
                conn = sqlite3.connect(self.db_path, timeout=30)
                conn.row_factory = sqlite3.Row
                self.connections.append(conn)
                self.in_use.add(conn)
                return conn
            
            # Wait for an available connection
            for _ in range(MAX_RETRIES):
                time.sleep(RETRY_DELAY)
                for conn in self.connections:
                    if conn not in self.in_use:
                        self.in_use.add(conn)
                        return conn
            
            raise sqlite3.Error("Could not obtain database connection after maximum retries")
    
    def release_connection(self, conn):
        with self.lock:
            if conn in self.in_use:
                self.in_use.remove(conn)
    
    def close_all(self):
        with self.lock:
            for conn in self.connections:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self.connections.clear()
            self.in_use.clear()

# Global connection pool
_connection_pool = None

def get_db_connection():
    """Get database connection based on environment"""
    if DATABASE_URL.startswith('sqlite'):
        # SQLite connection (development)
        conn = sqlite3.connect('family_planner.db')
        conn.row_factory = sqlite3.Row
        return conn
    else:
        # PostgreSQL connection (production)
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables based on database type
    if DATABASE_URL.startswith('sqlite'):
        # SQLite table creation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Add other table creation statements...
    else:
        # PostgreSQL table creation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Add other table creation statements...
    
    conn.commit()
    conn.close()

def execute_query(query: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
    """Execute a query and return results with proper error handling"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                return [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                return None
    except sqlite3.Error as e:
        logger.error(f"Query execution error: {str(e)}")
        raise DatabaseError(f"Query execution failed: {str(e)}")

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# User operations
def create_user(username, password, email):
    """Create a new user"""
    with get_db_connection() as conn:
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

def verify_user(username, password):
    """Verify user credentials"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and verify_password(password, user['password_hash']):
            return dict(user)
        return None

# Transaction operations
def add_transaction(user_id, amount, category, description, transaction_type):
    """Add a new transaction"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO transactions 
               (user_id, amount, category, description, transaction_type)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, amount, category, description, transaction_type)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def get_transactions(user_id, start_date=None, end_date=None, page=1, page_size=DEFAULT_PAGE_SIZE):
    """Get user transactions with optional date range and pagination"""
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get total count for pagination
        count_query = 'SELECT COUNT(*) as total FROM transactions WHERE user_id = ?'
        count_params = [user_id]
        
        if start_date:
            count_query += ' AND date >= ?'
            count_params.append(start_date)
        if end_date:
            count_query += ' AND date <= ?'
            count_params.append(end_date)
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]  # Access first element directly
        
        # Get paginated transactions
        query = '''
            SELECT t.*, 
                   CASE 
                       WHEN t.transaction_type = 'expense' THEN -t.amount 
                       ELSE t.amount 
                   END as signed_amount
            FROM transactions t
            WHERE t.user_id = ?
        '''
        params = [user_id]
        
        if start_date:
            query += ' AND t.date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND t.date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY t.date DESC LIMIT ? OFFSET ?'
        params.extend([page_size, offset])
        
        cursor.execute(query, params)
        transactions = []
        for row in cursor.fetchall():
            transaction = {
                'id': row[0],
                'user_id': row[1],
                'amount': row[2],
                'category': row[3],
                'description': row[4],
                'transaction_type': row[5],
                'date': row[6],
                'signed_amount': row[7]
            }
            transactions.append(transaction)
        
        return {
            'transactions': transactions,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }

# Budget operations
def set_budget(user_id, category, amount, month, year):
    """Set or update budget for a category"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT OR REPLACE INTO budgets 
               (user_id, category, amount, month, year)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, category, amount, month, year)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def get_budgets(user_id, month, year):
    """Get all budgets for a specific month and year (cached)"""
    cache_key = f"budgets_{user_id}_{month}_{year}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        record_cache_hit()
        return cached_result
    
    record_cache_miss()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM budgets WHERE user_id = ? AND month = ? AND year = ?',
            (user_id, month, year)
        )
        budgets = [dict(budget) for budget in cursor.fetchall()]
        _cache.set(cache_key, budgets)
        return budgets

# Shopping List operations
def create_shopping_list(user_id, name):
    """Create a new shopping list"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO shopping_lists (user_id, name) VALUES (?, ?)',
            (user_id, name)
        )
        list_id = cursor.lastrowid
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()
        return list_id

def get_shopping_lists(user_id):
    """Get all shopping lists for a user (cached)"""
    cache_key = f"shopping_lists_{user_id}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        record_cache_hit()
        return cached_result
    
    record_cache_miss()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM shopping_lists WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        lists = [dict(lst) for lst in cursor.fetchall()]
        _cache.set(cache_key, lists)
        return lists

def add_list_item(list_id, item_name, quantity=1):
    """Add an item to a shopping list"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO shopping_list_items (list_id, item_name, quantity) VALUES (?, ?, ?)',
            (list_id, item_name, quantity)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def get_list_items(list_id):
    """Get all items in a shopping list (cached)"""
    cache_key = f"list_items_{list_id}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        record_cache_hit()
        return cached_result
    
    record_cache_miss()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM shopping_list_items WHERE list_id = ?', (list_id,))
        items = [dict(item) for item in cursor.fetchall()]
        _cache.set(cache_key, items)
        return items

def update_item_status(item_id, completed):
    """Update the completion status of a shopping list item"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE shopping_list_items SET completed = ? WHERE id = ?',
            (completed, item_id)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def delete_shopping_list(list_id):
    """Delete a shopping list and all its items"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM shopping_list_items WHERE list_id = ?', (list_id,))
        cursor.execute('DELETE FROM shopping_lists WHERE id = ?', (list_id,))
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

# Enhanced Budget operations
@lru_cache(maxsize=100)
def get_budget_categories():
    """Get list of predefined budget categories (cached)"""
    return [
        "Groceries", "Utilities", "Rent/Mortgage", "Transportation",
        "Healthcare", "Entertainment", "Education", "Shopping",
        "Savings", "Investments", "Insurance", "Dining Out",
        "Travel", "Gifts", "Other"
    ]

def get_budget_summary(user_id, month, year):
    """Get budget summary with actual spending for each category (cached)"""
    cache_key = f"budget_summary_{user_id}_{month}_{year}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        record_cache_hit()
        return cached_result
    
    record_cache_miss()
    with get_db_connection() as conn:
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
        
        _cache.set(cache_key, summary)
        return summary

def delete_budget(user_id, category, month, year):
    """Delete a budget category"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM budgets WHERE user_id = ? AND category = ? AND month = ? AND year = ?',
            (user_id, category, month, year)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

# Family Member operations
def add_family_member(user_id, name, relationship, birth_date=None):
    """Add a new family member"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO family_members (user_id, name, relationship, birth_date) VALUES (?, ?, ?, ?)',
            (user_id, name, relationship, birth_date)
        )
        member_id = cursor.lastrowid
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()
        return member_id

def get_family_members(user_id):
    """Get all family members for a user (cached)"""
    cache_key = f"family_members_{user_id}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        record_cache_hit()
        return cached_result
    
    record_cache_miss()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM family_members WHERE user_id = ?', (user_id,))
        members = [dict(member) for member in cursor.fetchall()]
        _cache.set(cache_key, members)
        return members

def update_family_member(member_id, name, relationship, birth_date):
    """Update family member details"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''UPDATE family_members 
               SET name = ?, relationship = ?, birth_date = ?
               WHERE id = ?''',
            (name, relationship, birth_date, member_id)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def delete_family_member(member_id):
    """Delete a family member"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM family_members WHERE id = ?', (member_id,))
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

@lru_cache(maxsize=100)
def get_relationship_types():
    """Get list of predefined relationship types (cached)"""
    return [
        "Spouse/Partner", "Child", "Parent", "Sibling",
        "Grandparent", "Grandchild", "Uncle/Aunt",
        "Niece/Nephew", "Cousin", "Other"
    ]

# Event operations
def add_event(user_id, title, description, start_date, end_date=None, reminder=False, reminder_time=None):
    """Add a new event"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO events 
               (user_id, title, description, start_date, end_date, reminder, reminder_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, title, description, start_date, end_date, reminder, reminder_time)
        )
        event_id = cursor.lastrowid
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()
        return event_id

def get_events(user_id, start_date=None, end_date=None, page=1, page_size=DEFAULT_PAGE_SIZE):
    """Get events within a date range with pagination"""
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get total count for pagination
        count_query = 'SELECT COUNT(*) as total FROM events WHERE user_id = ?'
        count_params = [user_id]
        
        if start_date:
            count_query += ' AND start_date >= ?'
            count_params.append(start_date)
        if end_date:
            count_query += ' AND start_date <= ?'
            count_params.append(end_date)
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']
        
        # Get paginated events
        query = '''
            SELECT e.*,
                   CASE 
                       WHEN e.reminder = 1 AND e.reminder_time <= datetime('now', '+1 hour') 
                       THEN 1 
                       ELSE 0 
                   END as needs_reminder
            FROM events e
            WHERE e.user_id = ?
        '''
        params = [user_id]
        
        if start_date:
            query += ' AND e.start_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND e.start_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY e.start_date ASC LIMIT ? OFFSET ?'
        params.extend([page_size, offset])
        
        cursor.execute(query, params)
        events = [dict(event) for event in cursor.fetchall()]
        
        return {
            'events': events,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }

def update_event(event_id, title, description, start_date, end_date=None, reminder=False, reminder_time=None):
    """Update event details"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''UPDATE events 
               SET title = ?, description = ?, start_date = ?, 
                   end_date = ?, reminder = ?, reminder_time = ?
               WHERE id = ?''',
            (title, description, start_date, end_date, reminder, reminder_time, event_id)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def delete_event(event_id):
    """Delete an event"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def get_upcoming_events(user_id, days=7, limit=10):
    """Get upcoming events for the next N days with limit (cached)"""
    cache_key = f"upcoming_events_{user_id}_{days}_{limit}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        record_cache_hit()
        return cached_result
    
    record_cache_miss()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        query = '''
            SELECT e.*,
                   CASE 
                       WHEN e.reminder = 1 AND e.reminder_time <= datetime('now', '+1 hour') 
                       THEN 1 
                       ELSE 0 
                   END as needs_reminder
            FROM events e
            WHERE e.user_id = ? 
            AND e.start_date >= ? 
            AND e.start_date <= ?
            ORDER BY e.start_date ASC
            LIMIT ?
        '''
        
        cursor.execute(query, (user_id, start_date, end_date, limit))
        events = [dict(event) for event in cursor.fetchall()]
        _cache.set(cache_key, events)
        return events

def get_events_by_month(user_id, year, month, page=1, page_size=DEFAULT_PAGE_SIZE):
    """Get all events for a specific month with pagination"""
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        # Get total count for pagination
        count_query = '''
            SELECT COUNT(*) as total 
            FROM events 
            WHERE user_id = ? AND start_date >= ? AND start_date < ?
        '''
        cursor.execute(count_query, (user_id, start_date, end_date))
        total_count = cursor.fetchone()['total']
        
        # Get paginated events
        query = '''
            SELECT e.*,
                   CASE 
                       WHEN e.reminder = 1 AND e.reminder_time <= datetime('now', '+1 hour') 
                       THEN 1 
                       ELSE 0 
                   END as needs_reminder
            FROM events e
            WHERE e.user_id = ? 
            AND e.start_date >= ? 
            AND e.start_date < ?
            ORDER BY e.start_date ASC
            LIMIT ? OFFSET ?
        '''
        
        cursor.execute(query, (user_id, start_date, end_date, page_size, offset))
        events = [dict(event) for event in cursor.fetchall()]
        
        return {
            'events': events,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }

@lru_cache(maxsize=100)
def get_event_categories():
    """Get list of predefined event categories (cached)"""
    return [
        "Family Gathering", "Birthday", "Anniversary", "Doctor's Appointment",
        "School Event", "Sports/Activity", "Holiday", "Travel",
        "Bill Payment", "Shopping", "Other"
    ]

@lru_cache(maxsize=100)
def get_goal_categories():
    """Get list of predefined goal categories (cached)"""
    return [
        "Financial", "Education", "Health", "Family", "Career",
        "Home", "Travel", "Personal Development", "Other"
    ]

@lru_cache(maxsize=100)
def get_goal_status_types():
    """Get list of predefined goal status types (cached)"""
    return [
        "Not Started", "In Progress", "Completed", "On Hold"
    ]

def add_goal(user_id, title, category, description, target_date, target_amount=None):
    """Add a new goal"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO goals 
               (user_id, title, category, description, target_date, target_amount, status, progress)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, title, category, description, target_date, target_amount, "Not Started", 0)
        )
        goal_id = cursor.lastrowid
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()
        return goal_id

def get_goals(user_id, category=None, status=None):
    """Get goals with optional filters (cached)"""
    cache_key = f"goals_{user_id}_{category}_{status}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    with get_db_connection() as conn:
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
        goals = [dict(goal) for goal in cursor.fetchall()]
        _cache.set(cache_key, goals)
        return goals

def update_goal(goal_id, title=None, category=None, description=None, 
                target_date=None, target_amount=None, status=None, progress=None):
    """Update goal details"""
    with get_db_connection() as conn:
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
            # Clear relevant cache entries
            _cache.clear()

def delete_goal(goal_id):
    """Delete a goal"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def add_goal_milestone(goal_id, title, target_date, completed=False):
    """Add a milestone for a goal"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO goal_milestones 
               (goal_id, title, target_date, completed)
               VALUES (?, ?, ?, ?)''',
            (goal_id, title, target_date, completed)
        )
        milestone_id = cursor.lastrowid
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()
        return milestone_id

def get_goal_milestones(goal_id):
    """Get all milestones for a goal (cached)"""
    cache_key = f"goal_milestones_{goal_id}"
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        record_cache_hit()
        return cached_result
    
    record_cache_miss()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM goal_milestones WHERE goal_id = ? ORDER BY target_date ASC', (goal_id,))
        milestones = [dict(milestone) for milestone in cursor.fetchall()]
        _cache.set(cache_key, milestones)
        return milestones

def update_milestone_status(milestone_id, completed):
    """Update milestone completion status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE goal_milestones SET completed = ? WHERE id = ?',
            (completed, milestone_id)
        )
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

def delete_milestone(milestone_id):
    """Delete a milestone"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM goal_milestones WHERE id = ?', (milestone_id,))
        conn.commit()
        # Clear relevant cache entries
        _cache.clear()

# User Settings and Profile operations
def update_user_profile(user_id, email=None, password=None):
    """Update user profile information"""
    with get_db_connection() as conn:
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
            # Clear relevant cache entries
            _cache.clear()

def get_user_data(user_id):
    """Get all user data for export"""
    with get_db_connection() as conn:
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
        
        return user_data

def import_user_data(user_id, data):
    """Import user data from a backup"""
    with get_db_connection() as conn:
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
            # Clear all cache entries
            _cache.clear()
            return True
        except Exception as e:
            conn.rollback()
            return False

def delete_user_data(user_id):
    """Delete all user data"""
    with get_db_connection() as conn:
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
            # Clear all cache entries
            _cache.clear()
            return True
        except Exception as e:
            conn.rollback()
            return False 