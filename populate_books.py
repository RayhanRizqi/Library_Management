import psycopg2
import csv
import requests
from PIL import Image
from io import BytesIO

def populate_books():
    # Connect to the database
    db = psycopg2.connect(database="flask_db", user="postgres",
                          password="root", host="localhost", port="5432")
    cursor = db.cursor()

    create_library_query = """
    INSERT INTO library (bids, membership_id)
    VALUES (ARRAY[]::TEXT[], 'Library A')
    RETURNING lid;
    """
    cursor.execute(create_library_query)
    library_id = cursor.fetchone()[0]
    print(f"Library created with ID: {library_id}")

    create_library_query = """
    INSERT INTO library (bids, membership_id)
    VALUES (ARRAY[]::TEXT[], 'Library B')
    RETURNING lid;
    """
    cursor.execute(create_library_query)
    library_id = cursor.fetchone()[0]
    print(f"Library created with ID: {library_id}")

    # Open the CSV file with comma delimiter
    with open("cleaned_books.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')  # Use comma as the delimiter

        # Print the column names to confirm the headers are correct
        print("CSV headers:", reader.fieldnames)

        book_count_limit = 100
        curr_book_count = 0

        for row in reader:
            # Extract data from the CSV row and strip any extra spaces
            bid = row['ISBN'].strip()
            title = row['Book-Title'].strip()
            author = row['Book-Author'].strip()
            year = row['Year-Of-Publication'].strip()
            book_cover = row['Image-URL-L'].strip()

            try:
                year = int(year)  # Convert year to integer
            except (ValueError, TypeError):
                print(f"Skipping row due to invalid year: {year}")
                continue

            # Ensure all necessary fields are present
            if bid and title and author and year and book_cover and curr_book_count < book_count_limit:
                # Prepare the SQL query for inserting into the book table
                insert_book_query = """
                INSERT INTO book (bid, title, author, year, book_cover)
                VALUES (%s, %s, %s, %s, %s)
                """
                # Execute the query with the extracted data
                cursor.execute(insert_book_query, (bid, title, author, year, book_cover))

                update_library_query = """
                    UPDATE library
                    SET bids = array_append(bids, %s)
                    WHERE lid = %s;
                    """
                
                if curr_book_count < book_count_limit // 2:
                    cursor.execute(update_library_query, (bid, 1))
                else:
                    cursor.execute(update_library_query, (bid, 2))

                curr_book_count += 1
    
    # Commit the changes
    db.commit()
    cursor.close()
    db.close()
    print("Database populated")

if __name__ == "__main__":
    populate_books()