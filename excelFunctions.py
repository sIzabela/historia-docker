import pandas as pd
import openpyxl

# Funkcja do zapisywania wierszy do nowego pliku Excel
def append_to_excel(file_name, df):
    try:
        # Wczytanie istniejącego pliku Excel
        workbook = openpyxl.load_workbook(file_name)
        sheet = workbook.active

        # Zapisanie wierszy do arkusza
        for index, row in df.iterrows():
            sheet.append(row.tolist())

        # Zapisanie pliku Excel
        workbook.save(file_name)
    
    except PermissionError:
        print(f"{file_name} - Brak uprawnień do pliku lub plik jest otwarty przez inny program")
        exit(1)
    except:
        # Tworzenie nowego pliku Excel, jeśli nie istnieje
        df.to_excel(file_name, index=False)
    

def write_to_temp_excel(file_name, df):
    try:
        # Wczytanie istniejącego pliku Excel
        workbook = openpyxl.load_workbook(file_name)
        sheet = workbook.active

        # Zapisanie wierszy do arkusza
        for index, row in df.iterrows():
            sheet.append(row.tolist())

        # Zapisanie pliku Excel
        workbook.save(file_name)
    except:
        # Tworzenie nowego pliku Excel, jeśli nie istnieje
        df.to_excel(file_name, index=False)
        print(f"Zapisywanie do pliku tymczasowego: {file_name} - OK")


def verify_excel_count_rows(file_name):
    try:
        df = pd.read_excel(file_name)
        return len(df.index)
    except:
        return 0