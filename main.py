from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

PAGE_TO_CONSULT = "https://consultaprocesos.ramajudicial.gov.co/Procesos/NombreRazonSocial"  # Reemplaza con la URL correcta

# Acceder a la página (reemplaza con la URL correcta)



driver_path = os.path.abspath("chromedriver-win64/chromedriver.exe")
service = Service(driver_path)
driver = webdriver.Chrome(service=service)

try:
    driver.get(PAGE_TO_CONSULT)
    time.sleep(2)  # Esperar que cargue la página
    
    # 1. Verificar si el elemento existe
    try:
        radio = driver.find_element(By.ID, "input-67")
        print("Radio encontrado en el DOM:", bool(radio))
    except:
        print("No se pudo encontrar el elemento por ID")
    
    # 2. Verificar si es visible y clickeable
    try:
        radio = driver.find_element(By.ID, "input-67")
        print("Radio is_displayed():", radio.is_displayed())
        print("Radio is_enabled():", radio.is_enabled())
    except:
        print("No se puede verificar visibilidad")
    
    # 3. Probar las diferentes estrategias:
    
    # a. Click directo
    try:    
        driver.find_element(By.ID, "input-67").click()
        print("Click directo ejecutado")
    except Exception as e:
        print(f"Error en click directo: {e}")
    
    # b. Click a la etiqueta
    try:
        driver.find_element(By.XPATH, "//label[@for='input-67']").click()
        print("Click en etiqueta ejecutado")
    except Exception as e:
        print(f"Error en click a etiqueta: {e}")
    
    # c. JavaScript click
    try:
        driver.execute_script("document.getElementById('input-67').click();")
        print("JS click ejecutado")
    except Exception as e:
        print(f"Error en JS click: {e}")
    
    # Verificar el resultado
    time.sleep(1)
    resultado = driver.execute_script("return document.getElementById('input-67').getAttribute('aria-checked');")
    print(f"Estado final del radio: aria-checked='{resultado}'")
    
except Exception as e:
    print(f"Error general: {e}")
finally:
    time.sleep(15)  # Esperar para ver el resultado
    driver.quit()