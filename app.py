import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

DB_PATH = "attendance.db"

st.set_page_config(page_title="Student Attendance Management", page_icon="📚", layout="wide")

def connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def initialize_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_number TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                course TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
                UNIQUE(student_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
        """)

def query_df(sql, params=()):
    with connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def execute(sql, params=()):
    with connect() as conn:
        conn.execute(sql, params)
        conn.commit()

initialize_db()
st.title("📚 Student Attendance Management System")
st.caption("Manage student records, record daily attendance, and review attendance performance.")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Choose a page", [
        "Dashboard", "Manage Students", "Mark Attendance", "Attendance Reports"
    ])
    st.divider()
    st.caption("Built with Python, Streamlit, SQLite and Pandas.")

students = query_df("SELECT id, roll_number, name, course FROM students ORDER BY roll_number")
attendance = query_df("""
    SELECT a.id, s.roll_number, s.name, s.course, a.attendance_date, a.status
    FROM attendance a JOIN students s ON s.id = a.student_id
    ORDER BY a.attendance_date DESC, s.roll_number
""")

if page == "Dashboard":
    st.subheader("Dashboard")
    total_students = len(students)
    total_records = len(attendance)
    today_str = date.today().isoformat()
    today_records = attendance[attendance["attendance_date"] == today_str] if not attendance.empty else attendance
    present_today = int((today_records["status"] == "Present").sum()) if not today_records.empty else 0
    absent_today = int((today_records["status"] == "Absent").sum()) if not today_records.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total students", total_students)
    c2.metric("Attendance records", total_records)
    c3.metric("Present today", present_today)
    c4.metric("Absent today", absent_today)
    st.info("Get started by adding students, then use Mark Attendance to record a day's attendance.")
    if not students.empty:
        st.markdown("#### Student list")
        st.dataframe(students[["roll_number", "name", "course"]], use_container_width=True, hide_index=True)
    if not today_records.empty:
        st.markdown("#### Today's attendance")
        st.dataframe(today_records[["roll_number", "name", "status"]], use_container_width=True, hide_index=True)

elif page == "Manage Students":
    st.subheader("Manage Students")
    with st.form("add_student_form", clear_on_submit=True):
        st.markdown("#### Add a student")
        roll = st.text_input("Roll number", placeholder="e.g. 24F25A0501").strip()
        name = st.text_input("Student name", placeholder="Full name").strip()
        course = st.text_input("Course / department", placeholder="e.g. B.Tech CSE").strip()
        submitted = st.form_submit_button("Add student", type="primary")
        if submitted:
            if not roll or not name or not course:
                st.error("Please fill in all three fields.")
            else:
                try:
                    execute(
                        "INSERT INTO students (roll_number, name, course, created_at) VALUES (?, ?, ?, ?)",
                        (roll, name, course, date.today().isoformat())
                    )
                    st.success(f"Added {name} successfully.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That roll number already exists. Use a unique roll number.")

    st.markdown("#### Existing students")
    search = st.text_input("Search by roll number, name, or course")
    filtered = students.copy()
    if search and not filtered.empty:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]
    if filtered.empty:
        st.info("No students found. Add a student using the form above.")
    else:
        st.dataframe(filtered[["roll_number", "name", "course"]], use_container_width=True, hide_index=True)
        with st.expander("Delete a student"):
            st.warning("Deleting a student also deletes their attendance records.")
            choices = {
                f'{row.roll_number} — {row.name}': int(row.id)
                for row in filtered.itertuples()
            }
            selected_label = st.selectbox("Choose student", list(choices.keys()))
            if st.button("Delete selected student", type="secondary"):
                student_id = choices[selected_label]
                execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
                execute("DELETE FROM students WHERE id = ?", (student_id,))
                st.success("Student and related attendance records deleted.")
                st.rerun()

elif page == "Mark Attendance":
    st.subheader("Mark Attendance")
    if students.empty:
        st.warning("Add students first in Manage Students.")
    else:
        chosen_date = st.date_input("Attendance date", value=date.today())
        day = chosen_date.isoformat()
        st.caption("Choose a status for each student. Saving again for the same date updates the existing record.")
        existing = query_df("SELECT student_id, status FROM attendance WHERE attendance_date = ?", (day,))
        existing_status = dict(zip(existing["student_id"], existing["status"])) if not existing.empty else {}
        with st.form("attendance_form"):
            selections = {}
            for row in students.itertuples():
                default = existing_status.get(int(row.id), "Present")
                selections[int(row.id)] = st.selectbox(
                    f"{row.roll_number} — {row.name}",
                    ["Present", "Absent"],
                    index=0 if default == "Present" else 1,
                    key=f"status_{row.id}_{day}"
                )
            saved = st.form_submit_button("Save attendance", type="primary")
            if saved:
                with connect() as conn:
                    for student_id, status in selections.items():
                        conn.execute("""
                            INSERT INTO attendance (student_id, attendance_date, status)
                            VALUES (?, ?, ?)
                            ON CONFLICT(student_id, attendance_date)
                            DO UPDATE SET status = excluded.status
                        """, (student_id, day, status))
                    conn.commit()
                st.success(f"Attendance saved for {day}.")
                st.rerun()

elif page == "Attendance Reports":
    st.subheader("Attendance Reports")
    if students.empty:
        st.info("Add students and record attendance to generate reports.")
    elif attendance.empty:
        st.info("No attendance records yet. Use Mark Attendance to add records.")
    else:
        report = query_df("""
            SELECT s.roll_number, s.name, s.course,
                   COUNT(a.id) AS classes_recorded,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS classes_present,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS classes_absent
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.id
            GROUP BY s.id, s.roll_number, s.name, s.course
            ORDER BY s.roll_number
        """)
        report["attendance_percentage"] = report.apply(
            lambda r: round((r["classes_present"] / r["classes_recorded"]) * 100, 2)
            if r["classes_recorded"] else 0.0,
            axis=1
        )
        report["below_75_percent"] = report["attendance_percentage"] < 75
        col1, col2 = st.columns(2)
        col1.metric("Students below 75%", int(report["below_75_percent"].sum()))
        col2.metric("Average attendance", f'{report["attendance_percentage"].mean():.1f}%')
        st.dataframe(report, use_container_width=True, hide_index=True)
        low = report[report["below_75_percent"]]
        if not low.empty:
            st.warning("Students with attendance below 75% are listed below.")
            st.dataframe(low[["roll_number", "name", "attendance_percentage"]], use_container_width=True, hide_index=True)
        csv = report.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download attendance report (CSV)",
            data=csv,
            file_name="attendance_report.csv",
            mime="text/csv"
        )
        st.markdown("#### Detailed attendance records")
        start_date = st.date_input("Filter from date", value=date.today().replace(day=1), key="start_date")
        end_date = st.date_input("Filter to date", value=date.today(), key="end_date")
        if start_date > end_date:
            st.error("The start date must be on or before the end date.")
        else:
            details = attendance[
                (attendance["attendance_date"] >= start_date.isoformat()) &
                (attendance["attendance_date"] <= end_date.isoformat())
            ]
            st.dataframe(details, use_container_width=True, hide_index=True)
            st.download_button(
                "Download detailed records (CSV)",
                data=details.to_csv(index=False).encode("utf-8"),
                file_name="detailed_attendance.csv",
                mime="text/csv"
            )
