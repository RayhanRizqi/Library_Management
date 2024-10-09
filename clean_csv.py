import csv
import requests
from PIL import Image
from io import BytesIO

# Function to check if the image size is not 1x1
def is_valid_image(url, headers):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.size != (1, 1):
                return True
            else:
                print(f"Image at {url} is 1x1")
        else:
            print(f"Failed to fetch image from {url}, status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching image from {url}: {e}")
    return False

# Function to clean the CSV and write to a new cleaned CSV
def clean_books_csv(input_csv, output_csv):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    # Use 'ISO-8859-1' to handle non-UTF-8 characters
    with open(input_csv, newline='', encoding='ISO-8859-1') as csvfile, open(output_csv, mode='w', newline='', encoding='utf-8') as cleaned_csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(cleaned_csvfile, fieldnames=fieldnames)

        # Write the headers to the cleaned CSV file
        writer.writeheader()

        for row in reader:
            # Extract relevant data
            bid = row.get("ISBN")
            title = row.get("Book-Title")
            author = row.get("Book-Author")
            year = row.get("Year-Of-Publication")
            book_cover = row.get("Image-URL-L")

            # Ensure title, author, isbn, year, and book_cover are not NULL or empty
            if bid and title and author and year and book_cover:
                try:
                    # Ensure the year is an integer
                    year = int(year)

                    # Check if the book cover image is valid (not 1x1)
                    if is_valid_image(book_cover, headers):
                        # Write the valid row to the cleaned CSV
                        writer.writerow(row)
                    else:
                        print(f"Invalid image for ISBN: {bid}")
                except ValueError:
                    print(f"Invalid year for ISBN: {bid}")
            else:
                print(f"Missing required data for ISBN: {bid}")

if __name__ == "__main__":
    input_csv = "books.csv"
    output_csv = "cleaned_books.csv"
    clean_books_csv(input_csv, output_csv)
    print("Cleaned CSV file created.")
