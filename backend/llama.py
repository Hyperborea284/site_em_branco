import os
from sqlalchemy import create_engine
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

def select_database():
    # List available databases
    databases_folder = os.path.join(os.path.dirname(__file__), 'databases')
    available_databases = [f for f in os.listdir(databases_folder) if os.path.isfile(os.path.join(databases_folder, f))]

    # Check if there are any databases available
    if not available_databases:
        print("No databases found in the 'databases' folder.")
        exit()

    # Display available databases for selection
    print("Available databases for analysis:")
    for i, db in enumerate(available_databases):
        print(f"{i + 1}. {db}")

    # Prompt user to choose a database for analysis
    while True:
        try:
            selected_db_index = int(input("\nPlease enter the number corresponding to the database you want to analyze: "))
            if 1 <= selected_db_index <= len(available_databases):
                selected_db = available_databases[selected_db_index - 1]
                break
            else:
                print("Invalid selection. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Construct database URI
    db_path = os.path.join(databases_folder, selected_db)
    db_uri = f'sqlite:///{db_path}'
    
    return db_uri

def process_user_query(user_query, query_engine):
    # Execution of the query using NLSQLTableQueryEngine
    response = query_engine.query(user_query)
    return response

# Clear the terminal screen
os.system('cls' if os.name == 'nt' else 'clear')

while True:
    db_uri = select_database()

    # Connection to the selected database
    engine = create_engine(db_uri)

    # Configuration of the SQLDatabase
    sql_database = SQLDatabase(engine, include_tables=["links"])

    # Initialization of the NLSQLTableQueryEngine
    query_engine = NLSQLTableQueryEngine(sql_database, tables=["links"])

    # Instruction for inserting the question
    print("Please insert your question about the database below (Type 'exit' to quit):\n")

    # Receiving the user question via prompt
    user_query = input()

    if user_query.lower() == 'exit':
        print("Exiting the program...")
        break

    # Processing the query and getting the response
    response = process_user_query(user_query, query_engine)

    # Handling the response
    print(response)
