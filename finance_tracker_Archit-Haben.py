import mysql.connector
import hashlib
import tkinter as tk
from tkinter import messagebox


# Function to connect to MySQL server (without using a database)
def connect_to_server():
    try:
        connection = mysql.connector.connect(host='localhost', user='root', password='')
        if connection.is_connected():
            print("Connected to MySQL server successfully!")
            return connection
    except mysql.connector.Error as e:
        print("Error while connecting to MySQL server:", e)
        return None

# Function to connect to the finance_tracker database, creating it if it doesn't exist
def connect_to_db():
    # Connect to the server first
    server_connection = connect_to_server()
    if server_connection is None:
        return None

    # Create database if it doesn't exist
    create_database_if_not_exists(server_connection)
    server_connection.close()  # Close initial connection to the server

    # Connect to the newly created or existing 'finance_tracker' database
    try:
        connection = mysql.connector.connect(host='localhost', database='finance_tracker', user='root', password='')
        if connection.is_connected():
            print("Connected to 'finance_tracker' database successfully!")
            return connection
    except mysql.connector.Error as e:
        print("Error while connecting to MySQL:", e)
        return None


# Function to create the database if it doesn't exist
def create_database_if_not_exists(connection):
    cursor = connection.cursor()
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS finance_tracker")
        connection.commit()
        print("Database 'finance_tracker' checked/created successfully.")
    except mysql.connector.Error as e:
        print("Error creating database:", e)
    cursor.close()

# Function to create tables if they don't exist
def create_tables_if_not_exists(connection):
    cursor = connection.cursor()
    try:
        # Creates the users table without 'email' column
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            budget DECIMAL(10, 2) DEFAULT 0)""")

        # Ensures 'budget' column exists and adds it if missing
        cursor.execute("SHOW COLUMNS FROM users LIKE 'budget'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN budget DECIMAL(10, 2) DEFAULT 0")
            print("Added 'budget' column to 'users' table.")

        # Create the transactions table with 'transaction_id' column as primary key
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            amount DECIMAL(10, 2),
            description VARCHAR(255),
            category VARCHAR(255),
            date DATE,
            FOREIGN KEY (username) REFERENCES users(username))""")
        connection.commit()
    except mysql.connector.Error as e:
        print("Error creating or updating tables:", e)
    cursor.close()



# Function to hash passwords before storing them
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to create a new user
def create_user(connection, username, password):
    try:
        cursor = connection.cursor()
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash, budget) VALUES (%s, %s, %s)", 
                       (username, hashed_password, 0))
        connection.commit()
        print("User created successfully!")
    except mysql.connector.Error as e:
        print("Error creating user:", e)


# Function to validate user login
def check_user(connection, username, password):
    try:
        cursor = connection.cursor()
        hashed_password = hash_password(password)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password_hash = %s", (username, hashed_password))
        user = cursor.fetchone()
        if user:
            print(f"Login successful, welcome {username}!")
            check_budget_progress(connection, username)  # Check budget after logging in
            return True
        else:
            return False
    except mysql.connector.Error as e:
        print("Error checking user:", e)
        return False


#Function to set budget
def set_budget(connection, username, budget_amount):
    try:
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET budget = %s WHERE username = %s", (budget_amount, username))
        connection.commit()
        print("Budget set successfully!")
    except mysql.connector.Error as e:
        print("Error setting budget:", e)
    finally:
        cursor.close()

# Function to add a new transaction
def add_transaction(connection, username, amount, description, category):
    cursor = connection.cursor()
    query = """INSERT INTO transactions (username, amount, description, category)VALUES (%s, %s, %s, %s)"""
    values = (username, amount, description, category)
    try:
        # Adds the new transaction
        cursor.execute(query, values)
        connection.commit()
        print("Transaction added successfully.")
        
        # After adding the transaction, checks if the budget is exceeded
        check_budget_progress(connection, username)
        
    except mysql.connector.Error as e:
        print(f"An error occurred while adding the transaction: {e}")
    finally:
        cursor.close()



# Function to display all transactions with their IDs for the user to select
def display_transactions(connection, username):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT transaction_id, amount, description, category FROM transactions WHERE username = %s", (username,))
        transactions = cursor.fetchall()

        if transactions:
            print("\nTransaction ID | Amount | Description | Category")
            print("---------------------------------------------")
            for transaction in transactions:
                print(f"{transaction[0]} | {transaction[1]} | {transaction[2]} | {transaction[3]}")
        else:
            print("No transactions found for this user.")
    except mysql.connector.Error as err:
        print("Error retrieving transactions:", err)

# Function to edit a transaction
def edit_transaction(connection, transaction_id, amount, description, category):
    try:
        cursor = connection.cursor()
        cursor.execute("""
        UPDATE transactions
        SET amount = %s, description = %s, category = %s
        WHERE transaction_id = %s""", (amount, description, category, transaction_id))
        connection.commit()
        print("Transaction updated successfully.")
    except mysql.connector.Error as e:
        print("Error updating transaction:", e)
    cursor.close()



