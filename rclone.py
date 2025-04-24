import datetime
import shutil
import subprocess
from logFunctions import log_message

# Funkcja do sprawdzania, czy folder z dzisiejszą datą już istnieje na SP
def check_if_folder_exists(sp_path):
    paths_date = datetime.datetime.now().strftime("%Y%m%d")
    try:
        resultLs = subprocess.run(['rclone', 'lsd', f'{sp_path}' + paths_date], check=True, capture_output=True, text=True)
        log_message(f'Folder z dzisiejszą datą już istnieje na SP.')
        return True
    except subprocess.CalledProcessError:
        log_message(f'Folder z dzisiejszą datą nie istnieje na SP.')
        return False

# Funkcja do przesyłania plików na SP
def upload_to_SP(base_path, sp_path):
    paths_date = datetime.datetime.now().strftime("%Y%m%d")
    try:
        resultMkdir = subprocess.run(['rclone', 'mkdir', f'{sp_path}' + paths_date], check=True, capture_output=True, text=True)
        log_message(f'Folder został utworzony na SP.')
        try:
            # Uruchom rclone copy
            resultCopy = subprocess.run(['rclone', 'copy', base_path, f'{sp_path}' + paths_date, '--ignore-size', '--ignore-checksum', '--progress'], check=True, capture_output=True, text=True)
            log_message('Folder został przesłany na SP.')
        except subprocess.CalledProcessError as e:
            log_message(f"Błąd podczas przesyłania folderu: {e}")
            log_message(f"Wyjście standardowe: {e.stdout}")  # Wydrukuj standardowe wyjście
            log_message(f"Wyjście błędów: {e.stderr}")  # Wydrukuj wyjście błędów
    except subprocess.CalledProcessError as e:
        log_message(f"Bład podczas tworzenia folderu na SP: {e}")
        log_message(f"Wyjcie standardowe: {e.stdout}")  # Wydrukuj standardowe wyjście
        log_message(f"Wyjcie błeów: {e.stderr}")  # Wydrukuj wyjście błędów


# Funkcja zmiany folderu na archiwum zip
def replace_folder_to_zip(folder):
    shutil.make_archive(f'{folder}', 'zip', folder)
    shutil.rmtree(folder)
    log_message(f"Folder z raportami został zastąpiony archiwum zip")