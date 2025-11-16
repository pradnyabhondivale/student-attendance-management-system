import sqlite3
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
import random


def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Drop existing tables
    cursor.execute('DROP TABLE IF EXISTS attendance')
    cursor.execute('DROP TABLE IF EXISTS notices')
    cursor.execute('DROP TABLE IF EXISTS users')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            class_name TEXT,
            roll_number TEXT,
            branch TEXT,
            year INTEGER,
            subject TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            subject TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')

    # Create notices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # === INSERT ADMIN ===
    cursor.execute(
        "INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?)",
        ('Admin', 'admin@attendease.com', 
         generate_password_hash('Admin@2025', method='pbkdf2:sha256'), 
         'admin')
    )

    # === INSERT FACULTY MEMBERS ===
    faculty_data = [
        ('Dr. Rajesh Patil', 'rajesh.patil@college.edu', 'Rajesh@123', 'Computer Science', 'Data Structures'),
        ('Prof. Sneha Deshmukh', 'sneha.deshmukh@college.edu', 'Sneha@456', 'Computer Science', 'Object Oriented Programming'),
        ('Dr. Amit Kulkarni', 'amit.kulkarni@college.edu', 'Amit@789', 'Information Technology', 'Database Management Systems'),
        ('Prof. Priya Joshi', 'priya.joshi@college.edu', 'Priya@321', 'Information Technology', 'Operating Systems'),
        ('Dr. Vikram Sharma', 'vikram.sharma@college.edu', 'Vikram@654', 'Computer Science', 'Discrete Mathematics'),
    ]

    for name, email, password, branch, subject in faculty_data:
        cursor.execute(
            "INSERT INTO users (full_name, email, password, role, branch, subject) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, 
             generate_password_hash(password, method='pbkdf2:sha256'), 
             'faculty', branch, subject)
        )

    # === INSERT STUDENTS ===
    # SE COMP-A
    students_csa = [
        ('Aditya Patil', 'aditya.patil@student.edu', 'Aditya@2201', 'SE COMP-A', 'C2201', 'Computer Science', 2),
        ('Priyanka Deshmukh', 'priyanka.deshmukh@student.edu', 'Priyanka@2202', 'SE COMP-A', 'C2202', 'Computer Science', 2),
        ('Rahul Kulkarni', 'rahul.kulkarni@student.edu', 'Rahul@2203', 'SE COMP-A', 'C2203', 'Computer Science', 2),
        ('Sneha Joshi', 'sneha.joshi@student.edu', 'Sneha@2204', 'SE COMP-A', 'C2204', 'Computer Science', 2),
        ('Vaibhav Pawar', 'vaibhav.pawar@student.edu', 'Vaibhav@2205', 'SE COMP-A', 'C2205', 'Computer Science', 2),
        ('Sakshi Shirke', 'sakshi.shirke@student.edu', 'Sakshi@2206', 'SE COMP-A', 'C2206', 'Computer Science', 2),
    ]
    
    # SE COMP-B
    students_csb = [
        ('Omkar Shinde', 'omkar.shinde@student.edu', 'Omkar@2207', 'SE COMP-B', 'C2207', 'Computer Science', 2),
        ('Pooja Kadam', 'pooja.kadam@student.edu', 'Pooja@2208', 'SE COMP-B', 'C2208', 'Computer Science', 2),
        ('Rohit Bhosale', 'rohit.bhosale@student.edu', 'Rohit@2209', 'SE COMP-B', 'C2209', 'Computer Science', 2),
        ('Vaishnavi More', 'vaishnavi.more@student.edu', 'Vaishnavi@2210', 'SE COMP-B', 'C2210', 'Computer Science', 2),
        ('Saurabh Jadhav', 'saurabh.jadhav@student.edu', 'Saurabh@2211', 'SE COMP-B', 'C2211', 'Computer Science', 2),
        ('Manasi Rane', 'manasi.rane@student.edu', 'Manasi@2212', 'SE COMP-B', 'C2212', 'Computer Science', 2),
    ]
    
    # TE IT
    students_it = [
        ('Yash Kale', 'yash.kale@student.edu', 'Yash@2101', 'TE IT', 'I2101', 'Information Technology', 3),
        ('Anjali Sawant', 'anjali.sawant@student.edu', 'Anjali@2102', 'TE IT', 'I2102', 'Information Technology', 3),
        ('Pratik Naik', 'pratik.naik@student.edu', 'Pratik@2103', 'TE IT', 'I2103', 'Information Technology', 3),
        ('Nikita Gaikwad', 'nikita.gaikwad@student.edu', 'Nikita@2104', 'TE IT', 'I2104', 'Information Technology', 3),
    ]

    # Insert all students
    all_students = students_csa + students_csb + students_it
    for name, email, password, class_name, roll, branch, year in all_students:
        cursor.execute(
            "INSERT INTO users (full_name, email, password, role, class_name, roll_number, branch, year) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, email, 
             generate_password_hash(password, method='pbkdf2:sha256'), 
             'student', class_name, roll, branch, year)
        )

    # === SUBJECTS BY CLASS ===
    subjects_map = {
        'SE COMP-A': [
            'Data Structures',
            'Object Oriented Programming',
            'Discrete Mathematics',
            'Digital Logic Design',
            'Computer Graphics'
        ],
        'SE COMP-B': [
            'Data Structures',
            'Object Oriented Programming',
            'Discrete Mathematics',
            'Digital Logic Design',
            'Computer Graphics'
        ],
        'TE IT': [
            'Database Management Systems',
            'Operating Systems',
            'Computer Networks',
            'Software Engineering',
            'Web Technology'
        ]
    }

    # === GENERATE ATTENDANCE (Last 40 working days) ===
    students = cursor.execute("SELECT id, class_name FROM users WHERE role='student'").fetchall()
    
    start_date = date.today() - timedelta(days=60)
    working_days = 0
    current_date = start_date
    
    while working_days < 40:
        if current_date.weekday() < 5:  # Only weekdays
            working_days += 1
            
            for student_id, class_name in students:
                subjects = subjects_map.get(class_name, ['General'])
                daily_subjects = random.sample(subjects, min(random.randint(2, 3), len(subjects)))
                
                for subject in daily_subjects:
                    rand = random.randint(1, 100)
                    if rand <= 10:
                        attendance_rate = random.randint(90, 100)
                    elif rand <= 70:
                        attendance_rate = random.randint(75, 89)
                    elif rand <= 90:
                        attendance_rate = random.randint(60, 74)
                    else:
                        attendance_rate = random.randint(40, 59)
                    
                    status = 'Present' if random.randint(1, 100) <= attendance_rate else 'Absent'
                    
                    cursor.execute(
                        "INSERT INTO attendance (student_id, date, subject, status) VALUES (?, ?, ?, ?)",
                        (student_id, current_date.strftime('%Y-%m-%d'), subject, status)
                    )
        
        current_date += timedelta(days=1)

    # === INSERT NOTICES ===
    notices_data = [
        ('Mid-Semester Examination Schedule',
         'Mid-semester examinations for SE COMP (A & B) and TE IT will be conducted from November 18-25, 2025. All students must carry their college ID cards and examination hall tickets.',
         'Dr. Rajesh Patil - Computer Science',
         '2025-11-01'),
        
        ('Data Structures Assignment Extension',
         'The deadline for Data Structures assignment (SE COMP A & B) has been extended to November 12, 2025. Submissions will be accepted via college portal only.',
         'Prof. Sneha Deshmukh - Computer Science',
         '2025-11-02'),
        
        ('Diwali Holiday Notice',
         'The college will remain closed from November 10-14, 2025 for Diwali festival celebrations. Regular classes will resume from November 15, 2025.',
         'Admin',
         '2025-11-03'),
        
        ('Guest Lecture on AI & ML',
         'A guest lecture on Artificial Intelligence and Machine Learning will be conducted on November 16, 2025 at 11:00 AM in Seminar Hall. All TE IT students are required to attend.',
         'Dr. Amit Kulkarni - Information Technology',
         '2025-11-04'),
    ]

    for title, content, author, created_at in notices_data:
        cursor.execute(
            "INSERT INTO notices (title, content, author, created_at) VALUES (?, ?, ?, ?)",
            (title, content, author, created_at)
        )

    conn.commit()
    conn.close()
    
    print("Database initialized successfully!")


if __name__ == '__main__':
    init_db()
