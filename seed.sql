-- Drop the existing tables if they exist
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS sessions;

-- Recreate the players table
CREATE TABLE players (
    email TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

-- Recreate the sessions table
CREATE TABLE sessions (
    session_start TIMESTAMP NOT NULL,
    session_end TIMESTAMP NOT NULL,
    email TEXT NOT NULL,
    score1 INTEGER NOT NULL,
    score2 INTEGER NOT NULL,
    score3 INTEGER NOT NULL,
    FOREIGN KEY (email) REFERENCES players (email)
);

-- Insert 30 random players into the players table
INSERT INTO players (email, name) VALUES
('luke_skywalker@starwars.com', 'Luke Skywalker'),
('darth_vader@starwars.com', 'Darth Vader'),
('yoda@starwars.com', 'Yoda'),
('han_solo@starwars.com', 'Han Solo'),
('chewbacca@starwars.com', 'Chewbacca'),
('leia_organa@starwars.com', 'Leia Organa'),
('r2d2@starwars.com', 'R2-D2'),
('c3po@starwars.com', 'C-3PO'),
('obi_wan@starwars.com', 'Obi-Wan Kenobi'),
('anakin_skywalker@starwars.com', 'Anakin Skywalker'),
('darth_maul@starwars.com', 'Darth Maul'),
('jar_jar@starwars.com', 'Jar Jar Binks'),
('twinkle_twinkle@nurseryrhymes.com', 'Twinkle Twinkle'),
('mary_had_a_lamb@nurseryrhymes.com', 'Mary'),
('peter_piper@nurseryrhymes.com', 'Peter Piper'),
('jack_and_jill@nurseryrhymes.com', 'Jack and Jill'),
('itsy_bitsy@nurseryrhymes.com', 'Itsy Bitsy Spider'),
('old_mcdonald@nurseryrhymes.com', 'Old McDonald'),
('george_costanza@seinfeld.com', 'George Costanza'),
('jerry_seinfeld@seinfeld.com', 'Jerry Seinfeld'),
('elaine_benes@seinfeld.com', 'Elaine Benes'),
('kramer@seinfeld.com', 'Cosmo Kramer'),
('newman@seinfeld.com', 'Newman'),
('frank_costanza@seinfeld.com', 'Frank Costanza'),
('estelle_costanza@seinfeld.com', 'Estelle Costanza'),
('peterman@seinfeld.com', 'J. Peterman'),
('putty@seinfeld.com', 'David Puddy'),
('uncle_leo@seinfeld.com', 'Uncle Leo'),
('george_washington@seinfeld.com', 'George Washington'),
('mulva@seinfeld.com', 'Mulva');

-- Insert 100 random sessions for these players
-- Each session has 3 scores ranging between 20 and 400
INSERT INTO sessions (session_start, session_end, email, score1, score2, score3)
SELECT
    datetime('now', '-' || (ABS(RANDOM() % 365)) || ' days'),  -- Random session start time within the last year
    datetime('now', '-' || (ABS(RANDOM() % 365)) || ' days', '+' || (ABS(RANDOM() % 5)) || ' hours'),  -- Random session end time, a few hours later
    email,
    ABS(RANDOM() % 381) + 20,  -- Random score between 20 and 400
    ABS(RANDOM() % 381) + 20,  -- Random score between 20 and 400
    ABS(RANDOM() % 381) + 20   -- Random score between 20 and 400
FROM
    players
ORDER BY RANDOM()
LIMIT 100;  -- Limit to 100 random sessions
