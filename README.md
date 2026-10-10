# Student Attendance Management System

A beginner-friendly attendance tracking web app built with Python, Streamlit, SQLite, and Pandas.

## Features

- Add and search students
- Store student information in SQLite
- Mark Present/Absent attendance by date
- Update attendance records for a selected date
- View attendance percentages and flag students below 75%
- Export summary and detailed attendance records as CSV files
- Dashboard with student and daily attendance counts

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

5. Open the local URL shown in the terminal.

## Data and privacy

The app creates `attendance.db` automatically in the working directory. Use fictional sample student information when demonstrating the project. Do not publish real student personal information or attendance records.

## Technologies

- Python
- Streamlit
- SQLite
- Pandas
