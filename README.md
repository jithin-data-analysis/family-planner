# Family Planner Application

A Streamlit-based family planning and management application.

## Deployment Instructions for Python Anywhere

1. Sign up for a Python Anywhere account at https://www.pythonanywhere.com/

2. Create a new Web App:
   - Go to the Web tab
   - Click "Add a new web app"
   - Choose "Flask" as the framework
   - Select Python 3.9 as the Python version

3. Set up the virtual environment:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.9 family-planner
   pip install -r requirements.txt
   ```

4. Configure the Web App:
   - Set the working directory to your project directory
   - Set the WSGI configuration file to point to `wsgi.py`
   - Set the virtual environment path to your created virtual environment
   - Add the following environment variables:
     - DATABASE_URL
     - SECRET_KEY
     - DEBUG=false

5. Upload your code:
   - Use the Files tab to upload your project files
   - Or use Git to clone your repository

6. Configure the database:
   - Go to the Databases tab
   - Create a new MySQL database
   - Note down the database credentials
   - Update the DATABASE_URL environment variable

7. Start the Web App:
   - Go to the Web tab
   - Click the "Reload" button

## Local Development

To run the application locally:

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

## Features

- Family member management
- Task and event tracking
- Budget management
- Family calendar
- Document storage
- Family chat
- Family goals tracking

## Features

1. **User Authentication**
   - Secure login and registration
   - Password hashing with bcrypt
   - Email-based account management

2. **Financial Dashboard**
   - Track income and expenses
   - Categorize transactions
   - Visual spending analysis
   - Real-time balance tracking

3. **Budget Planning**
   - Set monthly budgets by category
   - Track spending against budgets
   - Visual progress indicators
   - Budget vs. actual analysis

4. **Shopping Lists**
   - Create multiple shopping lists
   - Add/remove items
   - Track quantities
   - Mark items as completed
   - Share lists with family members

5. **Family Profiles**
   - Manage family member information
   - Track relationships and birthdays
   - Family composition analysis
   - Age distribution visualization

6. **Calendar & Events**
   - Multiple calendar views (Month, Week, Upcoming)
   - Event management with reminders
   - Recurring events support
   - Event categorization

7. **Goals Tracking**
   - Set personal and family goals
   - Track progress with milestones
   - Financial and non-financial goals
   - Visual progress tracking
   - Goal categorization

8. **Data Management**
   - Export data to JSON
   - Import data from backups
   - Data deletion capabilities
   - Profile settings management

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/family-planner.git
   cd family-planner
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```bash
   python src/init_db.py
   ```

5. Run the application:
   ```bash
   streamlit run src/app.py
   ```

## Dependencies

- Python 3.8+
- Streamlit
- SQLite3
- Plotly
- bcrypt
- pandas

## Project Structure

```
family-planner/
├── src/
│   ├── app.py           # Main application file
│   ├── db_utils.py      # Database utilities
│   ├── models.py        # Database models
│   └── init_db.py       # Database initialization
├── data/
│   └── family_planner.db # SQLite database
├── requirements.txt      # Project dependencies
├── README.md            # Project documentation
└── .gitignore           # Git ignore file
```

## Database Schema

### Users Table
- id (PRIMARY KEY)
- username (UNIQUE)
- password_hash
- email (UNIQUE)
- created_at

### Family Members Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- name
- relationship
- birth_date

### Transactions Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- amount
- category
- description
- date
- transaction_type

### Budgets Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- category
- amount
- month
- year

### Shopping Lists Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- name
- created_at

### Shopping List Items Table
- id (PRIMARY KEY)
- list_id (FOREIGN KEY)
- item_name
- quantity
- completed

### Events Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- title
- description
- start_date
- end_date
- reminder
- reminder_time

### Goals Table
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- title
- category
- description
- target_date
- target_amount
- status
- progress

### Goal Milestones Table
- id (PRIMARY KEY)
- goal_id (FOREIGN KEY)
- title
- target_date
- completed
- created_at

## Deployment

1. **Local Deployment**
   - Follow the installation instructions above
   - Access the application at http://localhost:8501

2. **Cloud Deployment (Streamlit Cloud)**
   - Fork this repository to your GitHub account
   - Sign up for [Streamlit Cloud](https://streamlit.io/cloud)
   - Connect your GitHub repository
   - Deploy with one click

3. **Custom Server Deployment**
   - Install required dependencies
   - Set up a reverse proxy (nginx recommended)
   - Configure SSL certificates
   - Use process manager (PM2 or supervisord)

## Security Considerations

1. **Data Protection**
   - All passwords are hashed using bcrypt
   - Database is protected with proper permissions
   - Input validation and sanitization
   - CSRF protection

2. **Backup and Recovery**
   - Regular database backups recommended
   - Export functionality for user data
   - Data import validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 