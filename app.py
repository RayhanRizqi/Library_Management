import os
from flask import Flask, render_template, request, redirect, session, flash, jsonify
import psycopg2
from flask_session import Session
from psycopg2.extras import RealDictCursor
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Connection to the PostgreSQL
conn = psycopg2.connect(database="flask_db", user="postgres",
                        password="root", host="localhost", port="5432")

# the cursor for the PostgreSQL: use db to perform a sql query
db = conn.cursor(cursor_factory=RealDictCursor)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Flask route for the homepage, directs to index.html
@app.route('/')
@login_required
def index():
    """Show user's details, memberships, and checked-out books"""

    # Get the user ID from the session
    user_id = session['user_id']

    # Query database for user information
    db.execute("SELECT name, membership_id, bids FROM users WHERE uid = %s", (user_id,))
    user = db.fetchone()

    # User's name
    username = user['name']

    # User's memberships
    memberships = user['membership_id'] if user['membership_id'] else []

    # Get books that the user has checked out (bids)
    if user['bids']:
        db.execute("SELECT * FROM book WHERE bid = ANY(%s)", (user['bids'],))
        books = db.fetchall()
    else:
        books = []

    # Render the index page with the user's details
    return render_template('index.html', username=username, memberships=memberships, books=books)

# Flask route for the logout page, which logs the user out of the profile
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# Flask route for looking at the list of libraries, directs to viewLibrary.html
@app.route("/view_library")
@login_required
def view_library():
    """View books in libraries"""

    # Gets the list of all libraries in the system
    get_libraries_query = "SELECT membership_id FROM library"
    db.execute(get_libraries_query)
    libraries = db.fetchall()

    # Directs the user to viewLibrary.html
    return render_template("viewLibrary.html", libraries=libraries)

# Flask route for the membership page, which is in membership.html
@app.route("/membership", methods=["GET", "POST"])
@login_required
def membership_page():
    """Show user's memberships and options to acquire new ones"""
    # Gets the user's id
    user_id = session['user_id']

    # Gets all the info of the uesr
    db.execute("SELECT * FROM users WHERE uid = %s", (user_id,))
    user = db.fetchone()

    # Gets the list of membership id's the user has. If none, make one
    if user["membership_id"] is None:
        current_memberships = []
    else:
        current_memberships = user['membership_id']

    # Gets the list of libraries that the user does not have a membership in
    db.execute("""
               SELECT library.* 
               FROM library 
               LEFT JOIN membership ON library.lid=membership.lid AND membership.uid = %s
               WHERE membership.uid IS NULL
               """, (user_id,))
    libraries = db.fetchall()

    # POST route for generating a membership id for the user
    if request.method == "POST":
        # Gets the information of the library that the user wants to get a membership from
        library_id = request.form.get("library_id")
        library_name = request.form.get("library_name")

        # The formula for generating the next membership is this: {library_name}{n+1}
        # library_name is the prefix of the library stored in the library table
        # n is the number of people who has a membership to the library
        db.execute("""
            SELECT COUNT(*)
            FROM membership
            WHERE lid = %s
        """, (library_id,))
        membership_count = db.fetchone()['count']

        # Generates the new membership for the user
        next_membership_id = f"{library_name}{membership_count + 1}"

        # Generates a new row into the membership table to record the transaction
        db.execute("""
            INSERT INTO membership (lid, uid, date_of_acquisition)
            VALUES (%s, %s, %s)
        """, (library_id, user_id, datetime.date.today()))

        # Adds the new membership to the user's membership id list
        current_memberships.append(next_membership_id)

        db.execute("""
            UPDATE users
            SET membership_id = %s
            WHERE uid = %s
        """, (current_memberships, user_id))

        conn.commit()

        # Confirmation displayed to the user for the new membership id
        flash(f"You have successfully obtained {next_membership_id}")

        # Update the user's info to display onto the membership page
        db.execute("SELECT * FROM users WHERE uid = %s", (user_id,))
        user = db.fetchone()
        if user["membership_id"] is None:
            current_memberships = []
        else:
            current_memberships = user['membership_id']

        db.execute("""
                SELECT library.* 
                FROM library 
                LEFT JOIN membership ON library.lid=membership.lid AND membership.uid = %s
                WHERE membership.uid IS NULL
                """, (user_id,))
        libraries = db.fetchall()

    return render_template("membership.html", memberships=current_memberships, libraries=libraries)

