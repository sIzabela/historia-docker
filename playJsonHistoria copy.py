from playwright.sync_api import sync_playwright
import datetime, time, pandas as pd, json, re
from logFunctions import log_message

def send_query_json(page, numer_rejestracyjny, numer_vin, data_pierwszej_rejestracji):
    # for attempt in range(3):
        try:                
            # Przejście na stronę główną
            page.goto("https://moj.gov.pl/nforms/engine/ng/index?xFormsAppName=HistoriaPojazdu#/search", wait_until="commit")

            # Wypełnienie pól formularza (dostosuj selektory do aktualnej struktury strony)
            page.fill("input[id='registrationNumber']", numer_rejestracyjny)
            page.fill("input[id='VINNumber']", numer_vin)
            page.fill("input[id='firstRegistrationDate']", data_pierwszej_rejestracji)
            
            # Kliknięcie przycisku wysyłającego formularz
            page.click('button.nforms-button:has-text("Sprawdź pojazd")')
            
            # Czekamy na odpowiedź z API – filtrujemy po URL, który zawiera fragment "HistoriaPojazdu/x.x.xx/data/vehicle-data"
            response = page.wait_for_event("response", lambda r: re.search(r"HistoriaPojazdu/\d+\.\d+\.\d+/data/vehicle-data", r.url))
            vehicle_json = None
            timeline_json = None

            try:
                vehicle_json = response.json()
                log_message(f"> {numer_rejestracyjny} - Otrzymano dane.")
            except Exception as e:
                log_message(f"> {numer_rejestracyjny} - Błąd przy parsowaniu JSON: {e}")


            if vehicle_json and vehicle_json.get("VALIDATION_ERROR_MSG") != "W bazie danych nie istnieje pojazd o podanych parametrach":
                # Kliknij w zakładkę "Oś czasu"
                page.click('div[role="tab"]:has-text("Oś czasu")')

                timeline_response = page.wait_for_event("response", lambda response: re.search(r"HistoriaPojazdu/\d+\.\d+\.\d+/data/timeline-data", response.url), timeout=10000)
                
                try:
                    timeline_json = timeline_response.json()
                    log_message(f"> {numer_rejestracyjny} - Otrzymano dane JSON z timeline-data.")
                except Exception as e:
                    log_message(f"> {numer_rejestracyjny} - Błąd przy parsowaniu timeline JSON: {e}.")
                    return 1, 1
            
            else:
                log_message(f"> {numer_rejestracyjny} - W bazie danych nie istnieje pojazd o podanych parametrach.")

            return vehicle_json, timeline_json
        except Exception as e:
            log_message(f"> {numer_rejestracyjny} - Błąd podczas pobierania JSON: {e}.")
            if 'Timeout 30000.0ms exceeded while waiting for event "response"' in str(e):
                return 1, 1
            else:
                return 2, 2
            # if attempt < 2:
            #     log_message(f"> {numer_rejestracyjny} - Błąd podczas pobierania JSON: {e}.\nPróba {attempt} z 2.\nPonowna próba za 2 sekundy.")
            #     time.sleep(2)
            # else:
            #     log_message(f"> {numer_rejestracyjny} - Błąd podczas pobierania JSON: {e}.\nWyrzucam błąd.")
            #     exit(1)



