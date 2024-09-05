from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException
import time

# Configurações do Selenium
options = webdriver.ChromeOptions()
options.add_argument("--disable-popup-blocking")
options.add_argument("--blink-settings=imagesEnabled=false")  
driver = webdriver.Chrome(options=options)

# Acessa o site
driver.get("https://auction.cosl.org/Auctions/ListingsView")

def clicar_no_elemento_com_javascript(elemento):
    """Clica em um elemento usando JavaScript para evitar problemas de visibilidade."""
    driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", elemento)

def processar_listagens():
    try:
        while True:  # Loop para garantir que percorre todas as páginas de listagens
            # Espera os botões "Bid" com a classe especificada carregarem
            try:
                bid_buttons = WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1"))
                )
            except TimeoutException:
                print("Não foi possível carregar os botões 'Bid'. Encerrando o processo.")
                break

            for index in range(len(bid_buttons)):
                try:
                    # Re-localiza os botões a cada iteração para evitar o erro `stale element reference`
                    bid_buttons = driver.find_elements(By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1")
                    bid_button = bid_buttons[index]
                    print(f"Processando o item {index + 1} de {len(bid_buttons)}")
                    
                    clicar_no_elemento_com_javascript(bid_button)  # Clica no botão "Bid"
                    time.sleep(3)  # Ajuste conforme necessário

                    # Espera o botão "View on DataScoutPro" usando o atributo title
                    try:
                        view_button = WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.XPATH, "//a[@title='View on DataScoutPro']"))
                        )

                        # Tentativa de clicar no link usando Selenium
                        try:
                            view_button.click()
                            print("Botão 'View on DataScoutPro' clicado com Selenium.")
                        except (ElementClickInterceptedException, ElementNotInteractableException):
                            print("Falha ao clicar no botão com Selenium, tentando com JavaScript.")
                            clicar_no_elemento_com_javascript(view_button)  # Tenta clicar com JavaScript

                        time.sleep(3)  # Ajuste conforme necessário

                        # Coleta os detalhes da página atual (adapte a função conforme necessário)
                        coletar_detalhes()

                    except TimeoutException:
                        print("Botão 'View on DataScoutPro' não encontrado a tempo.")

                    # Volta para a página de listagens usando o "voltar" do navegador
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

            # Verifica se há um botão "Next" para navegar para a próxima página de listagens
            try:
                next_button = driver.find_element(By.XPATH, "//a[contains(@class, 'next-page')]")  # Ajuste o seletor conforme necessário
                if next_button.is_displayed() and next_button.is_enabled():
                    print("Indo para a próxima página de listagens...")
                    clicar_no_elemento_com_javascript(next_button)
                    time.sleep(3)
                else:
                    print("Fim das listagens.")
                    break
            except NoSuchElementException:
                print("Botão 'Next' não encontrado. Fim das listagens.")
                break  # Sai do loop se o botão "Next" não for encontrado

    except Exception as e:
        print(f"Erro ao processar as listagens: {e}")

# Função para coletar detalhes (substitua pelo que é necessário coletar)
def coletar_detalhes():
    try:
        # Exemplo: Coletar algum detalhe da página atual
        detalhes = driver.page_source  # Ou use BeautifulSoup para parsear os detalhes necessários
        print("Detalhes coletados com sucesso.")
    except Exception as e:
        print(f"Erro ao coletar detalhes: {e}")

# Executa a função para processar as listagens
processar_listagens()

# Fecha o navegador
driver.quit()
