import psycopg2
import click

def get_db():
    
    db = psycopg2.connect(database="flask_db", user="postgres",
                        password="root", host="localhost", port="5432")
    return db

def init_db():

    db = get_db()

    with open("clear_schema.sql", "r") as f:
        sql_script = f.read()

    cursor = db.cursor()
    cursor.execute(sql_script)
    db.commit()
    db.close()

@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Database cleared.")

# main
if __name__ == "__main__":
    init_db_command()