def json_to_list(vehicle_json, timeline_json, new_row):
    data_vehicle = vehicle_json
    new_row['gov_MARKA'] =  data_vehicle["technicalData"]["basicData"]["make"]
    if new_row['gov_MARKA'] == None: new_row['gov_MARKA'] = 'brak danych'

    new_row['gov_MODEL'] = data_vehicle["technicalData"]["basicData"]["model"]
    if new_row['gov_MODEL'] == None: new_row['gov_MODEL'] = 'brak danych'

    new_row['gov_POJEMNOSC'] = data_vehicle["technicalData"]["detailedData"]["engineCapacity"]
    if new_row['gov_POJEMNOSC'] == None: new_row['gov_POJEMNOSC'] = 'brak danych'

    new_row['gov_MOC'] = data_vehicle["technicalData"]["detailedData"]["maxNetEnginePower"]
    if new_row['gov_MOC'] == None: new_row['gov_MOC'] = 'brak danych'

    data_timeline = timeline_json
    events = data_timeline["timelineData"]["events"]

    if not events or len(events) == 0:
        
        log_message(f"> {new_row['NR_REJESTRACYJNY']} - brak danych na osi czasu.")
    else:
        # Przebieg różnica
        przebieg_1 = None
        przebieg_2 = None
        data_przebieg_1 = None
        data_przebieg_2 = None
        inna_jednostka_przebiegu = None

        okresowe_badania = [event for event in events if event["eventType"] == "badanie-techniczne-okresowe"]
        okresowe_badania.sort(key=lambda x: x["eventDate"], reverse=True)

        if len(okresowe_badania) > 1:
            for badanie in okresowe_badania[:2]:
                for detail in badanie["eventDetails"]:
                    if detail["name"] == "Odczytany stan drogomierza":
                        value = detail["value"]
                        if przebieg_1 is None:
                            przebieg_1 = value
                            data_przebieg_1 = datetime.datetime.strptime(badanie["eventDate"], '%Y-%m-%d').strftime('%d.%m.%Y')
                        elif przebieg_2 is None:
                            przebieg_2 = value
                            data_przebieg_2 = datetime.datetime.strptime(badanie["eventDate"], '%Y-%m-%d').strftime('%d.%m.%Y')
                        if "km" not in value and "mi" not in value:
                            inna_jednostka_przebiegu = f"Inna jednostka: {value}"
            
            if przebieg_1:
                przebieg_1 = przebieg_1.rsplit(' ', 1)[0]
            if przebieg_2:
                przebieg_2 = przebieg_2.rsplit(' ', 1)[0]

            if inna_jednostka_przebiegu:
                new_row['gov_PROGNOZOWANY_PRZEBIEG'] = inna_jednostka_przebiegu
            else:
                if przebieg_1 and przebieg_2:
                    test = 1
        else:
            new_row['gov_PROGNOZOWANY_PRZEBIEG'] = 'brak danych'

        # Badania dodatkowe
        badanie_dodatkowe_value = None
        badanie_dodatkowe_date = None

        dodatkowe_badania = [event for event in events if event["eventType"] == "badanie-techniczne-dodatkowe"]
        for badanie in dodatkowe_badania:
            badanie_dodatkowe_date = datetime.datetime.strptime(badanie["eventDate"], '%Y-%m-%d').strftime('%d.%m.%Y')
            for detail in badanie["eventDetails"]:
                if detail["name"] == "Rodzaj badania":
                    badanie_dodatkowe_value = detail["value"]
        new_row['gov_WYKORZYSTANIE_POJAZDU'] = 'PRYWATNIE (W TYM DOJAZD DO PRACY)'
        if badanie_dodatkowe_value and ('DICT124_5.1' in badanie_dodatkowe_value.upper() or 'DICT124_3.1' in badanie_dodatkowe_value.upper()):
            if 'DICT124_5.1' in badanie_dodatkowe_value.upper():
                new_row['gov_WYKORZYSTANIE_POJAZDU'] = 'NAUKA JAZDY (' + badanie_dodatkowe_date + ')'
            elif 'DICT124_3.1' in badanie_dodatkowe_value.upper():
                new_row['gov_WYKORZYSTANIE_POJAZDU'] = 'TAXI (' + badanie_dodatkowe_date + ')'

        # Pochodzenie - daty
        pierwsza_rejestracja_za_granica = None
        pierwsza_rejestracja_w_polsce = None

        for event in events:
            if "Pierwsza rejestracja za granicą" in event["eventName"]:
                pierwsza_rejestracja_za_granica = datetime.datetime.strptime(event["eventDate"], '%Y-%m-%d').strftime('%d.%m.%Y')
            elif "Pierwsza rejestracja w Polsce"in event["eventName"]:
                pierwsza_rejestracja_w_polsce = datetime.datetime.strptime(event["eventDate"], '%Y-%m-%d').strftime('%d.%m.%Y')

        # sprowadzenie = (datetime.datetime.strptime(new_row['DATA_ZAWARCIA'], '%Y-%m-%d') - datetime.datetime.strptime(pierwsza_rejestracja_w_polsce, '%d.%m.%Y')).days
        sprowadzenie = (pd.to_datetime(new_row['DATA_ZAWARCIA']) - pd.to_datetime(pierwsza_rejestracja_w_polsce, dayfirst=True)).days
        
        # Czy było badanie techniczne
        if data_przebieg_1:
            dni_od_badania = abs((pd.to_datetime(new_row['POCZATEK_OCHRONY']) - datetime.datetime.strptime(data_przebieg_1, '%d.%m.%Y')).days)
            if(dni_od_badania <= 365):
                        new_row['gov_BADANIE_TECHNICZNE'] = "TAK"

            elif data_przebieg_2:
                dni_od_badania2 = abs((pd.to_datetime(new_row['POCZATEK_OCHRONY']) - datetime.datetime.strptime(data_przebieg_2, '%d.%m.%Y')).days)

                if(dni_od_badania2 <= 365):
                    new_row['gov_BADANIE_TECHNICZNE'] = "TAK"
                else:
                    new_row['gov_BADANIE_TECHNICZNE'] = "NIE"

            else:
                new_row['gov_BADANIE_TECHNICZNE'] = "brak danych"   
        else:
            new_row['gov_BADANIE_TECHNICZNE'] = 'brak danych'

        # Zmiany właściciela
        zmiana_wlasciciela_count = 1

        for event in events:
            date = datetime.datetime.strptime(event["eventDate"], '%Y-%m-%d')
            if "zmiana-wlasciciela" in event["eventType"] and date > pd.to_datetime(new_row['DATA_ZAWARCIA']):
                zmiana_wlasciciela_count += 1

            new_row['gov_ZMIANY_WLASCICIELA'] = str(zmiana_wlasciciela_count)

        # Współwlasciciele
        wspolwlasciciele = data_timeline["timelineData"]["currentCoOwners"]
        new_row['gov_WSPOLWLASCICIEL'] = str(wspolwlasciciele)

    return new_row