# Function to delete a transaction
def delete_transaction(connection, transaction_id):
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM transactions WHERE transaction_id = %s", (transaction_id,))
        connection.commit()
        print("Transaction deleted successfully.")
    except mysql.connector.Error as e:
        print("Error deleting transaction:", e)
    finally:
        cursor.close()

#Function to display a pop-up alert
def show_alert(title, message):
    # Create a new root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window (we don't need it)
    
    # Set the root window to always appear on top
    root.attributes('-topmost', True)
    
    # Show the message box with the title and message
    messagebox.showinfo(title, message)  # This will block until the user closes the alert
    
    # After closing the message box, clean up and continue the program
    root.quit()
    root.destroy()

#check budget progress    
def check_budget_progress(connection, username):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT budget FROM users WHERE username = %s", (username,))
        budget = cursor.fetchone()
        
        if budget:
            # Sum only transactions where the category is 'expense'
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE username = %s AND category = 'expense'", (username,))
            total_spent = cursor.fetchone()[0] or 0

            # Calculate remaining budget
            remaining_budget = budget[0] - total_spent

            # Print budget progress
            print(f"Budget: {budget[0]}, Total Spent: {total_spent}")
            
            # Check if budget is exceeded and show alert
            if remaining_budget < 0:
                show_alert("Budget Exceeded", f"You have exceeded your budget by {abs(remaining_budget)}!")
            else:
                print(f"Remaining Budget: {remaining_budget}")
        else:
            print("No budget found for the user.")
    except mysql.connector.Error as e:
        print("Error checking budget progress:", e)
    finally:
        cursor.close()

# Main function to run the program
def main():
    connection = connect_to_db()
    if connection is None:
        return
    
    create_database_if_not_exists(connection)
    create_tables_if_not_exists(connection)

    logged_in_user = None
    while True:
        if logged_in_user is None:
            print("\n---Welcome to PennyPilot---")
            print("For all your finance management needs :-)")
            print("Please select an option to continue")
            print("1. Create User")
            print("2. Login")
            print("3. Exit")  # Option to exit the program
            choice = input("Enter your choice: ")

            if choice == '1':
                username = input("Enter username: ")
                password = input("Enter password: ")
                create_user(connection, username, password)

            elif choice == '2':
                username = input("Enter username: ")
                password = input("Enter password: ")
                if check_user(connection, username, password):
                    print(f"Login successful, welcome {username}!")
                    logged_in_user = username
                else:
                    print("Invalid username or password.")
            
            elif choice == '3':  # Exit option
                print("Exiting the program...")
                break  # Exit the main loop and close the program

            else:
                print("Invalid choice. Please try again.")

        else:
            print("\nWelcome back, " + logged_in_user + "!")
            print("1. Set Budget")
            print("2. Add Transaction")
            print("3. View Transactions")
            print("4. View Budget Progress")
            print("5. Edit Transaction")
            print("6. Delete Transaction")
            print("7. Log out")
            print("8. Exit")  # Option to exit the program while logged in
            choice = input("Enter your choice: ")

            if choice == '1':  # Set Budget
                budget_amount = float(input("Enter your budget: "))
                set_budget(connection, logged_in_user, budget_amount)

            elif choice == '2':  # Add Transaction
                amount = float(input("Enter transaction amount: "))
                description = input("Enter transaction description: ")
                category = input("Enter transaction category (income/expense): ")
                add_transaction(connection, logged_in_user, amount, description, category)
                
            elif choice == '3':  # View Transactions
                display_transactions(connection, logged_in_user)

            elif choice == '4':  # View Budget Progress
                check_budget_progress(connection, logged_in_user)

            elif choice == '5':  # Edit Transaction
                display_transactions(connection, logged_in_user)  # Show all transactions with IDs
                transaction_id = int(input("Enter the transaction ID you want to edit: "))
                amount = float(input("Enter new transaction amount: "))
                description = input("Enter new transaction description: ")
                category = input("Enter new transaction category (income/expense): ")
                edit_transaction(connection, transaction_id, amount, description, category)

            elif choice == '6':  # Delete Transaction
                display_transactions(connection, logged_in_user)  # Show all transactions with IDs
                transaction_id = int(input("Enter the transaction ID you want to delete: "))
                delete_transaction(connection, transaction_id)

            elif choice == '7':  # Log out
                print(f"Goodbye, {logged_in_user}!")
                logged_in_user = None  # Set to None to go back to the main menu

            elif choice == '8':  # Exit the program
                print("Exiting the program...")
                break  # Exit the program

            else:
                print("Invalid choice. Please try again.")


# Run the program
main()

