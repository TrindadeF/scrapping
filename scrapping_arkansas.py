from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException
from bs4 import BeautifulSoup
import time
import csv
import signal
import sys

options = webdriver.ChromeOptions()
options.add_argument("--disable-popup-blocking")
options.add_argument("--headless")  
options.add_argument("--blink-settings=imagesEnabled=false")
driver = webdriver.Chrome(options=options)


dados_coletados = []

driver.get("https://auction.cosl.org/Auctions/ListingsView")

def clicar_no_elemento_com_javascript(elemento):
    driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", elemento)


def salvar_dados_em_csv(dados, nome_arquivo='dados_coletados.csv'):
    if not dados:
        print("Nenhum dado coletado para salvar.")
        return


    chaves = dados[0].keys()
    with open(nome_arquivo, 'w', newline='', encoding='utf-8') as arquivo_csv:
        escritor_csv = csv.DictWriter(arquivo_csv, fieldnames=chaves)
        escritor_csv.writeheader()
        escritor_csv.writerows(dados)
    print(f"Dados salvos em {nome_arquivo}.")

def processar_listagens():
    try:
        while True: 
            try:
                bid_buttons = WebDriverWait(driver, 30).until(
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
                        view_button = WebDriverWait(driver, 20).until(
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
                            close_button = WebDriverWait(driver, 20).until(
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
                    WebDriverWait(driver, 20).until(
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
        
        tables = soup.find_all('div', class_='table-responsive')
        if tables:
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                for row in rows:
                    data = [td.get_text(strip=True) for td in row.find_all('td')]
                    if data:
                        dados_coletados.append({"Tabela": i + 1, "Dados": data})
        else:
            print("DataScoutPro não possui detalhes desta propriedade !")
        
    except Exception as e:
        print(f"Erro ao coletar detalhes: {e}")

def interromper_script(signal, frame):
    print("\nInterrupção recebida! Salvando dados coletados...")
    salvar_dados_em_csv(dados_coletados)
    print("Dados salvos. Encerrando o script.")
    driver.quit()
    sys.exit(0)

signal.signal(signal.SIGINT, interromper_script)

processar_listagens()

salvar_dados_em_csv(dados_coletados)

driver.quit()
