
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_google_maps(url, progress_callback=None):
    # Configurar as opções do Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Executar em modo headless (sem interface gráfica)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=pt-BR")

    # Instanciar o WebDriver do Chrome utilizando o gerenciador nativo do Selenium
    # Se falhar, o Selenium tentará baixar o driver adequado automaticamente.
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Erro ao inicializar o ChromeDriver: {e}")
        # Tentar novamente forçando o serviço se necessário (geralmente não precisa na v4.40+)
        raise e

    try:
        # Abrir a URL
        driver.get(url)

        # Aguardar o carregamento da página
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc")))

        # Scroll no painel de resultados para carregar todas as empresas
        scrollable = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
        previous_count = 0
        retries = 0
        max_retries = 30

        while retries < max_retries:
            # Scroll incremental simulando comportamento do usuário
            driver.execute_script("""
                var el = arguments[0];
                el.scrollTop = el.scrollHeight;
            """, scrollable)
            time.sleep(2)

            # Verificar se chegamos ao final da lista checando o texto do feed
            try:
                feed_html = scrollable.get_attribute("innerHTML")
                if "Você chegou ao final da lista" in feed_html or "You&#39;ve reached the end of the list" in feed_html:
                    print("Fim da lista de resultados detectado.")
                    break
            except:
                pass

            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc"))
            if current_count == previous_count:
                retries += 1
                # Tentar scroll adicional após falha
                driver.execute_script("""
                    var el = arguments[0];
                    el.scrollBy(0, 500);
                """, scrollable)
                time.sleep(2)
            else:
                retries = 0
                previous_count = current_count
                print(f"Resultados carregados até agora: {current_count}")

        # Extrair informações das empresas
        results = []
        business_elements = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
        total = len(business_elements)
        print(f"Total de empresas encontradas: {total}")

        for i in range(total):
            # Re-localizar elementos e re-rolar se necessário para garantir que o item i existe
            business_elements = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            while len(business_elements) <= i:
                scrollable = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable)
                time.sleep(2)
                business_elements = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            business = business_elements[i]

            name = "N/A"
            address = "N/A"
            email = "N/A"
            website = "N/A"

            try:
                name = business.get_attribute("aria-label")
            except Exception as e:
                print(f"Erro ao extrair o nome: {e}")

            try:
                # Scroll o elemento para ficar visível antes de clicar
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", business)
                time.sleep(1)
                business.click()
                time.sleep(3)

                try:
                    address = driver.find_element(By.CSS_SELECTOR, "[data-item-id='address']").text.replace("\n", "")
                except:
                    pass

                try:
                    email_element = driver.find_element(By.CSS_SELECTOR, "a[href^='mailto:']")
                    email = email_element.get_attribute("href").replace("mailto:", "")
                except:
                    pass

                try:
                    website_element = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
                    website = website_element.get_attribute("href")
                except:
                    pass

                # Fechar o painel de detalhes clicando no botão voltar
                try:
                    back_btn = driver.find_element(By.CSS_SELECTOR, "button[jsaction*='back']")
                    back_btn.click()
                except:
                    driver.back()
                time.sleep(2)

                # Aguardar a lista de resultados reaparecer
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))

            except Exception as e:
                print(f"Erro ao processar empresa {i+1}/{total} ({name}): {e}")

            results.append({
                "Name": name,
                "Full Address": address,
                "EMAIL": email,
                "URL": website
            })
            print(f"Empresa {i+1}/{total} processada: {name}")
            if progress_callback:
                progress_callback(i + 1, total)

        return results

    finally:
        # Fechar o navegador
        driver.quit()

def save_to_csv(data, filename="output.csv"):
    # Criar um DataFrame a partir dos dados extraídos
    if not data:
        print("Nenhum dado para salvar.")
        return
    df = pd.DataFrame(data)

    # Salvar o DataFrame em um arquivo CSV
    df.to_csv(filename, index=False)
    print(f"Os dados foram salvos com sucesso no arquivo '{filename}'")

if __name__ == "__main__":
    from urllib.parse import quote

    termo = input("Digite o termo de busca (ex: confecções): ").strip()
    cidade = input("Digite a cidade (ex: Nova Friburgo): ").strip()

    if not termo or not cidade:
        print("Erro: termo de busca e cidade são obrigatórios.")
        exit(1)

    query = f"{termo} em {cidade}"
    search_url = f"https://www.google.com/maps/search/{quote(query)}"
    print(f"\nBuscando: {query}")
    print(f"URL: {search_url}\n")

    # Realizar o scraping
    scraped_data = scrape_google_maps(search_url)

    # Salvar os dados em um arquivo CSV
    if scraped_data:
        save_to_csv(scraped_data)
    else:
        print("Nenhum dado foi extraído.")