def checks_vehicle(new_row):
    new_row['info_MARKA'] = 'ZGODNE'
    new_row['info_MODEL'] = 'ZGODNE'
    new_row['info_POJEMNOSC'] = 'ZGODNE'
    new_row['info_MOC'] = 'ZGODNE'
    new_row['info_PROGNOZOWANY_PRZEBIEG'] = 'ZGODNE'
    new_row['info_POCHODZENIE_POJAZDU'] = 'ZGODNE'
    new_row['info_ZMIANY_WLASCICIELA'] = 'ZGODNE'
    new_row['info_WYKORZYSTANIE_POJAZDU'] = 'ZGODNE'
    new_row['info_BADANIE_TECHNICZNE'] = 'ZGODNE'
    new_row['info_WSPOLWLASCICIEL'] = ''
    new_row['PODSUMOWANIE'] = 'OK'
    flag_weryfikacja = False


    if(new_row['MARKA'].upper() != new_row['gov_MARKA'].upper()):
        new_row['info_MARKA'] = 'BRAK ZGODNOŚCI'
        flag_weryfikacja = True


    if(new_row['MODEL'].upper() != new_row['gov_MODEL'].upper()):
        new_row['info_MODEL'] = 'INNE'


    if(new_row['POJEMNOSC'] != new_row['gov_POJEMNOSC']):
        if(new_row['gov_POJEMNOSC'] == 'brak danych'):
            new_row['info_POJEMNOSC'] = 'INNE'
        else:
            roznica = abs(int(new_row['POJEMNOSC']) - int(new_row['gov_POJEMNOSC']))
            if(roznica > 29):
                new_row['info_POJEMNOSC'] = 'BRAK ZGODNOŚCI'
                flag_weryfikacja = True

    if(new_row['MOC'] != new_row['gov_MOC']):
        if('brak danych' in str(new_row['MOC']) or 'brak danych' in str(new_row['gov_MOC'])):
            new_row['info_MOC'] = 'INNE'
        else:
            roznica = abs(int(new_row['MOC']) - int(new_row['gov_MOC']))
            if(roznica > 19):
                new_row['info_MOC'] = 'BRAK ZGODNOŚCI'
                flag_weryfikacja = True


    #CHECK info PROGNOZOWANY_PRZEBIEG
    



    if(new_row['POCHODZENIE_POJAZDU'] not in new_row['gov_POCHODZENIE_POJAZDU']):
        if ('SPROWADZONY Z ZAGRANICY W OSTATNIM ROKU' in new_row['gov_POCHODZENIE_POJAZDU']): #WERYFIKUJ row czy gov?
            new_row['info_POCHODZENIE_POJAZDU'] = 'BRAK ZGODNOŚCI'
            flag_weryfikacja = True
        else:
            new_row['info_POCHODZENIE_POJAZDU'] = 'INNE'


    if(str(new_row['ZMIANY_WLASCICIELA']) != str(new_row['gov_ZMIANY_WLASCICIELA'])):
        new_row['info_ZMIANY_WLASCICIELA'] = 'BRAK ZGODNOŚCI'
        flag_weryfikacja = True


    if(new_row['WYKORZYSTANIE_POJAZDU'] not in new_row['gov_WYKORZYSTANIE_POJAZDU']):
        new_row['info_WYKORZYSTANIE_POJAZDU'] = 'BRAK ZGODNOŚCI'
        flag_weryfikacja = True


    if('Wznowienie automatyczne' in new_row['RODZAJ_UMOWY']):
        new_row['info_BADANIE_TECHNICZNE'] = 'INNE'
    elif(new_row['BADANIE_TECHNICZNE'] != new_row['gov_BADANIE_TECHNICZNE']):
        if 'TAK' in new_row['gov_BADANIE_TECHNICZNE']:
            new_row['info_BADANIE_TECHNICZNE'] = "ZGODNE"
        else:
            new_row['info_BADANIE_TECHNICZNE'] = 'BRAK ZGODNOŚCI'
            flag_weryfikacja = True
    

    if(flag_weryfikacja == True):
        new_row['PODSUMOWANIE'] = 'WERYFIKACJA'

    return new_row, flag_weryfikacja
