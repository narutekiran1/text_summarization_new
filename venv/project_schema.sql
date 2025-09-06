-- ==========================================
-- Project Schema for Text Summarization
-- User: proj_user
-- ==========================================

-- Drop old tables (if they exist)
DROP TABLE summaries CASCADE CONSTRAINTS;
DROP TABLE news_articles CASCADE CONSTRAINTS;
DROP TABLE users CASCADE CONSTRAINTS;
DROP TABLE roles CASCADE CONSTRAINTS;

-- ==========================================
-- Roles Table
-- ==========================================
CREATE TABLE roles (
    id NUMBER PRIMARY KEY,
    role_name VARCHAR2(100) NOT NULL UNIQUE
);

CREATE SEQUENCE roles_seq START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER roles_trg
BEFORE INSERT ON roles
FOR EACH ROW
WHEN (new.id IS NULL)
BEGIN
    SELECT roles_seq.NEXTVAL INTO :new.id FROM dual;
END;
/

-- ==========================================
-- Users Table
-- ==========================================
CREATE TABLE users (
    id NUMBER PRIMARY KEY,
    username VARCHAR2(255) NOT NULL UNIQUE,
    password VARCHAR2(255) NOT NULL,
    role_id NUMBER NOT NULL,
    CONSTRAINT fk_role FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE SEQUENCE users_seq START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER users_trg
BEFORE INSERT ON users
FOR EACH ROW
WHEN (new.id IS NULL)
BEGIN
    SELECT users_seq.NEXTVAL INTO :new.id FROM dual;
END;
/

-- ==========================================
-- News Articles Table
-- ==========================================
CREATE TABLE news_articles (
    id NUMBER PRIMARY KEY,
    title VARCHAR2(500) NOT NULL,
    source VARCHAR2(255),
    url VARCHAR2(1000),
    language VARCHAR2(10),
    published_date DATE DEFAULT SYSDATE
);

CREATE SEQUENCE news_articles_seq START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER news_articles_trg
BEFORE INSERT ON news_articles
FOR EACH ROW
WHEN (new.id IS NULL)
BEGIN
    SELECT news_articles_seq.NEXTVAL INTO :new.id FROM dual;
END;
/

-- ==========================================
-- Summaries Table
-- ==========================================
CREATE TABLE summaries (
    id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL,
    news_id NUMBER,
    original_text CLOB NOT NULL,
    summarized_text CLOB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_news FOREIGN KEY (news_id) REFERENCES news_articles(id)
);

CREATE SEQUENCE summaries_seq START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER summaries_trg
BEFORE INSERT ON summaries
FOR EACH ROW
WHEN (new.id IS NULL)
BEGIN
    SELECT summaries_seq.NEXTVAL INTO :new.id FROM dual;
END;
/

-- ==========================================
-- Insert Initial Roles
-- ==========================================
INSERT INTO roles (role_name) VALUES ('Admin');
INSERT INTO roles (role_name) VALUES ('User');

COMMIT;
