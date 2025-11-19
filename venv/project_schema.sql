DROP TABLE IF EXISTS summaries;
DROP TABLE IF EXISTS news_articles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

-- Roles
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(100) UNIQUE NOT NULL
);

-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role_id INTEGER REFERENCES roles(id)
);

-- News Articles
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source VARCHAR(255),
    url TEXT,
    language VARCHAR(20),
    summary TEXT,
    published_date DATE DEFAULT CURRENT_DATE,
    user_id INT REFERENCES users(id)
);

-- Summaries
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    news_id INT,
    original_text TEXT NOT NULL,
    summarized_text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Roles
INSERT INTO roles(role_name) VALUES ('Admin'), ('User');