# Flask route for viewing the list of books available for checkout in the chosen library
@app.route("/library/<membership_id>", methods=["GET"])
@login_required
def view_specific_library(membership_id):
    """View a specific library based on its membership_id and handle book search."""
    
    # Query to fetch details of the selected library
    db.execute("SELECT * FROM library WHERE membership_id = %s", (membership_id,))
    library_details = db.fetchone()

    # Correcting for edge case
    if not library_details:
        return apology("Library not found", 404)

    # Fetch books based on bids in library.bids
    bids = library_details['bids']
    search_query = request.args.get('search', '')

    # Gets the list of books available in the library
    if bids:
        if search_query:
            # Search for books with titles matching the query
            db.execute("""
                SELECT * FROM book 
                WHERE bid = ANY(%s) AND title ILIKE %s
            """, (bids, f'%{search_query}%'))
        else:
            # Fetch all books if no search query is provided
            db.execute("SELECT * FROM book WHERE bid = ANY(%s)", (bids,))
        books = db.fetchall()
    else:
        books = []

    # Render the template with the books and library details
    return render_template("libraryDetail.html", library=library_details, books=books)

# Flask route for the search bar function in the libraryDetail.html page
@app.route("/library/<membership_id>/search")
@login_required
def search_books_in_library(membership_id):
    """Search for books in the specified library based on the search query"""
    # Gets the content of the search bar
    search_query = request.args.get('query', '')

    # Query to fetch details of the selected library
    db.execute("SELECT * FROM library WHERE membership_id = %s", (membership_id,))
    library_details = db.fetchone()

    if not library_details:
        return jsonify({'books': []})

    # Fetch books based on bids in library.bids
    bids = library_details['bids']
    if bids:
        if search_query:
            # Search for books with titles matching the query
            db.execute("""
                SELECT * FROM book 
                WHERE bid = ANY(%s) AND title ILIKE %s
            """, (bids, f'%{search_query}%'))
        else:
            # Fetch all books if no search query is provided
            db.execute("SELECT * FROM book WHERE bid = ANY(%s)", (bids,))
        books = db.fetchall()
    else:
        books = []

    # Return the filtered books in JSON format
    return jsonify({'books': books})

