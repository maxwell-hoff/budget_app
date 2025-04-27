import sqlite3
import argparse

def inspect_database(inspect_table_name, inspect_row_limit):
    conn = sqlite3.connect('instance/finance.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables in database:")
    for table in tables:
        table_name = table[0]
        inspect_table(cursor, table_name)
    
    if inspect_table_name is not None:
        inspect_table(cursor, inspect_table_name, limit=inspect_row_limit)
    
    conn.close()

def inspect_table(cursor, table_name, limit=5):
    print(f"\nTable: {table_name}")
    
    # Get table structure
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"Total rows: {count}")
    
    # Show first few rows
    if count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
        rows = cursor.fetchall()
        print("\nFirst 5 rows:")
        for row in rows:
            print(f"  {row}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect SQLite database")
    parser.add_argument("--inspect_table_name", type=str, default=None, help="Table you want to inspect")
    parser.add_argument("--inspect_row_limit", type=str, default=100, help="Row limit for the table you want to inspect")
    args = parser.parse_args()
    inspect_database(args.inspect_table_name, args.inspect_row_limit) 