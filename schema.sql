-- Initalize the database
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS checkBook;
DROP TABLE IF EXISTS membership;
DROP TABLE IF EXISTS book;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS library;


CREATE TABLE users (
    uid SERIAL PRIMARY KEY, 
    name TEXT NOT NULL, 
    hash TEXT NOT NULL, 
    membership_id TEXT[], -- memberships the user has
    bids TEXT[] -- Books the user has checked out
);

CREATE TABLE library (
                    lid SERIAL PRIMARY KEY,
                    bids TEXT[], -- books available in the library
                    membership_id TEXT
);

CREATE TABLE book (
    bid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER NOT NULL,
    book_cover TEXT NOT NULL
);

CREATE TABLE membership (
    lid INTEGER NOT NULL,
    uid INTEGER NOT NULL,
    date_of_acquisition DATE,
    PRIMARY KEY (lid, uid),
    FOREIGN KEY (lid) REFERENCES library (lid),
    FOREIGN KEY (uid) REFERENCES users (uid)
);

CREATE TABLE checkBook (
    lid INTEGER NOT NULL,
    uid INTEGER NOT NULL,
    bid TEXT NOT NULL,
    checkIn BOOLEAN,
    checkOutDate DATE,
    duration INTEGER,
    PRIMARY KEY (lid, uid, bid),
    FOREIGN KEY (lid) REFERENCES library (lid),
    FOREIGN KEY (uid) REFERENCES users (uid),
    FOREIGN KEY (bid) REFERENCES book (bid)
);