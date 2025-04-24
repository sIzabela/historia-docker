from logFunctions import *
import pandas as pd
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect, MetaData, Table
import os, json

with open('config.json') as f:
    config = json.load(f)

def insert_df_to_mssql(df):
    # Utworzenie silnika bazy danych
    USER = os.getenv('SQL_USER')
    PASSWD = os.getenv('SQL_PASSWD')
    SERVER_NAME = os.getenv('SQL_SERVER')
    # DB_NAME = "UnextWorkspace"
    DB_NAME = os.getenv('SQL_DATABASE')
    # table_name = "IK_CEPIK_BAZA_ODPYTAŃ_WEFOX"
    TABLE_NAME = config['sql']['insert_table']

    log_message(DB_NAME + '.' + TABLE_NAME)
    connection_string = f"mssql://{USER}:{PASSWD}@{SERVER_NAME}/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=Yes"
    engine = create_engine(connection_string)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Wstawianie danych do tabeli
        df.to_sql(TABLE_NAME, con=engine, index=False, if_exists='append')

        session.commit()
        log_message(f"Dane zostały wstawione do tabeli {TABLE_NAME}")
    except Exception as e:
        session.rollback()
        log_message(f"Operacja nieudana: {e}")
    finally:
        session.close()


def insert_dataframe_to_sql(df):    
    # Pobieranie parametrów bazy danych ze zmiennych środowiskowych
    USER = os.getenv('SQL_USER')
    PASSWD = os.getenv('SQL_PASSWD')
    SERVER_NAME = os.getenv('SQL_SERVER')
    DB_NAME = os.getenv('SQL_DATABASE')
    
    connection_string = f'DRIVER={{SQL Server}};SERVER={SERVER_NAME};DATABASE={DB_NAME};UID={USER};PWD={PASSWD}'

    # Tworzenie połączenia z bazą danych
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    try:
        # Rozpoczęcie transakcji
        cursor.execute("BEGIN TRANSACTION")

        # Iteracja przez wiersze dataframe'a
        for index, row in df.iterrows():
            # Przygotowanie zapytania SQL
            sql = config['sql']['sql_insert']

            # Wartości do zapytania
            values = (
                
            )

            # Wykonanie zapytania
            cursor.execute(sql, values)

        # Zatwierdzenie transakcji
        cursor.execute("COMMIT")

    except Exception as e:
        # Wycofanie transakcji w przypadku błędu
        cursor.execute("ROLLBACK")
        log_message(f"Błąd: {e}")

    finally:
        # Zamknięcie połączenia
        conn.close()

def check_db_properties():
    USER = os.getenv('SQL_USER')
    PASSWD = os.getenv('SQL_PASSWD')
    SERVER_NAME = os.getenv('SQL_SERVER')
    DB_NAME = os.getenv('SQL_DATABASE')
    TABLE_NAME = config['sql']['insert_table']

    connection_string = f"mssql://{USER}:{PASSWD}@{SERVER_NAME}/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=Yes"

    engine = create_engine(connection_string)
    try:
        connection = engine.connect()
        inspector = inspect(engine)
        columns = inspector.get_columns(TABLE_NAME)
        log_message(f"Właściwości tabeli '{TABLE_NAME}':")
        for column in columns:
            log_message(f"Nazwa kolumny: {column['name']}, Typ: {column['type']}, Nullable: {column['nullable']}, Domyślna wartość: {column['default']}")
        connection.close()
    except Exception as e:
        log_message("Nie udało się połączyć do bazy danych MSSQL lub uzyskać właściwości tabeli:", e)