import os
from datetime import datetime, timedelta
import logging

def setup_logging():
    # Uzyskanie dzisiejszej daty w formacie yyyyMMdd
    today_date = datetime.now().strftime("%Y%m%d")
    log_file_path = f"./files/logs/{today_date}.log"

    # Sprawdzanie, czy plik istnieje
    if not os.path.exists(log_file_path):
        # Jeśli plik nie istnieje, tworzenie nowego pliku
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'w') as file:
            pass  # Tworzenie pustego pliku

    # Ustawianie loggera
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Tworzenie formatowania logów
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Handler do zapisywania logów do pliku
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler do logowania na standardowe wyjście (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def log_message(message):
    logging.info(message)

# def setup_logging():
#     # Uzyskanie dzisiejszej daty w formacie yyyyMMdd
#     today_date = datetime.now().strftime("%Y%m%d")
#     log_file_path = f"./files/logs/{today_date}.log"
    
#     # Sprawdzanie, czy plik istnieje
#     if not os.path.exists(log_file_path):
#         # Jeśli plik nie istnieje, tworzenie nowego pliku
#         os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
#         with open(log_file_path, 'w') as file:
#             pass # Tworzenie pustego pliku
    
#     # Ustawianie zapisywania logów w tym pliku
#     import logging
#     logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(message)s', encoding='utf-8', datefmt='%Y-%m-%d %H:%M:%S')


# def log_message(message):
#     logging.info(message)
#     print(">> " + message)

def silent_log_message(message):
    logging.info(message)

def remove_old_logs():
    log_message(f"Usuwam pliki starsze niż 30 dni")
    logs_dir = "./files/logs"
    # Definiowanie progu czasu dla plików starszych niż 30 dni
    threshold_date = datetime.now() - timedelta(days=30)
    threshold_time = threshold_date.timestamp()
    
    # Przechodzenie przez pliki w katalogu
    for filename in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, filename)
        
        if os.path.isfile(file_path):
            # Sprawdzanie czasu utworzenia pliku
            file_create_time = os.path.getctime(file_path)
            
            if file_create_time < threshold_time:
                # Usuwanie plików starszych niż 30 dni
                os.remove(file_path)
                log_message(f"Usunięto: {file_path}")


def get_flag(env_var, default):
    value = os.getenv(env_var, default)
    value = value.lower()
    
    if value in ['true', '1', 't']:
        return True
    elif value in ['false', '0', 'f']:
        return False
    else:
        return default

