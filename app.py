from flask import Flask, render_template, request, redirect, url_for, session, flash, g, make_response
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime, timedelta
import json
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'a_very_secret_key_for_production'
DATABASE = 'database.db'

# --- Database Connection ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to view that page.", "error")
            return redirect(url_for('auth'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to view that page.", "error")
            return redirect(url_for('auth'))
        if session.get('user_role') != 'admin':
            flash("You don't have permission to access this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def faculty_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to view that page.", "error")
            return redirect(url_for('auth'))
        if session.get('user_role') != 'faculty':
            flash("Access denied. Faculty only.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Main & Auth Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('user_role') == 'faculty':
            return redirect(url_for('faculty_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('landing.html')

@app.route('/auth')
def auth():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('user_role') == 'faculty':
            return redirect(url_for('faculty_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('auth.html')

@app.route('/signup', methods=['POST'])
def signup():
    full_name = request.form['full_name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    db = get_db()
    try:
        db.execute("INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?)",
                   (full_name, email, hashed_password, role))
        db.commit()
        flash("Account created successfully! Please log in.", "success")
    except sqlite3.IntegrityError:
        flash("That email address is already registered. Please login instead.", "error")
    return redirect(url_for('auth'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
   
    if user and check_password_hash(user['password'], password):
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_role'] = user['role']
       
        if user['role'] == 'admin':
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for('admin_dashboard'))
        elif user['role'] == 'faculty':
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for('faculty_dashboard'))
        elif user['role'] == 'student':
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid user role.", "error")
            return redirect(url_for('auth'))
    else:
        flash("Invalid email or password. Please try again.", "error")
        return redirect(url_for('auth'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('index'))

# ============= STUDENT MODULE ROUTES =============

from datetime import date

@app.route('/dashboard')
@login_required
def student_dashboard():
    db = get_db()
    # Notices
    notices = db.execute("SELECT * FROM notices ORDER BY created_at DESC").fetchall()
    # Attendance records
    records = db.execute("SELECT status, subject FROM attendance WHERE student_id = ?", (session['user_id'],)).fetchall()
    total_days = len(records)
    present_days = sum(1 for r in records if r['status'] == 'Present')
    absent_days = sum(1 for r in records if r['status'] == 'Absent')
    leave_days = sum(1 for r in records if r['status'] == 'Leave')
    attendance_percentage = int(present_days / total_days * 100) if total_days > 0 else 0

    subjects = {}
    for r in records:
        subj = r['subject']
        subjects.setdefault(subj, {'present': 0, 'total': 0})
        subjects[subj]['total'] += 1
        if r['status'] == 'Present':
            subjects[subj]['present'] += 1
    subject_performance = [
        {"name": name, "percentage": int(data['present'] / data['total'] * 100) if data['total'] > 0 else 0}
        for name, data in subjects.items()
    ]

    current_date = date.today().strftime("%B %d, %Y")
    return render_template('dashboard.html',
        notices=notices,
        total_days=total_days,
        present_days=present_days,
        absent_days=absent_days,
        leave_days=leave_days,
        attendance_percentage=attendance_percentage,
        subject_performance=subject_performance,
        current_date=current_date
    )


@app.route('/profile')
@login_required
def student_profile():
    db = get_db()
    user_info = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('profile.html', user=user_info)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    new_full_name = request.form['full_name']
    new_email = request.form['email']
    db = get_db()
    db.execute('UPDATE users SET full_name = ?, email = ? WHERE id = ?',
              (new_full_name, new_email, session['user_id']))
    db.commit()
    session['user_name'] = new_full_name
    flash('Profile details updated successfully!', 'success')
    return redirect(url_for('student_profile'))

@app.route('/password/update', methods=['POST'])
@login_required
def update_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_new_password']
   
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('student_profile'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not check_password_hash(user['password'], current_password):
        flash('Incorrect current password.', 'error')
        return redirect(url_for('student_profile'))

    new_hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.execute('UPDATE users SET password = ? WHERE id = ?',
              (new_hashed_password, session['user_id']))
    db.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('student_profile'))

@app.route('/attendance_history')
@login_required
def attendance_history():
    db = get_db()
    query = """
        SELECT a.*, 
            (SELECT full_name FROM users WHERE role = 'faculty' AND subject = a.subject LIMIT 1) AS faculty
        FROM attendance a
        WHERE a.student_id = ?
    """
    params = [session['user_id']]
    # Get filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    subject = request.args.get('subject')

    if start_date:
        query += " AND a.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND a.date <= ?"
        params.append(end_date)
    if status:
        query += " AND a.status = ?"
        params.append(status)
    if subject:
        query += " AND a.subject = ?"
        params.append(subject)

    query += " ORDER BY a.date DESC"
    records = db.execute(query, tuple(params)).fetchall()

    all_records = db.execute("SELECT DISTINCT subject FROM attendance WHERE student_id = ?", (session['user_id'],)).fetchall()
    subjects = [row['subject'] for row in all_records]
    return render_template('attendance_history.html', records=records, subjects=subjects)



# ============= ADMIN MODULE ROUTES =============

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
   
    total_students = db.execute(
        "SELECT COUNT(*) as count FROM users WHERE role='student'"
    ).fetchone()['count']
   
    total_faculty = db.execute(
        "SELECT COUNT(*) as count FROM users WHERE role='faculty'"
    ).fetchone()['count']
   
    total_classes = db.execute(
        "SELECT COUNT(DISTINCT class_name) as count FROM users WHERE role='student' AND class_name IS NOT NULL"
    ).fetchone()['count']
   
    total_records = db.execute("SELECT COUNT(*) as count FROM attendance").fetchone()['count']
    present_records = db.execute(
        "SELECT COUNT(*) as count FROM attendance WHERE status='Present'"
    ).fetchone()['count']
    overall_attendance = round((present_records / total_records * 100) if total_records > 0 else 0, 1)
   
    recent_students = db.execute("""
        SELECT u.id, u.full_name, u.class_name, u.roll_number,
               COUNT(a.id) as total_classes,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY u.id DESC
        LIMIT 5
    """).fetchall()
   
    students_with_attendance = []
    for student in recent_students:
        attendance_pct = round(
            (student['present_count'] / student['total_classes'] * 100)
            if student['total_classes'] > 0 else 0
        )
        students_with_attendance.append({
            'name': student['full_name'],
            'class': student['class_name'] or 'N/A',
            'attendance': attendance_pct
        })
   
    classes_overview = db.execute("""
        SELECT class_name, COUNT(*) as student_count
        FROM users
        WHERE role='student' AND class_name IS NOT NULL
        GROUP BY class_name
    """).fetchall()
   
    monthly_trend = []
    for i in range(9, -1, -1):
        month_date = datetime.now() - timedelta(days=30*i)
        month_name = month_date.strftime('%b')
        month_str = month_date.strftime('%Y-%m')
        month_total = db.execute(
            "SELECT COUNT(*) as count FROM attendance WHERE date LIKE ?",
            (f"{month_str}%",)
        ).fetchone()['count']
        month_present = db.execute(
            "SELECT COUNT(*) as count FROM attendance WHERE date LIKE ? AND status='Present'",
            (f"{month_str}%",)
        ).fetchone()['count']
        month_pct = round((month_present / month_total * 100) if month_total > 0 else 0)
        monthly_trend.append({'month': month_name, 'percentage': month_pct})
   
    return render_template('admin_dashboard.html',
                         total_students=total_students,
                         total_faculty=total_faculty,
                         total_classes=total_classes,
                         overall_attendance=overall_attendance,
                         recent_students=students_with_attendance,
                         classes_overview=classes_overview,
                         monthly_trend=json.dumps(monthly_trend))

@app.route('/admin/users')
@admin_required
def admin_users():
    db = get_db()
    # All students with their attendance summary
    students = db.execute("""
        SELECT u.id, u.full_name, u.email, u.class_name, u.roll_number,
               COUNT(a.id) as total_classes,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY u.roll_number
    """).fetchall()
    students_data = []
    for s in students:
        attendance_pct = round(
            (s['present_count'] / s['total_classes'] * 100)
            if s['total_classes'] > 0 else 0
        )
        students_data.append({
            'id': s['id'],
            'roll_no': s['roll_number'] or 'N/A',
            'name': s['full_name'],
            'email': s['email'],
            'class': s['class_name'] or 'N/A',
            'attendance': attendance_pct
        })
    # Display all faculty
    faculty = db.execute(
        "SELECT id, full_name, email, subject, class_name FROM users WHERE role='faculty'"
    ).fetchall()
    # Display all users (for "All Users" tab)
    users = db.execute("SELECT * FROM users").fetchall()
    return render_template('admin_users.html',
                           students=students_data,
                           faculty=faculty,
                           users=users)

@app.route('/admin/classes')
@admin_required
def admin_classes():
    db = get_db()
    classes = db.execute("""
        SELECT DISTINCT u.class_name, a.subject,
            (SELECT full_name FROM users WHERE role='faculty' AND subject = a.subject LIMIT 1) as faculty,
            COUNT(DISTINCT u.id) as total_students
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id AND a.subject IS NOT NULL
        WHERE u.role='student' AND u.class_name IS NOT NULL
        GROUP BY u.class_name, a.subject
        ORDER BY u.class_name
    """).fetchall()

    attendance_records = db.execute("""
        SELECT u.full_name as student_name, u.class_name, u.roll_number as roll_no,
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as presents,
            SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) as absents,
            COUNT(a.id) as total,
            ROUND(SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)*100.0/COUNT(a.id),1) as percentage
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id
        WHERE u.role='student'
        GROUP BY u.id
        ORDER BY u.class_name, u.roll_number
    """).fetchall()
    
    class_list = sorted(set([c['class_name'] for c in classes if c['class_name']]))
    return render_template('admin_classes.html',
        classes=classes,
        attendance_records=attendance_records,
        class_list=class_list)

@app.route('/admin/class/<class_name>/<subject>')
@admin_required
def view_class(class_name, subject):
    db = get_db()
    # Query details for students in this class for the given subject
    class_students = db.execute("""
        SELECT u.full_name, u.roll_number, a.status, a.date
        FROM users u
        LEFT JOIN attendance a
            ON u.id = a.student_id AND a.subject = ?
        WHERE u.class_name = ?
        ORDER BY u.roll_number, a.date
    """, (subject, class_name)).fetchall()
    return render_template('class_details.html', students=class_students, class_name=class_name, subject=subject)

@app.route('/admin/class/add', methods=['GET', 'POST'])
@admin_required
def add_class():
    db = get_db()
    if request.method == 'POST':
        class_name = request.form['class_name']
        subject = request.form['subject']
        faculty = request.form['faculty']
        db.execute(
            "INSERT INTO classes (class_name, subject, faculty) VALUES (?, ?, ?)",
            (class_name, subject, faculty)
        )
        db.commit()
        flash('Class added successfully!', 'success')
        return redirect(url_for('admin_classes'))
    return render_template('admin_add_class.html')

# For any page that has filter forms:
@app.route('/admin/users/filter')
@admin_required
def admin_users_filter():
    db = get_db()
    role_filter = request.args.get('role', '')
    class_filter = request.args.get('class', '')
    query = "SELECT * FROM users WHERE 1=1"
    params = []
    if role_filter:
        query += " AND role=?"
        params.append(role_filter)
    if class_filter:
        query += " AND class_name=?"
        params.append(class_filter)
    users = db.execute(query, tuple(params)).fetchall()
    return render_template('admin_users.html', users=users)

# If you want subject filtering in the classes page:
@app.route('/admin/classes/filter')
@admin_required
def admin_classes_filter():
    db = get_db()
    class_filter = request.args.get('class', '')
    subject_filter = request.args.get('subject', '')
    base_query = """
        SELECT DISTINCT u.class_name, a.subject,
            (SELECT full_name FROM users WHERE role='faculty' AND subject = a.subject LIMIT 1) as faculty,
            COUNT(DISTINCT u.id) as total_students
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id AND a.subject IS NOT NULL
        WHERE u.role='student' AND u.class_name IS NOT NULL
    """
    filters = []
    params = []
    if class_filter:
        filters.append("u.class_name = ?")
        params.append(class_filter)
    if subject_filter:
        filters.append("a.subject = ?")
        params.append(subject_filter)
    if filters:
        base_query += " AND " + " AND ".join(filters)
    base_query += " GROUP BY u.class_name, a.subject ORDER BY u.class_name"
    classes = db.execute(base_query, tuple(params)).fetchall()
    return render_template('admin_classes.html', classes=classes)

@app.route('/admin/reports')
@admin_required
def admin_reports():
    db = get_db()
   
    notices = db.execute('SELECT * FROM notices ORDER BY created_at DESC').fetchall()
    total_classes = db.execute(
        "SELECT COUNT(DISTINCT class_name) as count FROM users WHERE class_name IS NOT NULL"
    ).fetchone()['count']
   
    total_records = db.execute("SELECT COUNT(*) as count FROM attendance").fetchone()['count']
    present_records = db.execute(
        "SELECT COUNT(*) as count FROM attendance WHERE status='Present'"
    ).fetchone()['count']
    avg_attendance = round((present_records / total_records * 100) if total_records > 0 else 0)
   
    students_below_75 = db.execute("""
        SELECT COUNT(DISTINCT student_id) as count
        FROM (
            SELECT student_id,
                   SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as attendance_pct
            FROM attendance
            GROUP BY student_id
            HAVING attendance_pct < 75
        )
    """).fetchone()['count']
   
    perfect_attendance = db.execute("""
        SELECT COUNT(DISTINCT student_id) as count
        FROM (
            SELECT student_id,
                   SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as attendance_pct
            FROM attendance
            GROUP BY student_id
            HAVING attendance_pct = 100
        )
    """).fetchone()['count']
   
    return render_template('admin_reports.html',
                         notices=notices,
                         total_classes=total_classes,
                         avg_attendance=avg_attendance,
                         below_75=students_below_75,
                         perfect_attendance=perfect_attendance)

@app.route('/admin/notice/create', methods=['POST'])
@admin_required
def create_notice():
    title = request.form['title']
    content = request.form['content']
    audience = request.form.get('audience', 'All')
   
    db = get_db()
    db.execute('INSERT INTO notices (title, content, author, created_at) VALUES (?, ?, ?, ?)',
               (title, content, audience, datetime.now().strftime('%Y-%m-%d')))
    db.commit()
   
    flash('Notice created successfully!', 'success')
    return redirect(url_for('admin_reports'))

@app.route('/admin/notice/delete/<int:notice_id>', methods=['POST'])
@admin_required
def delete_notice(notice_id):
    db = get_db()
    db.execute('DELETE FROM notices WHERE id = ?', (notice_id,))
    db.commit()
   
    flash('Notice deleted successfully!', 'success')
    return redirect(url_for('admin_reports'))

@app.route('/admin/user/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        class_name = request.form.get('class_name', '')
        roll_number = request.form.get('roll_number', '')
       
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
       
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (full_name, email, password, role, class_name, roll_number) VALUES (?, ?, ?, ?, ?, ?)",
                (full_name, email, hashed_password, role, class_name, roll_number)
            )
            db.commit()
            flash(f'{role.capitalize()} "{full_name}" added successfully!', 'success')
            return redirect(url_for('admin_users'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'error')
   
    return render_template('admin_add_user.html')

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.execute('DELETE FROM attendance WHERE student_id = ?', (user_id,))
    db.commit()
   
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/download/pdf')
@admin_required
def download_pdf():
    db = get_db()
    class_filter = request.args.get('class', '').strip()

    base_query = """
        SELECT u.full_name, u.class_name, u.roll_number,
               COUNT(a.id) as total,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as presents,
               SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absents
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id
        WHERE u.role = 'student'
    """
    params = []
    if class_filter:
        base_query += " AND u.class_name = ?"
        params.append(class_filter)
    base_query += " GROUP BY u.id ORDER BY u.class_name, u.roll_number"
    attendance_data = db.execute(base_query, params).fetchall()

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            h1 {{ color: #1e293b; text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #3b82f6; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #e5e7eb; }}
            tr:hover {{ background: #f9fafb; }}
        </style>
    </head>
    <body>
        <h1>AttendEase - Attendance Report</h1>
        <p>Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <table>
            <thead>
                <tr>
                    <th>Roll No</th>
                    <th>Name</th>
                    <th>Class</th>
                    <th>Present</th>
                    <th>Absent</th>
                    <th>Total</th>
                    <th>Attendance %</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for record in attendance_data:
        percentage = round((record['presents'] / record['total'] * 100) if record['total'] > 0 else 0)
        html_content += f"""
                <tr>
                    <td>{record['roll_number'] or 'N/A'}</td>
                    <td>{record['full_name']}</td>
                    <td>{record['class_name'] or 'N/A'}</td>
                    <td>{record['presents']}</td>
                    <td>{record['absents']}</td>
                    <td>{record['total']}</td>
                    <td>{percentage}%</td>
                </tr>
        """
    
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{datetime.now().strftime("%Y%m%d")}.html'
    
    return response


@app.route('/admin/download/csv')
@admin_required
def download_csv():
    db = get_db()
    class_filter = request.args.get('class', '').strip()

    base_query = """
        SELECT u.roll_number, u.full_name, u.class_name,
               COUNT(a.id) as total,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as presents,
               SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absents
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id
        WHERE u.role = 'student'
    """
    params = []
    if class_filter:
        base_query += " AND u.class_name = ?"
        params.append(class_filter)
    base_query += " GROUP BY u.id ORDER BY u.class_name, u.roll_number"
    attendance_data = db.execute(base_query, params).fetchall()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Roll Number', 'Full Name', 'Class', 'Present', 'Absent', 'Total', 'Attendance %'])

    for record in attendance_data:
        percentage = round((record['presents'] / record['total'] * 100) if record['total'] > 0 else 0)
        writer.writerow([
            record['roll_number'] or 'N/A',
            record['full_name'],
            record['class_name'] or 'N/A',
            record['presents'],
            record['absents'],
            record['total'],
            f"{percentage}%"
        ])

    output = si.getvalue()
    si.close()
    response = make_response(output)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{datetime.now().strftime("%Y%m%d")}.csv'
    return response


# ============= FACULTY MODULE ROUTES =============

@app.route('/faculty/dashboard')
@faculty_required
def faculty_dashboard():
    from datetime import datetime, date
    db = get_db()

    # Fetch faculty's assigned subject from users table
    faculty = db.execute('SELECT subject, full_name FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    faculty_subject = faculty['subject'] if faculty and faculty['subject'] else 'General'
    faculty_name = faculty['full_name'] if faculty else "Faculty"

    notices = db.execute('SELECT * FROM notices ORDER BY created_at DESC LIMIT 3').fetchall()

    today_obj = date.today()
    today = today_obj.strftime('%Y-%m-%d')
    today_day_name = today_obj.strftime('%A')
    current_time = datetime.now().time()

    # For dashboard cards
    total_students = db.execute("SELECT COUNT(*) as count FROM users WHERE role='student'").fetchone()['count']

    # All valid classes for this subject
    classes_with_subject = db.execute("""
        SELECT DISTINCT u.class_name
        FROM users u
        JOIN attendance a ON u.id = a.student_id
        WHERE u.role='student' AND a.subject=?
    """, (faculty_subject,)).fetchall()
    valid_classes = [r['class_name'] for r in classes_with_subject]

    # Weekly schedule (use whichever format and classes you wish below)
    all_schedules = [
        {'day': 'Monday', 'time': '9:00 - 10:30', 'class': 'SE COMP-A'},
        {'day': 'Monday', 'time': '11:00 - 12:30', 'class': 'SE COMP-B'},
        {'day': 'Tuesday', 'time': '8:00 - 10:30', 'class': 'SE COMP-A'},
        {'day': 'Wednesday', 'time': '2:00 - 3:30', 'class': 'SE COMP-B'},
        {'day': 'Thursday', 'time': '10:00 - 11:30', 'class': 'SE COMP-A'},
        {'day': 'Friday', 'time': '1:00 - 2:30', 'class': 'SE COMP-B'},
    ]

    # Only show schedule with classes which actually have this subject
    weekly_schedule = [
        {
            'day_short': s['day'][:3],
            'time': s['time'],
            'class_name': s['class'],
            'subject': faculty_subject,
            'full_day': s['day']
        }
        for s in all_schedules if s['class'] in valid_classes
    ]

    # Today's schedule: Only those that match today's day
    todays_schedule = []
    for schedule in weekly_schedule:
        if schedule['full_day'] == today_day_name:
            time_parts = schedule['time'].split(' - ')
            start_time = datetime.strptime(time_parts[0].strip(), '%H:%M').time()
            end_time = datetime.strptime(time_parts[1].strip(), '%H:%M').time()
            attendance_marked = db.execute("""
                SELECT COUNT(*) as count
                FROM attendance a
                JOIN users u ON a.student_id = u.id
                WHERE u.class_name = ? AND a.date = ? AND a.subject = ?
            """, (schedule['class_name'], today, faculty_subject)).fetchone()['count'] or 0

            if attendance_marked > 0:
                status = 'Completed'
            elif current_time < start_time:
                status = 'Upcoming'
            elif current_time > end_time:
                status = 'Pending'
            else:
                status = 'In Progress'

            todays_schedule.append({
                'time': schedule['time'],
                'class_name': schedule['class_name'],
                'subject': faculty_subject,
                'status': status
            })

    todays_classes = len(todays_schedule)
    attendance_pending = sum(1 for x in todays_schedule if x['status'] != 'Completed')
    completed_today = sum(1 for x in todays_schedule if x['status'] == 'Completed')

    return render_template('faculty_dashboard.html',
        faculty_name=faculty_name,
        faculty_subject=faculty_subject,
        total_students=total_students,
        todays_classes=todays_classes,
        attendance_pending=attendance_pending,
        completed_today=completed_today,
        notices=notices,
        weekly_schedule=weekly_schedule,
        todays_schedule=todays_schedule,
        current_date=today_obj.strftime("%B %d, %Y"))


@app.route('/faculty/mark-attendance', methods=['GET', 'POST'])
@faculty_required
def faculty_mark_attendance():
    db = get_db()
    
    # Get faculty's assigned subject
    faculty = db.execute('SELECT subject FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    faculty_subject = faculty['subject'] if faculty and faculty['subject'] else 'General'
    
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        attendance_date = request.form.get('date')
        # SECURITY: Force subject to be faculty's assigned subject
        subject = faculty_subject
        
        # Get all students for the class
        students = db.execute(
            "SELECT id FROM users WHERE role='student' AND class_name=?",
            (class_name,)
        ).fetchall()
        
        # Mark attendance
        for student in students:
            student_id = student['id']
            status = request.form.get(f'status_{student_id}', 'Absent')
            
            # Check if attendance already exists
            existing = db.execute(
                "SELECT id FROM attendance WHERE student_id=? AND date=? AND subject=?",
                (student_id, attendance_date, subject)
            ).fetchone()
            
            if not existing:
                # Insert new attendance record
                db.execute(
                    "INSERT INTO attendance (student_id, date, subject, status) VALUES (?, ?, ?, ?)",
                    (student_id, attendance_date, subject, status)
                )
            else:
                # Update existing record
                db.execute(
                    "UPDATE attendance SET status = ? WHERE id = ?",
                    (status, existing['id'])
                )
        
        db.commit()
        flash(f'Attendance marked successfully for {class_name} - {subject}!', 'success')
        return redirect(url_for('faculty_mark_attendance'))
    
    # GET request - show form
    selected_class = request.args.get('class', None)
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    # This ensures faculty can only mark classes where their subject is taught
    classes = db.execute("""
        SELECT DISTINCT u.class_name
        FROM users u
        JOIN attendance a ON u.id = a.student_id
        WHERE u.role='student' 
          AND u.class_name IS NOT NULL
          AND a.subject = ?
        ORDER BY u.class_name
    """, (faculty_subject,)).fetchall()
    
    # If no classes found with attendance, show all classes but they won't have students
    if not classes:
        classes = db.execute("""
            SELECT DISTINCT class_name
            FROM users
            WHERE role='student' AND class_name IS NOT NULL
            ORDER BY class_name
        """).fetchall()
    
    # Set default class if none selected
    if not selected_class and classes:
        selected_class = classes[0]['class_name']
    
    # Get students for selected class
    students = []
    if selected_class:
        students = db.execute("""
            SELECT id, roll_number, full_name, class_name
            FROM users
            WHERE role='student' AND class_name=?
            ORDER BY roll_number
        """, (selected_class,)).fetchall()
    
    return render_template('faculty_mark_attendance.html',
                         students=students,
                         classes=classes,
                         selected_class=selected_class,
                         selected_date=selected_date,
                         faculty_subject=faculty_subject)


@app.route('/faculty/view-attendance')
@faculty_required
def faculty_view_attendance():
    db = get_db()
    
    faculty = db.execute('SELECT subject FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    faculty_subject = faculty['subject'] if faculty and faculty['subject'] else 'General'
    
    selected_class = request.args.get('class', None)
    
    # Get all classes
    classes = db.execute("""
        SELECT DISTINCT class_name
        FROM users
        WHERE role='student' AND class_name IS NOT NULL
        ORDER BY class_name
    """).fetchall()
    
    if not selected_class and classes:
        selected_class = classes[0]['class_name']
    
    # FIXED: Count number of CLASS DIVISIONS where this subject has been taught
    # (Not number of days, but number of different classes like SE COMP-A, SE COMP-B)
    total_classes = db.execute("""
        SELECT COUNT(DISTINCT u.class_name) as count
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        WHERE a.subject = ?
    """, (faculty_subject,)).fetchone()['count'] or 0
    
    # Get student-wise attendance FOR THIS SUBJECT ONLY
    student_attendance = db.execute("""
        SELECT 
            u.roll_number,
            u.full_name,
            COUNT(a.id) as total_days,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent,
            CASE 
                WHEN COUNT(a.id) > 0 
                THEN ROUND(SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) * 100.0 / COUNT(a.id), 1)
                ELSE 0
            END as percentage
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id AND a.subject = ?
        WHERE u.role = 'student' AND u.class_name = ?
        GROUP BY u.id
        ORDER BY u.roll_number
    """, (faculty_subject, selected_class)).fetchall()
    
    # Calculate statistics
    avg_attendance = 0
    below_75 = 0
    perfect = 0
    
    if student_attendance:
        total_pct = sum([s['percentage'] for s in student_attendance if s['percentage']])
        avg_attendance = round(total_pct / len(student_attendance) if len(student_attendance) > 0 else 0, 0)
        below_75 = len([s for s in student_attendance if s['percentage'] and s['percentage'] < 75])
        perfect = len([s for s in student_attendance if s['percentage'] and s['percentage'] == 100])
    
    return render_template('faculty_view_attendance.html',
                         students=student_attendance,
                         classes=classes,
                         selected_class=selected_class,
                         total_classes=total_classes,
                         avg_attendance=int(avg_attendance),
                         below_75=below_75,
                         perfect=perfect,
                         faculty_subject=faculty_subject)


@app.route('/faculty/send-notice', methods=['GET', 'POST'])
@faculty_required
def faculty_send_notice():
    db = get_db()
    
    faculty = db.execute('SELECT subject FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    faculty_subject = faculty['subject'] if faculty and faculty['subject'] else 'General'
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        faculty_name = session.get('user_name', 'Faculty')
        author = f"{faculty_name} - {faculty_subject}"
        
        db.execute(
            'INSERT INTO notices (title, content, author, created_at) VALUES (?, ?, ?, ?)',
            (title, content, author, datetime.now().strftime('%Y-%m-%d'))
        )
        db.commit()
        
        flash('Notice sent successfully to students!', 'success')
        return redirect(url_for('faculty_dashboard'))
    
    return render_template('faculty_send_notice.html', faculty_subject=faculty_subject)

if __name__ == '__main__':
    app.run(debug=True)
