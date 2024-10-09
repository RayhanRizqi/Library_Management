-- Initalize the database
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS checkBook;
DROP TABLE IF EXISTS membership;
DROP TABLE IF EXISTS book;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS library;


CREATE TABLE users (
    uid SERIAL PRIMARY KEY, -- user id
    name TEXT NOT NULL, -- user's name
    hash TEXT NOT NULL, -- user's password stored after encryption using SHA256
    membership_id TEXT[], -- memberships the user has
    bids TEXT[] -- Books the user has checked out
);

CREATE TABLE library (
                    lid SERIAL PRIMARY KEY, -- library id
                    bids TEXT[], -- books available in the library
                    membership_id TEXT -- the prefix of a member's membership id to this library
);

CREATE TABLE book (
    bid TEXT PRIMARY KEY, -- book id
    title TEXT NOT NULL, -- book title
    author TEXT NOT NULL, -- book's author
    year INTEGER NOT NULL, -- publishing year
    book_cover TEXT NOT NULL -- book's front cover in the form of a url link
);

CREATE TABLE membership (
    lid INTEGER NOT NULL, -- foreign key for the library id
    uid INTEGER NOT NULL, -- foreign key for the user id
    date_of_acquisition DATE, -- the date that the user got the membership
    PRIMARY KEY (lid, uid),
    FOREIGN KEY (lid) REFERENCES library (lid),
    FOREIGN KEY (uid) REFERENCES users (uid)
);

CREATE TABLE checkBook (
    lid INTEGER NOT NULL, -- foreign key for the library id
    uid INTEGER NOT NULL, -- foreign key for the user id
    bid TEXT NOT NULL, -- foreign key for the book id
    checkIn BOOLEAN, -- True if the book has been checked back into the library
    checkOutDate DATE, -- the date the book got checked out
    duration INTEGER, -- the number of days before the user has to return the book
    PRIMARY KEY (lid, uid, bid),
    FOREIGN KEY (lid) REFERENCES library (lid),
    FOREIGN KEY (uid) REFERENCES users (uid),
    FOREIGN KEY (bid) REFERENCES book (bid)
);
