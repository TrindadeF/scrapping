from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException
from bs4 import BeautifulSoup
from selenium.common.exceptions import StaleElementReferenceException
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from selenium.webdriver.chrome.options import Options
import time
import gspread
import signal
import sys
import os


options = webdriver.ChromeOptions()
options.add_argument("--disable-gpu") 
options.add_argument("--headless")  
driver = webdriver.Chrome(options=options)


escolha_usuario = None  
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

def buscar_planilha_por_nome(drive_service, condado):
    query = f"mimeType='application/vnd.google-apps.spreadsheet' and name='{condado}' and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        print(f"Nenhuma planilha encontrada para o condado '{condado}'")
        return None
    else:
        print(f"Planilha '{items[0]['name']}' encontrada.")
        return items[0]['id']  
def salvar_em_google_sheets(data, nome_planilha, nome_aba):
    try:
        cliente = autenticar_google_sheets()  
        if cliente is None:
            print("Falha ao autenticar no Google Sheets. Não é possível salvar os dados.")
            return
        
        try:
            pasta_projeto = cliente.open(nome_planilha.strip())  
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Planilha '{nome_planilha}' não encontrada.")
            return

        try:
            aba = pasta_projeto.worksheet(nome_aba.strip())  
            print(f"Aba '{nome_aba}' já existe. Atualizando dados...")
        except gspread.exceptions.WorksheetNotFound:
            aba = pasta_projeto.add_worksheet(title=nome_aba.strip(), rows="100", cols="20")
            print(f"Aba '{nome_aba}' criada com sucesso.")

        if data:
            headers = list(data[0].keys())  
            valores = [list(item.values()) for item in data] 

            existing_data = aba.get_all_values()  
       
            if len(existing_data) == 0:
                aba.append_row(headers) 
            else:
                range_name = 'A1:' + chr(64 + len(headers)) + '1'
                aba.update(range_name=range_name, values=[headers])  
                
            aba.append_rows(valores)  
            print(f"Dados adicionados na aba '{nome_aba}'.")
        else:
            print("Nenhum dado a ser salvo.")
    except Exception as e:
        print(f"Erro ao salvar dados no Google Sheets: {e}")


def processar_listagens(driver):
    global escolha_usuario  
    try:
        filtro_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "k-grid-filter"))
        )
        
        driver.execute_script("arguments[0].click();", filtro_btn)
        
        try:
            container_opcoes = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "k-multicheck-wrap"))
            )
        except Exception as e:
            print("Erro ao esperar o container de opções:", e)
            return

        if container_opcoes:
            print("Container de opções encontrado.")
        else:
            print("Container de opções não encontrado.")
            return
        
        time.sleep(2)

        lista_opcoes = container_opcoes.find_elements(By.CLASS_NAME, "k-item")

        if lista_opcoes:
            print("Opções encontradas:")
            for item in lista_opcoes:
                label_text = item.find_element(By.TAG_NAME, "span").text
                print(f"- {label_text}")
        else:
            print("Nenhuma opção foi encontrada dentro do container.")
            return

        escolha_usuario = input("Digite o nome do condado que deseja selecionar: ").strip().upper()

        opcao_encontrada = None
        for item in lista_opcoes:
            label_text = item.find_element(By.TAG_NAME, "span").text.strip().upper()
            if escolha_usuario in label_text:
                opcao_encontrada = item
                break

        if opcao_encontrada:
            checkbox = opcao_encontrada.find_element(By.TAG_NAME, "input")
            driver.execute_script("arguments[0].click();", checkbox)

            botao_filtrar = driver.find_element(By.CSS_SELECTOR, "button.k-primary")
            driver.execute_script("arguments[0].click();", botao_filtrar)

            time.sleep(3) 
            
            while True: 
                try:
                    bid_buttons = WebDriverWait(driver, 50).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1"))
                             )
                       
                    bid_buttons = [btn for btn in bid_buttons if btn.is_displayed() and btn.is_enabled()]

                    for index in range(len(bid_buttons)):
                        try:
                            time.sleep(3)

                            bid_buttons = WebDriverWait(driver, 50).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1"))
                             )
                            
                            bid_buttons = [btn for btn in bid_buttons if btn.is_displayed() and btn.is_enabled()]

                            bid_button = bid_buttons[index]

                            clicar_no_elemento_com_javascript(bid_button)
                            
                            print(f"Processando o item {index + 1} de {len(bid_buttons)}")
                            
                            time.sleep(6) 

                            dados_item = coletar_primeiro_detalhe()

                            try:
                                view_button = WebDriverWait(driver, 35).until(
                                    EC.presence_of_element_located((By.XPATH, "//a[@title='View on DataScoutPro']"))
                                )
                                view_button.click()
                                print("Botão 'View on DataScoutPro' clicado com Selenium.")
                                
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

                                dados_item_completo = coletar_detalhes(dados_item)

                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])

                                if dados_item_completo:
                                    dados_coletados.append(dados_item_completo)

                            except TimeoutException:
                                print("Botão 'View on DataScoutPro' não encontrado a tempo.")

                            driver.back()
                            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".k-button.k-button-icontext.ml-1")))

                            reaplicar_filtro(driver)

                        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException) as e:
                            print(f"Erro ao processar item {index + 1}: {e}")
                            driver.back()
                            reaplicar_filtro(driver)
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
                    print(f"Erro ao encontrar o botão Bid: {e}")
        else:
            print(f"Opção '{escolha_usuario}' não encontrada nas listagens.")

    except Exception as e:
        print(f"Erro ao processar as listagens: {e}")

