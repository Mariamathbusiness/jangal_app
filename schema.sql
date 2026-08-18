CREATE TABLE IF NOT EXISTS schools (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    director_name TEXT,               -- <-- AJOUTÉ
    address TEXT,
    phone TEXT,
    email TEXT,
    logo_path TEXT,
    level_types TEXT,
    grading_config TEXT,
    start_date DATE,                  -- <-- AJOUTÉ
    end_date DATE,                    -- <-- AJOUTÉ
    status TEXT DEFAULT 'active',     -- <-- AJOUTÉ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
   id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    photo_path TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS academic_years (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    label TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    is_current INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS levels (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    name TEXT NOT NULL,
    level_type TEXT NOT NULL,
    grading_scale_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS classes (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    level_id INTEGER,
    label TEXT NOT NULL,
    main_teacher_id INTEGER,
    room TEXT,
    capacity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    name TEXT NOT NULL,
    code TEXT,
    coefficient REAL DEFAULT 1.0,
    is_ue INTEGER DEFAULT 0,
    credits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    matricule TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth DATE,
    gender TEXT,
    photo_path TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    parent_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enrollments (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    student_id INTEGER,
    class_id INTEGER,
    academic_year_id INTEGER,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS grades (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    enrollment_id INTEGER,
    subject_id INTEGER,
    teacher_id INTEGER,
    grade_value REAL,
    max_value REAL,
    grade_type TEXT,
    session TEXT,
    coefficient REAL DEFAULT 1.0,
    semester INTEGER,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS grading_scales (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    level_type TEXT NOT NULL,
    scale_config TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fees (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    level_id INTEGER,
    fee_type TEXT NOT NULL,
    amount REAL NOT NULL,
    academic_year_id INTEGER,
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    student_id INTEGER,
    fee_id INTEGER,
    amount REAL NOT NULL,
    payment_date DATE,
    payment_method TEXT,
    receipt_number TEXT,
    received_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    expense_date DATE,
    recorded_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS time_slots (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_id INTEGER,
    day_of_week INTEGER NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS schedules (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    class_id INTEGER,
    subject_id INTEGER,
    teacher_id INTEGER,
    day_of_week INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attendances (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    enrollment_id INTEGER,
    date DATE NOT NULL,
    status TEXT NOT NULL,
    time_slot_id INTEGER,
    marked_by INTEGER,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS parents (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    user_id INTEGER,
    student_ids TEXT,
    relationship TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_uuid TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_students_matricule ON students(matricule);
CREATE INDEX IF NOT EXISTS idx_grades_enrollment ON grades(enrollment_id);
CREATE INDEX IF NOT EXISTS idx_payments_student ON payments(student_id);
CREATE INDEX IF NOT EXISTS idx_schedules_class ON schedules(class_id);
CREATE TABLE IF NOT EXISTS adhesions (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    school_name TEXT,
    school_type TEXT,
    student_count TEXT,
    address TEXT,
    creation_year TEXT,
    contact_name TEXT,
    contact_role TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    current_system TEXT,
    challenges TEXT,
    features_interest TEXT,
    start_timeline TEXT,
    has_computer TEXT,
    message TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);