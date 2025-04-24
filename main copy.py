# Biblioteki do pobrania i przetwarzania danych z serwera historiapojazdu.gov.pl
from playJsonHistoria import *

#Biblioteki do obsługi plików  i mail
from getRaport import *
from logFunctions import *
from excelFunctions import *
import pandas as pd
import os
from shutil import copytree
from rclone import *
from ITmails import *
from sql_insert import *
import traceback

#Biblioteki do obsługi czasu
import datetime
import time

with open('config.json') as f:
    config = json.load(f)

paths_date = datetime.datetime.now().strftime("%Y%m%d")
data_raportu = datetime.date.today().strftime('%Y-%m-%d')
SP_PATH = config['paths']['sp_path']

BASE_PATH = config['paths']['base_path'].format(paths_date=paths_date)
START_FILE = config['paths']['start_file'].format(BASE_PATH=BASE_PATH, paths_date=paths_date)
FILE = config['paths']['baza_file'].format(BASE_PATH=BASE_PATH, paths_date=paths_date)
KONCOWY_FILE = config['paths']['koncowy_file'].format(paths_date=paths_date)

files_path = "/app/files"
koncowy_path = f"{BASE_PATH}/{KONCOWY_FILE}"
folder = f'{BASE_PATH}/daneJSON'

# Sprawdzenie i tworzenie folderu z datą
os.makedirs(BASE_PATH, exist_ok=True)

temp_wynik_plik = f'{BASE_PATH}//temp_Wynik.xlsx'
temp_koncowy_plik = f'{BASE_PATH}//temp_Koncowy.xlsx'

proby_pobrania = 3
odczekanie = 1.5 # w sekundach np. 1.5 to 1.5 sekundy

# ================================================== DEBUG ==================================================
DEBUG = config['debug'].lower() == 'true'  # tryb DEBUG
SQL_INSERTION = config['sql_insertion'].lower() == 'true'  # czy wstawiać do SQL

setup_logging()
log_message("Rozpoczynam prace tryb DEBUG: " + str(DEBUG))
log_message("Plik wejsciowy: " + START_FILE)
log_message("Plik wynikowy: " + FILE)
log_message("Plik koncowy: " + KONCOWY_FILE)

if not DEBUG:
    if check_if_folder_exists(SP_PATH):
        log_message('Kończę działanie')
        exit(0)

# Sprawdzenie i tworzenie folderu pod raporty
folder = folder + '_' + paths_date
if not os.path.exists(folder):
    os.makedirs(folder)
    log_message('Utworzono folder na raporty gov: ' + folder)
else:
    log_message('Zapis raportów gov do istniejącego folderu: ' + folder)

get_today_raport_with_headers(START_FILE)

try:
    df = pd.read_excel(START_FILE, sheet_name='Sheet1')
except Exception as e:
    log_message('Błąd odczytu pliku wejściowego: ' + START_FILE + ' - ' + str(e))
    exit(1)


if DEBUG:
    log_message(df.describe()) #DEBUG
    log_message("\n========================================\n") #DEBUG
    log_message(df.head(3)) #DEBUG
    log_message("========================================") #DEBUG


log_message('Ilość rekordow do przeprocesowania: ' + str(len(df)))

list_result = []
list_koncowy = []

df_result = pd.DataFrame(columns=df.columns)
df_koncowy = pd.DataFrame(columns=df.columns)

#Sprawdzenie ilosci rekordow w plikach
wejscie_count = verify_excel_count_rows(START_FILE) 
wynik_count = verify_excel_count_rows(temp_wynik_plik)

start_time = time.time()

if DEBUG:
    wynik_count = 0
    wejscie_count = 10


