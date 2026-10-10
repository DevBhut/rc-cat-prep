-- 1. USERS
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- 2. OTP CODES (signup / password reset)
CREATE TABLE otps (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    purpose VARCHAR(20) DEFAULT 'signup', -- 'signup' | 'reset'
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. PASSAGES
CREATE TABLE passages (
    id SERIAL PRIMARY KEY,              -- Global sequential 1..117
    source VARCHAR(50) NOT NULL,      -- 'GMAT-NEW' | 'GMAT-22' | 'GMAT-15' | 'OG'
    passage_number INTEGER NOT NULL,  -- 1..63, 1..22, 1..15, 1..17 (local to source)
    title VARCHAR(500),
    passage_text TEXT NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, passage_number)
);

-- 4. QUESTIONS
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    passage_id INTEGER REFERENCES passages(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,   -- 1, 2, 3... within the passage
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    option_e TEXT NOT NULL,
    correct_option VARCHAR(1) NOT NULL CHECK (correct_option IN ('A','B','C','D','E')),
    explanation TEXT,                 -- Nullable for current PDF; populated for future PDFs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(passage_id, question_number)
);

-- 5. ATTEMPTS (one row per time a user starts & finishes a passage)
CREATE TABLE attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    passage_id INTEGER REFERENCES passages(id) ON DELETE CASCADE,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_time_seconds INTEGER,         -- Timer value at submission
    score INTEGER,                      -- Number of correct answers
    total_questions INTEGER,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. ATTEMPT RESPONSES (individual answers per attempt)
CREATE TABLE attempt_responses (
    id SERIAL PRIMARY KEY,
    attempt_id INTEGER REFERENCES attempts(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    selected_option VARCHAR(1),
    is_correct BOOLEAN,
    time_spent_seconds INTEGER DEFAULT 0,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(attempt_id, question_id)
);

-- 7. USER PASSAGE STATUS (denormalized "latest state" for fast filtering)
CREATE TABLE user_passage_status (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    passage_id INTEGER REFERENCES passages(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'unsolved' CHECK (status IN ('unsolved', 'in_progress', 'solved')),
    best_score INTEGER DEFAULT 0,
    best_time_seconds INTEGER,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    UNIQUE(user_id, passage_id)
);

-- Indexes for performance
CREATE INDEX idx_questions_passage ON questions(passage_id);
CREATE INDEX idx_attempts_user ON attempts(user_id);
CREATE INDEX idx_attempts_passage ON attempts(passage_id);
CREATE INDEX idx_user_passage_status_user ON user_passage_status(user_id);
CREATE INDEX idx_otps_email ON otps(email, created_at DESC);
