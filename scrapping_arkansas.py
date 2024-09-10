from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import time
import csv
import gspread
import signal
import sys
import os


load_dotenv()


options = webdriver.ChromeOptions()
options.add_argument("--disable-popup-blocking")
options.add_argument("--headless")  
options.add_argument("--blink-settings=imagesEnabled=false")
driver = webdriver.Chrome(options=options)


dados_coletados = []

driver.get("https://auction.cosl.org/Auctions/ListingsView")

def autenticar_google_sheets():
    
    credentials_info = {
        "type": os.getenv("GOOGLE_TYPE"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n"),  
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_CERT_URL"),
        "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_CERT_URL"),
        "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN")
    }

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              "https://www.googleapis.com/auth/drive"]

    credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    cliente = gspread.authorize(credentials)
    return cliente

def clicar_no_elemento_com_javascript(elemento):
    driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", elemento)

def salvar_em_google_sheets(data, nome_planilha, nome_aba):
    try:
        cliente = autenticar_google_sheets()  
        
        planilha = cliente.open(nome_planilha)
        
        try:
            aba = planilha.worksheet(nome_aba)
        except gspread.exceptions.WorksheetNotFound:
            aba = planilha.add_worksheet(title=nome_aba, rows="100", cols="20")
        
        if data:
            headers = list(data[0].keys())  
            valores = [list(item.values()) for item in data]  

            aba.clear()  
            aba.append_row(headers) 
            aba.append_rows(valores)  
            
            print(f"Dados enviados para a aba '{nome_aba}' na planilha '{nome_planilha}' com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar dados no Google Sheets: {e}")


def processar_listagens():
    try:
        while True: 
            try:
                bid_buttons = WebDriverWait(driver, 40).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1"))
                )

                bid_buttons = [btn for btn in bid_buttons if btn.is_displayed() and btn.is_enabled()]

            except TimeoutException:
                print("Não foi possível carregar os botões 'Bid'. Encerrando o processo.")
                break

            for index in range(len(bid_buttons)):
                try:
                    bid_buttons = driver.find_elements(By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1")
                    bid_buttons = [btn for btn in bid_buttons if btn.is_displayed() and btn.is_enabled()]
                    
                    if index >= len(bid_buttons):
                        print(f"Índice {index} fora do alcance após a recarga dos botões. Pulando para o próximo.")
                        continue

                    bid_button = bid_buttons[index]
                    
                    print(f"Processando o item {index + 1} de {len(bid_buttons)}")
                    
                    clicar_no_elemento_com_javascript(bid_button)  
                    time.sleep(3) 

                    try:
                        view_button = WebDriverWait(driver, 25).until(
                            EC.presence_of_element_located((By.XPATH, "//a[@title='View on DataScoutPro']"))
                        )

                        try:
                            view_button.click()
                            print("Botão 'View on DataScoutPro' clicado com Selenium.")
                        except (ElementClickInterceptedException, ElementNotInteractableException):
                            print("Falha ao clicar no botão com Selenium, tentando com JavaScript.")
                            clicar_no_elemento_com_javascript(view_button)  

                        time.sleep(3) 

                        driver.switch_to.window(driver.window_handles[-1])

                        try:
                            close_button = WebDriverWait(driver, 25).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Close')]"))
                            )
                            close_button.click()
                            print("Pop-up fechado com sucesso.")
                        except TimeoutException:
                            print("Botão 'Close' do pop-up não encontrado a tempo.")

                        coletar_detalhes()

                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                    except TimeoutException:
                        print("Botão 'View on DataScoutPro' não encontrado a tempo.")

                    driver.back()
                    WebDriverWait(driver, 25).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1"))
                    )

                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException) as e:
                    print(f"Erro ao processar item {index + 1}: {e}")
                    driver.back()
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1"))
                    )
                    continue

            try:
                next_button = driver.find_element(By.XPATH, "//a[contains(@class, 'Go to the next page')]")  
                if next_button.is_displayed() and next_button.is_enabled():
                    print("Indo para a próxima página de listagens...")
                    clicar_no_elemento_com_javascript(next_button)
                    time.sleep(3)
                else:
                    print("Fim das listagens.")
                    break
            except NoSuchElementException:
                print("Botão 'Next' não encontrado. Fim das listagens.")
                break  

    except Exception as e:
        print(f"Erro ao processar as listagens: {e}")

def coletar_detalhes():
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Encontrar as tabelas que contêm os dados necessários
        tables = soup.find_all('div', class_='table-responsive')
        
        if tables:
            for table in tables:
                rows = table.find_all('tr')
                dados_item = {}
                
                for row in rows:
                    cells = row.find_all('td')
                    
                    # Confere se existem exatamente duas colunas (chave e valor)
                    if len(cells) == 2:
                        chave = cells[0].get_text(strip=True).replace(':', '')
                        valor = cells[1].get_text(strip=True)
                        
                        # Se a chave ou o valor não forem válidos, pula para a próxima iteração
                        if not chave or not valor:
                            continue
                        
                        # Adiciona apenas se a chave não existir no dicionário
                        if chave not in dados_item:
                            dados_item[chave] = valor
                
                # Adiciona o item aos dados coletados apenas se for válido
                if dados_item:
                    dados_coletados.append(dados_item)
        else:
            print("Nenhuma tabela de detalhes encontrada na página.")
        
    except Exception as e:
        print(f"Erro ao coletar detalhes: {e}")


def interromper_script(signal, frame):
    print("\nInterrupção recebida! Salvando dados coletados...")
    salvar_em_google_sheets(dados_coletados, "Scrapping Test", "Arkansas")
    print("Dados salvos. Encerrando o script.")
    driver.quit()
    sys.exit(0)

signal.signal(signal.SIGINT, interromper_script)

processar_listagens()

salvar_em_google_sheets(dados_coletados, "Scrapping Test", "Arkansas")

driver.quit()