def reaplicar_filtro(driver):
    global escolha_usuario

    if escolha_usuario:
        try:
            filtro_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "k-grid-filter"))
            )
            driver.execute_script("arguments[0].click();", filtro_btn)

            time.sleep(2)  

            container_opcoes = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".k-reset.k-multicheck-wrap"))
            )

            lista_opcoes = container_opcoes.find_elements(By.CLASS_NAME, "k-item")

            opcao_encontrada = False

            for item in lista_opcoes:
                try:
                    checkbox = item.find_element(By.CSS_SELECTOR, "input.k-checkbox")
                    valor_checkbox = checkbox.get_attribute("value").strip().upper()

                    if valor_checkbox == escolha_usuario.upper():
                        opcao_encontrada = True
                        print(f"Selecionando a opção: {valor_checkbox}")

                        checkbox = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, f"input[value='{valor_checkbox}']"))
                        )
                        
                        driver.execute_script("arguments[0].click();", checkbox)
           
                        botao_filtrar = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.k-primary"))
                        )
                        driver.execute_script("arguments[0].click();", botao_filtrar)


                        print(f"Filtro reaplicado para a opção: {escolha_usuario}")
                        continue
                except StaleElementReferenceException:
                    print("Elemento ficou obsoleto, tentando recapturar o elemento...")
                    container_opcoes = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".k-reset.k-multicheck-wrap"))
                    )
                    lista_opcoes = container_opcoes.find_elements(By.CLASS_NAME, "k-item")
                    continue

            if not opcao_encontrada:
                print(f"Opção '{escolha_usuario}' não encontrada durante a reaplicação do filtro.")

        except StaleElementReferenceException as e:
            print("Elemento desatualizado, recarregando a página e tentando novamente.")
    
            driver.refresh()  
            time.sleep(5)  
            reaplicar_filtro(driver)  

        except Exception as e:
            print(f"Erro ao reaplicar o filtro: {e}")


def coletar_primeiro_detalhe():
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        dados_item = {}  

        dl_elements = soup.find_all('dl', class_='row row-border-bottom p-1 m-1')

        if len(dl_elements) >= 5:
            segundo_dl = dl_elements[1]  
            quinto_dl = dl_elements[4]  

            def processar_dl(dl):
                dt_elements = dl.find_all('dt')
                dd_elements = dl.find_all('dd')
                dados = {}

                for dt, dd in zip(dt_elements, dd_elements):
                    chave = dt.get_text(strip=True)
                    valor = dd.get_text(strip=True)

                    if chave and chave not in dados_item:  
                        dados[chave] = valor
                return dados

            dados_segundo_dl = processar_dl(segundo_dl)
            dados_quinto_dl = processar_dl(quinto_dl)

            dados_item.update(dados_segundo_dl)
            dados_item.update(dados_quinto_dl)

            if dados_item:   
                print("Dados da primeira página coletados com sucesso!")
                return dados_item
            else: 
                print("Nenhum detalhe encontrado na primeira página.")
        else:
            print("As tabelas segunda e/ou quinta não foram encontradas.")

    except Exception as e:
        print(f"Erro ao coletar o primeiro detalhe: {e}")


def coletar_detalhes(dados_item):
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        secoes_desejadas = ["Property Owner", "Property Information"]
    

        for secao_nome in secoes_desejadas:
            div_secao = soup.find('div', string=secao_nome)
            
            if div_secao:
                tabela = div_secao.find_next('table')
                
                if tabela:
                    rows = tabela.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        
                        if len(cells) == 2:
                            chave = cells[0].get_text(strip=True).replace(':', '')
                            valor = cells[1].get_text(strip=True)
                            
                            if chave and chave not in dados_item:
                                dados_item[chave] = valor
                else:
                    print(f"Tabela não encontrada para a seção: {secao_nome}")
            else:
                print(f"Div não encontrada para a seção: {secao_nome}")

        div_secao_market = soup.find('div', string="Market and Assessed Values")
        
        if div_secao_market:
            tabela_market = div_secao_market.find_next('table')
            
            if tabela_market:
                thead = tabela_market.find('thead')
                if thead:
                    headers = [th.get_text(strip=True) for th in thead.find_all('td')]
                
                tbody = tabela_market.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        
                        if len(cells) == len(headers):
                            for index, header in enumerate(headers):
                                chave = header
                                valor = cells[index].get_text(strip=True)
                                
                                if chave and chave not in dados_item:
                                    dados_item[chave] = valor
            else:
                print("Tabela não encontrada para a seção: Market and Assessed Values")
        else:
            print("Div não encontrada para a seção: Market and Assessed Values")

        if dados_item:
            print("Dados da segunda pagina coletdos com sucesso ! ")
            return dados_item
        else:
            print("Nenhum dado coletado das seções especificadas.")
            return dados_item
        
    except Exception as e:
        print(f"Erro ao coletar detalhes: {e}")


def interromper_script(signal, frame):
    try:
        print("\nInterrupção recebida! Salvando dados coletados...")

        salvar_em_google_sheets(dados_coletados, escolha_usuario, "Dados_Atualizados") 
        
        print(f"Dados salvos para o condado {escolha_usuario}. Encerrando o script.")
    except Exception as e:
        print(f"Erro ao salvar os dados: {str(e)}")
    finally:
        driver.quit()
        sys.exit()


signal.signal(signal.SIGINT, interromper_script)

processar_listagens(driver)

salvar_em_google_sheets(dados_coletados, escolha_usuario, "Dados_Atualizados")

driver.quit()
