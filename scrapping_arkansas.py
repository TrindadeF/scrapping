from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException
import time

options = webdriver.ChromeOptions()
options.add_argument("--disable-popup-blocking")
options.add_argument("--blink-settings=imagesEnabled=false")  
driver = webdriver.Chrome(options=options)

driver.get("https://auction.cosl.org/Auctions/ListingsView")

def clicar_no_elemento_com_javascript(elemento):
    """Clica em um elemento usando JavaScript para evitar problemas de visibilidade."""
    driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", elemento)

def processar_listagens():
    try:
        while True: 
            try:
                bid_buttons = WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1"))
                )
            except TimeoutException:
                print("Não foi possível carregar os botões 'Bid'. Encerrando o processo.")
                break

            for index in range(len(bid_buttons)):
                try:
                    bid_buttons = driver.find_elements(By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1")
                    bid_button = bid_buttons[index]
                    print(f"Processando o item {index + 1} de {len(bid_buttons)}")
                    
                    clicar_no_elemento_com_javascript(bid_button)  
                    time.sleep(3)  

                    try:
                        view_button = WebDriverWait(driver, 30).until(
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
                            close_button = WebDriverWait(driver, 30).until(
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
                    WebDriverWait(driver, 30).until(
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
                next_button = driver.find_element(By.XPATH, "//a[contains(@class, 'next-page')]")  
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
        detalhes = driver.page_source 
        print("Detalhes coletados com sucesso.")
    except Exception as e:
        print(f"Erro ao coletar detalhes: {e}")

processar_listagens()

driver.quit()