with sync_playwright() as p:
    log_message("Otwieram przeglądarkę")
    # Uruchomienie przeglądarki Chromium w trybie headless
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Iteracja po wszystkich pojazdach w xlsx
    for i in range(wynik_count, wejscie_count):
        # time.sleep(2)
        try:
            # Zrzucenie rekordu do zmiennej row
            row = df.iloc[i]

            # Zrzucenie potrzebnych danych z row do zmiennych
            sygnatura = str(row['SYGNATURA'])

            while(len(sygnatura) < 10):
                sygnatura = '0' + sygnatura
            
            numer_rejestracyjny = row['NR_REJESTRACYJNY']
            numer_vin = row['VIN']

            data_pierwszej_rejestracji = pd.to_datetime(row['DATA_PIERWSZEJ_REJESTRACJI']).strftime('%d.%m.%Y')
            data_pierwszej_rejestracji_excel = pd.to_datetime(row['DATA_PIERWSZEJ_REJESTRACJI']).strftime('%Y-%m-%d')
            data_zawarcia = pd.to_datetime(row['DATA_ZAWARCIA']).strftime('%Y-%m-%d')

            # print(data_pierwszej_rejestracji) #DEBUG
            for attempt in range(6):
                vehicle_json, timeline_json= send_query_json(page, numer_rejestracyjny, numer_vin, data_pierwszej_rejestracji)
                if vehicle_json == 1:
                    log_message('Ponawiam próbę')
                    continue
                if vehicle_json == 2:
                    # log_message('Restartuję przeglądarkę')
                    # browser.close()
                    # # time.sleep(10)
                    # # Uruchomienie przeglądarki Chromium w trybie headless
                    # browser = p.chromium.launch(headless=True)
                    # page = browser.new_page()

                    # Czyszczę cache i cookies
                    log_message('Czyszczę cache i cookies przeglądarki')
                    page.context.clear_cookies()
                    continue
                else:
                    break

            # Zapisywanie json_response
            if vehicle_json:
                filename = f"{folder}//JSON_{numer_rejestracyjny}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(vehicle_json, f, ensure_ascii=False, indent=4)
            
            if timeline_json:
                filename = f"{folder}//JSON_{numer_rejestracyjny}_timeline.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(timeline_json, f, ensure_ascii=False, indent=4)

            try:
                if (vehicle_json and vehicle_json.get("VALIDATION_ERROR_MSG") != "W bazie danych nie istnieje pojazd o podanych parametrach") and (timeline_json and timeline_json.get("VALIDATION_ERROR_MSG") != "Nie udało się ustalić szczegółów błędu"):
                    new_row = {
                        
                    }

                    new_row = json_to_list(vehicle_json, timeline_json, new_row)

                    #==========CHECKS==========

                    new_row, flag_weryfikacja = checks_vehicle(new_row)
                    
                    #=====PRINT=====
                    log_message(f"{i}: {sygnatura} - {new_row['gov_MARKA']}, {new_row['gov_MODEL']}, {new_row['PODSUMOWANIE']}")
                    
                    # time.sleep(0.4) #DEBUG
                    # new_df_row = pd.DataFrame([new_row])

                    #Zapisz do xlsx
                    # df_result = pd.concat([df_result, new_df_row], ignore_index=True)
                    list_result.append(new_row)
                    if(flag_weryfikacja == True):
                        # df_koncowy = pd.concat([df_koncowy, new_df_row], ignore_index=True)
                        list_koncowy.append(new_row)

                else:
                    log_message(f"{i}: {numer_rejestracyjny}, Sygnatura: {sygnatura} - weryfikacja!!!")

                    if timeline_json:
                        uwagi = '"Nie można połączyć się z Centralną Ewidencją Pojazdów. Spróbuj ponownie później."'
                    else:
                        uwagi = '"Niestety, w Centralnej Ewidencji Pojazdów nie ma pojazdu o podanych danych."'

                    new_row = {
                        
                    }

                    list_result.append(new_row)
                    # if(flag_weryfikacja == True):
                    list_koncowy.append(new_row)

            except AttributeError as e:
                if "int object has no attribute 'get'" in str(e):
                    log_message(f"Błąd przy parsowaniu JSON: {e}\nPowtarzam pętle dla tego rekordu")
                    i -= 1
                    continue
            except Exception as e:
                log_message(f"Przekazanie błędu.")
                raise e

        except Exception as e:
            log_message(f'INDEX {i} - BŁĄD: {e}')
            log_message(traceback.format_exc())
            
            df_temp = pd.DataFrame(list_result)
            df_temp_koncowy = pd.DataFrame(list_koncowy)
            log_message("Zamykam przeglądarkę")
            browser.close()
            log_message("Zapisywanie dotychczasowej pracy do plików tymczasowych...")
            write_to_temp_excel(temp_wynik_plik, df_temp)
            write_to_temp_excel(temp_koncowy_plik, df_temp_koncowy)
            if not DEBUG:
                send_error_email(f'INDEX {i} - BŁĄD: {e}')
            exit(1)
    log_message("Zamykam przeglądarkę")
    browser.close()

df_result = pd.DataFrame(list_result)
df_koncowy = pd.DataFrame(list_koncowy)

if os.path.exists(temp_wynik_plik):
    df_temp = pd.read_excel(temp_wynik_plik, sheet_name='Sheet1')
    df_temp_koncowy = pd.read_excel(temp_koncowy_plik, sheet_name='Sheet1')
    df_temp['SYGNATURA'] = df_temp['SYGNATURA'].astype(str).str.zfill(10)
    df_temp_koncowy['SYGNATURA'] = df_temp_koncowy['SYGNATURA'].astype(str).str.zfill(10)

    df_result = pd.concat([df_temp, df_result], ignore_index=True)
    df_koncowy = pd.concat([df_temp_koncowy, df_koncowy], ignore_index=True)
    os.remove(temp_wynik_plik)
    os.remove(temp_koncowy_plik)


log_message('Zapisywanie wyników do plików excel')
df_result.to_excel(FILE, index=False)
df_koncowy.to_excel(koncowy_path, index=False)

if DEBUG:
    send_end_debug(koncowy_path, KONCOWY_FILE, str(len(df_result)))
else:
    if SQL_INSERTION:
        log_message('Dodawanie rekordów do tabeli')
        insert_df_to_mssql(df_result)

    replace_folder_to_zip(folder)

    log_message('Rozpoczynam kopiowanie plików do folderu na SP')
    upload_to_SP(BASE_PATH, SP_PATH)

    log_message('Rozpoczynanie wysyłki maili')
    send_end_email(koncowy_path, KONCOWY_FILE, str(len(df_result)), paths_date)

log_message('Czas wykonania: ' + str(round(time.time() - start_time, 2)))