# Flask route for checking out the book from a library
@app.route("/library/<membership_id>/checkout", methods=["POST"])
@login_required
def checkout_book(membership_id):
    """Handle book checkout process"""
    
    # Get the user ID from the session
    user_id = session['user_id']
    
    # Get the book ID (bid) from the form
    bid = request.form.get('bid')
    
    # Fetch the library details based on membership ID
    db.execute("SELECT * FROM library WHERE membership_id = %s", (membership_id,))
    library = db.fetchone()
    
    if not library:
        return apology("Library not found", 404)
    
    # Check if the user has a membership in the library
    db.execute("""
        SELECT * FROM membership 
        WHERE uid = %s AND lid = %s
    """, (user_id, library['lid']))
    membership = db.fetchone()
    
    if not membership:
        # User does not have the right membership, redirect to the membership page
        return redirect("/membership")
    
    # Check if the user has already checked out the book
    db.execute("""
        SELECT * FROM checkBook
        WHERE uid = %s AND bid = %s AND lid = %s
    """, (user_id, bid, library['lid']))
    already_checked_out = db.fetchone()
    
    if already_checked_out:
        return apology("You have already checked out this book", 400)

    # Add a new row to the checkBook table
    db.execute("""
        INSERT INTO checkBook (lid, uid, bid, checkIn, checkOutDate, duration)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (library['lid'], user_id, bid, False, datetime.date.today(), 4))
    
    # Update the user's bids array
    db.execute("""
        UPDATE users
        SET bids = array_append(bids, %s)
        WHERE uid = %s
    """, (bid, user_id))
    
    # Remove the book from the library's bids array
    db.execute("""
        UPDATE library
        SET bids = array_remove(bids, %s)
        WHERE lid = %s
    """, (bid, library['lid']))
    
    # Commit the transaction to the database
    conn.commit()
    
    # Redirect the user to the index page
    return redirect(f"/library/{membership_id}")

@app.route("/book/<book_id>")
@login_required
def view_book(book_id):
    """Show details of a specific book and calculate return date"""

    # Query the database to get the details of the selected book
    db.execute("SELECT * FROM book WHERE bid = %s", (book_id,))
    book = db.fetchone()

    # If the book does not exist, return an error
    if not book:
        return apology("Book not found", 404)

    # Query the database to get the checkBook details for this book and the current user
    db.execute("""
        SELECT checkOutDate, duration 
        FROM checkBook 
        WHERE bid = %s AND uid = %s AND checkIn = False
    """, (book_id, session['user_id']))
    check_book = db.fetchone()

    print(check_book)  # Debugging statement to see what check_book contains

    # Calculate how many days are left before the book is due
    if check_book:
        checkout_date = check_book.get('checkoutdate')  # Use .get() to avoid KeyError
        duration = check_book.get('duration')  # Use .get() to avoid KeyError

        if checkout_date and duration:
            due_date = checkout_date + datetime.timedelta(days=duration)
            today = datetime.date.today()
            days_left = (due_date - today).days
        else:
            days_left = None  # Handle case where data might be missing or incomplete
    else:
        days_left = None  # This will cover cases where the user has not checked out the book

    # Render the book details template, passing the book and days_left information
    return render_template("book.html", book=book, days_left=days_left)

@app.route("/book/<book_id>/return", methods=["POST"])
@login_required
def return_book(book_id):
    """Handle the process of returning a book to the library."""
    
    # Get the user ID from the session
    user_id = session['user_id']

    # Fetch the library ID where the book was checked out from
    db.execute("""
        SELECT lid FROM checkBook WHERE bid = %s AND uid = %s AND checkIn = False
    """, (book_id, user_id))
    check_book = db.fetchone()

    if not check_book:
        return apology("You haven't checked out this book", 400)
    
    library_id = check_book['lid']

    # Remove the book from the user's bids array
    db.execute("""
        UPDATE users
        SET bids = array_remove(bids, %s)
        WHERE uid = %s
    """, (book_id, user_id))

    # Set the checkIn to True in the checkBook table to mark the return
    db.execute("""
        UPDATE checkBook
        SET checkIn = True
        WHERE bid = %s AND uid = %s AND lid = %s
    """, (book_id, user_id, library_id))

    # Add the book back to the library's bids array
    db.execute("""
        UPDATE library
        SET bids = array_append(bids, %s)
        WHERE lid = %s
    """, (book_id, library_id))

    # Commit the transaction
    conn.commit()

    # Redirect the user back to the book details page with a success message
    flash("You have successfully returned the book.")
    return redirect("/")

# Flask route for the login page, the first page as a new user
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure name was submitted
        if not request.form.get("name"):
            return apology("must provide name", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for name
        name = request.form.get("name")
        db.execute("SELECT * FROM users WHERE name = %s", (name,))
        rows = db.fetchall()

        print("name: " + str(name))
        print("rows: " + str(rows))

        # Ensure name exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid name and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["uid"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
# Flask route for the register page, directing the user to register.html
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Validate submission
        name = request.form.get("name")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Query database for name
        db.execute("SELECT * FROM users WHERE name = %s", (name,))
        rows = db.fetchall()

        # Ensure password == confirmation
        if not (password == confirmation):
            return apology("the passwords do not match", 400)

        # Ensure password not blank
        if password == "" or confirmation == "" or name == "":
            return apology("input is blank", 400)

        # Ensure name does not exists already
        if len(rows) == 1:
            return apology("name already exist", 400)
        else:
            hashcode = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT INTO users (name, hash) VALUES(%s, %s)", (name, hashcode,))
            conn.commit()
            print("user inserted")

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/settings")
@login_required
def settings():
    """Show settings"""
    # Query database
    db.execute("SELECT name FROM users WHERE uid = %s", (session["user_id"],))
    name = db.fetchone()['name']
    return render_template("settings.html", name=name)

@app.route("/passwordupdate", methods=["GET", "POST"])
@login_required
def passwordupdate():
    """Show settings"""

    if request.method == "POST":

        # Validate submission
        currentpassword = request.form.get("currentpassword")
        newpassword = request.form.get("newpassword")
        confirmation = request.form.get("confirmation")

        # Query database for username
        db.execute("SELECT * FROM users WHERE uid = %s", (session["user_id"],))
        rows = db.fetchall()

        # Ensure password == confirmation
        if not (newpassword == confirmation):
            return apology("the passwords do not match", 400)

        # Ensure password not blank
        if currentpassword == "" or newpassword == "" or confirmation == "":
            return apology("input is blank", 400)

       # Ensure password is correct
        if not check_password_hash(rows[0]["hash"], currentpassword):
            return apology("invalid password", 403)
        else:
            hashcode = generate_password_hash(newpassword, method='pbkdf2:sha256', salt_length=8)
            db.execute("UPDATE users SET hash = %s WHERE uid = %s", (hashcode, session["user_id"]))

        # Redirect user to settings
        return redirect("/settings")

    else:
        return render_template("passwordupdate.html")

if __name__ == '__main__':
    app.run(debug=True)
