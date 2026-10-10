
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="Student Attendance System",
    page_icon="🎓",
    layout="wide"
)

conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    roll_no TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    year TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no TEXT NOT NULL,
    attendance_date TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE(roll_no, attendance_date)
)
""")
conn.commit()

st.title("🎓 Student Attendance Management System")
st.write("Manage student details and daily attendance easily.")

menu = st.sidebar.selectbox(
    "Choose an option",
    [
        "Dashboard",
        "Add Student",
        "View Students",
        "Mark Attendance",
        "Attendance Records",
        "Attendance Report"
    ]
)

if menu == "Dashboard":
    total_students = cursor.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    today = str(date.today())
    present = cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Present'",
        (today,)
    ).fetchone()[0]

    absent = cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Absent'",
        (today,)
    ).fetchone()[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Students", total_students)
    c2.metric("Present Today", present)
    c3.metric("Absent Today", absent)

    st.subheader("Welcome!")
    st.write("Use the sidebar to manage students and attendance.")

elif menu == "Add Student":
    st.subheader("Add New Student")

    with st.form("student_form"):
        roll_no = st.text_input("Roll Number")
        name = st.text_input("Student Name")
        department = st.selectbox(
            "Department",
            ["CSE", "ECE", "EEE", "Civil", "Mechanical", "Other"]
        )
        year = st.selectbox(
            "Year",
            ["1st Year", "2nd Year", "3rd Year", "4th Year"]
        )

        submitted = st.form_submit_button("Add Student")

        if submitted:
            if roll_no.strip() and name.strip():
                try:
                    cursor.execute(
                        "INSERT INTO students VALUES (?, ?, ?, ?)",
                        (roll_no.strip(), name.strip(), department, year)
                    )
                    conn.commit()
                    st.success("Student added successfully!")
                except sqlite3.IntegrityError:
                    st.error("This roll number already exists.")
            else:
                st.warning("Please enter the roll number and student name.")

elif menu == "View Students":
    st.subheader("Registered Students")

    df = pd.read_sql_query(
        "SELECT roll_no AS 'Roll Number', name AS 'Name', department AS 'Department', year AS 'Year' FROM students",
        conn
    )

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download Student List CSV",
            df.to_csv(index=False).encode("utf-8"),
            "students.csv",
            "text/csv"
        )
    else:
        st.info("No students added yet.")

elif menu == "Mark Attendance":
    st.subheader("Mark Daily Attendance")
    selected_date = st.date_input("Attendance Date", date.today())
    students = cursor.execute(
        "SELECT roll_no, name FROM students ORDER BY roll_no"
    ).fetchall()

    if students:
        with st.form("attendance_form"):
            attendance_data = []

            for roll_no, name in students:
                status = st.radio(
                    f"{name} ({roll_no})",
                    ["Present", "Absent"],
                    horizontal=True,
                    key=f"{roll_no}_{selected_date}"
                )
                attendance_data.append((roll_no, str(selected_date), status))

            save = st.form_submit_button("Save Attendance")

            if save:
                cursor.executemany("""
                    INSERT INTO attendance (roll_no, attendance_date, status)
                    VALUES (?, ?, ?)
                    ON CONFLICT(roll_no, attendance_date)
                    DO UPDATE SET status=excluded.status
                """, attendance_data)

                conn.commit()
                st.success("Attendance saved successfully!")
    else:
        st.info("Please add students before marking attendance.")

elif menu == "Attendance Records":
    st.subheader("Attendance History")

    df = pd.read_sql_query("""
        SELECT s.roll_no AS 'Roll Number',
               s.name AS 'Student Name',
               a.attendance_date AS 'Date',
               a.status AS 'Status'
        FROM attendance a
        JOIN students s ON s.roll_no = a.roll_no
        ORDER BY a.attendance_date DESC, s.roll_no
    """, conn)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download Attendance CSV",
            df.to_csv(index=False).encode("utf-8"),
            "attendance_records.csv",
            "text/csv"
        )
    else:
        st.info("No attendance records available.")

elif menu == "Attendance Report":
    st.subheader("Student Attendance Percentage")

    df = pd.read_sql_query("""
        SELECT s.roll_no AS 'Roll Number',
               s.name AS 'Student Name',
               COUNT(a.id) AS 'Classes Recorded',
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS 'Present',
               SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS 'Absent'
        FROM students s
        LEFT JOIN attendance a ON s.roll_no = a.roll_no
        GROUP BY s.roll_no, s.name
        ORDER BY s.roll_no
    """, conn)

    if not df.empty:
        df["Attendance Percentage"] = (
            df["Present"] / df["Classes Recorded"].replace(0, float("nan")) * 100
        ).round(2).fillna(0)

        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download Attendance Report",
            df.to_csv(index=False).encode("utf-8"),
            "attendance_report.csv",
            "text/csv"
        )
    else:
        st.info("No students available for the report.")

conn.close()
