import time
import json
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

class JudicialProcessScraper:
    """
    A class to scrape information from the Colombian judicial processes website
    by iterating through all possible combinations of search parameters.
    """
    
    def __init__(self, search_name, headless=False):
        """
        Initialize the scraper with the search name and browser settings
        
        Args:
            search_name (str): The name to search for
            headless (bool): Whether to run the browser in headless mode
        """
        self.url = "https://consultaprocesos.ramajudicial.gov.co/Procesos/NombreRazonSocial"
        self.search_name = search_name
        self.results = []
        
        # Configure Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1400,800")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        # Initialize the WebDriver with proper error handling
        try:
            logging.info("Initializing Chrome WebDriver...")
            
            try:
                # Use the local ChromeDriver in the chromedriver-win64 directory
                driver_path = os.path.abspath("chromedriver-win64/chromedriver.exe")
                
                # Verify that the driver exists before trying to use it
                if not os.path.exists(driver_path):
                    raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")
                
                logging.info(f"Using ChromeDriver at: {driver_path}")
                
                # Initialize the WebDriver with the service
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
            except Exception as err:
                logging.error(f"ChromeDriver initialization failed: {err}")
                raise
            # Set up wait mechanism with longer timeout
            self.wait = WebDriverWait(self.driver, 30)
            self.short_wait = WebDriverWait(self.driver, 5)  # For quick checks
            logging.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize Chrome WebDriver: {e}")
            print("\nChrome WebDriver initialization failed. Please ensure:")
            print("1. Chrome browser is installed and up to date")
            print("2. You have proper permissions to execute programs")
            print("3. Your antivirus is not blocking WebDriver")
            raise
    
    def __del__(self):
        """Clean up resources by closing the browser when done"""
        if hasattr(self, 'driver'):
            try:
                logging.info("Closing Chrome WebDriver...")
                self.driver.quit()
                logging.info("Chrome WebDriver closed successfully")
            except Exception as e:
                logging.error(f"Error closing Chrome WebDriver: {e}")
    
    def initialize_search_form(self, max_retries=1):
        """Navigate to the search page and set initial form values with retries"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                logging.info(f"Navigating to URL: {self.url} (Attempt {retry_count + 1}/{max_retries})")
                self.driver.get(self.url)
                
                # Wait for the page to load with multiple conditions
                logging.info("Waiting for page to fully load...")
                
                # First wait for document ready state
                self.wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
                logging.info("Document ready state complete")
                
                # Then wait for jQuery to be loaded and active (if present)
                jquery_ready = """
                    return (typeof jQuery !== 'undefined') ? 
                        jQuery.active === 0 : true;
                """
                try:
                    self.short_wait.until(lambda d: d.execute_script(jquery_ready))
                    logging.info("jQuery ready state complete")
                except:
                    logging.info("jQuery not detected on page, continuing")
                
                # Additional wait time for any asynchronous content
                #time.sleep(1)
                
                # Try multiple selector strategies for the radio button
                logging.info("Selecting 'Todos los procesos (consulta completa, menos rápida)'...")
                radio_selectors = [
                    # New selector format with aria-checked attribute
                    (By.XPATH, "//label[@for='input-67']")
                ]
                radio_todos = None
                for selector in radio_selectors:
                    try:
                        logging.info(f"Trying selector: {selector}")
                        radio_todos = self.wait.until(EC.element_to_be_clickable(selector))
                        if radio_todos:
                            break
                    except Exception as e:
                        logging.warning(f"Selector {selector} failed: {e}")
                
                if not radio_todos:
                    raise NoSuchElementException("Could not find radio button with any selector")
                
                try:
                    radio_todos.click()
                except Exception as click_error:
                    logging.warning(f"Standard click failed: {click_error}")
                                   
                logging.info("Radio button selected successfully")

                # Set the "Tipo Persona" select to "Natural" with better error handling
                logging.info("Setting 'Tipo Persona' to 'Natural'...")
                try:
                    # Wait for the select element to be present
                    logging.info("Opened 'Tipo Persona' dropdown...")
                    button_tipo_persona_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='list-72']"))
                    )
                    button_tipo_persona_element.click()
                    #time.sleep(1)  # Wait for the dropdown to open
                    logging.info("Selecting 'Natural' from dropdown...")
                    tipo_persona_element = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-list-item')][.//div[contains(@class, 'v-list-item__title') and normalize-space()='Natural']]"))
                    )
                    
                    tipo_persona_element.click()
                    logging.info("Tipo Persona set successfully")
                except Exception as e:
                    logging.error(f"Error setting Tipo Persona: {e}")
                    # Take a screenshot for debugging
                    screenshot_path = f"error_screen_{int(time.time())}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logging.info(f"Screenshot saved to {screenshot_path}")
                    raise
                
                # Fill the name field with better error handling
                logging.info(f"Filling name field with: {self.search_name}")
                try:
                    nombre_input = self.wait.until(
                        EC.presence_of_element_located((By.ID, "input-78"))
                    )
                    nombre_input.clear()
                    nombre_input.send_keys(self.search_name)
                    logging.info("Name field filled successfully")
                    
                    # Successfully initialized the form, return from the function
                    return
                except Exception as e:
                    logging.error(f"Error filling name field: {e}")
                    # Take a screenshot for debugging
                    screenshot_path = f"error_screen_{int(time.time())}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logging.info(f"Screenshot saved to {screenshot_path}")
                    raise
                    
            except Exception as e:
                logging.error(f"Error initializing search form: {e}")
            
            # If we got here, there was an error, increment retry counter and try again
            retry_count += 1
            logging.warning(f"Retrying form initialization (attempt {retry_count + 1}/{max_retries})")
            #time.sleep(5)  # Wait before retrying
            
        # If we exhausted all retries, raise an exception
        raise Exception(f"Failed to initialize search form after {max_retries} attempts")
        
    def handle_select_chain(self, department_index=1, city_index=1, entity_index=1, 
                            specialty_index=1, office_index=1, max_retries=3):
        """
        Handle the chain of dependent select fields with backtracking
        
        This method implements the backtracking algorithm to try all combinations
        of the select fields in the form.
        """
        # Select Department (Departamento)
        # Select Department (Departamento) with retry logic
        for retry in range(max_retries):
            try:
                # Wait for both presence and interactability
                dept_element = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='list-83']"))
                )
                dept_element.click()
                #time.sleep(1)  # Wait for the dropdown to open
                departmentList = self.wait.until(EC.visibility_of_element_located((By.ID, "list-83")))
                break
            except (TimeoutException, StaleElementReferenceException) as e:
                if retry == max_retries - 1:
                    logging.error(f"Failed to select department after {max_retries} attempts: {e}")
                    raise
                logging.warning(f"Attempt {retry+1}/{max_retries} failed to select department: {e}")
                # Take a screenshot for debugging
                self.driver.save_screenshot(f"dept_select_error_{retry}.png")
                # Refresh the page and reinitialize form if needed
                if retry > 0:
                    self.driver.refresh()
                    #time.sleep(3)
                    # Wait for document ready state
                    self.wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        # Get all department options
        try:
            logging.info("Getting department options...")
            departments = departmentList.find_elements(By.CSS_SELECTOR, ".v-list-item__title")
            logging.info(f"Found {len(departments)-1} departments")
        except Exception as e:
            logging.error(f"Error getting department options: {e}")
            departments = []
            
        if len(departments) <= 1:
            logging.warning("No department options found, cannot proceed")
            return
            
        if department_index >= len(departments):
            logging.info("All departments processed")
            return  # All departments processed
        
        try:
            department_element_to_click = departments[department_index]
            department_element_to_click.click()
            
            selected_dept_text = department_element_to_click.text
            
            logging.info(f"Selected Department: {department_index} - {selected_dept_text}")
            #time.sleep(1)
        except Exception as e:
            logging.error(f"Error selecting department {department_index}: {e}")
            # Try to recover by moving to the next department
            self.handle_select_chain(department_index + 1, city_index, entity_index, specialty_index, office_index)
            return
        
        # Select City (Ciudad)
        # Select City (Ciudad) with retry logic
        for retry in range(max_retries):
            try:
                # Make sure the city dropdown has loaded after department selection
                city_element = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='list-89']"))
                )
                city_element.click()
                #time.sleep(2)  # Wait for the dropdown to open
                cityList = self.wait.until(EC.visibility_of_element_located((By.ID, "list-89")))
                break
            except (TimeoutException, StaleElementReferenceException) as e:
                if retry == max_retries - 1:
                    logging.error(f"Failed to select city after {max_retries} attempts: {e}")
                    raise
                logging.warning(f"Attempt {retry+1}/{max_retries} failed to select city: {e}")
                #time.sleep(2)
        
        # Get all city options for the selected department
        try:
            logging.info("Getting city options...")
            cities = cityList.find_elements(By.CSS_SELECTOR, ".v-list-item__title")
            logging.info(f"Found {len(cities)-1} cities for department {selected_dept_text}")
        except Exception as e:
            logging.error(f"Error getting city options: {e}")
            cities = []
            
        if len(cities) <= 1:
            logging.warning(f"No city options found for department {selected_dept_text}, moving to next department")
            self.handle_select_chain(department_index + 1, city_index, entity_index, specialty_index, office_index)
            return
            
        if city_index >= len(cities):
            logging.info(f"All cities processed for department {selected_dept_text}")
            # Move to next department
            self.handle_select_chain(department_index + 1, 1, 1, 1, 1)
            return
        
        try:
            city_element_to_click = cities[city_index]
            city_element_to_click.click()
            
            selected_city_text = city_element_to_click.text
            
            logging.info(f"Selected City: {city_index} - {selected_city_text}")
            #time.sleep(1)
        except Exception as e:
            logging.error(f"Error selecting city {city_index}: {e}")
            # Try to recover by moving to the next city
            self.handle_select_chain(department_index, city_index + 1, 1, 1, 1)
            return
        # Select Entity (Entidad)
        # Select Entity (Entidad) with retry logic
        for retry in range(max_retries):
            try:
                # Wait for entity dropdown to be interactive
                entity_element = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='list-95']"))
                )
                entity_element.click()
                #time.sleep(1)  # Wait for the dropdown to open
                entityList = self.wait.until(EC.visibility_of_element_located((By.ID, "list-95")))
                break
            except (TimeoutException, StaleElementReferenceException) as e:
                if retry == max_retries - 1:
                    logging.error(f"Failed to select entity after {max_retries} attempts: {e}")
                    raise
                logging.warning(f"Attempt {retry+1}/{max_retries} failed to select entity: {e}")
                #time.sleep(2)
        
        # Get all entity options for the selected city
        try:
            logging.info("Getting entity options...")
            entities = entityList.find_elements(By.CSS_SELECTOR, ".v-list-item__title")
            logging.info(f"Found {len(entities)-1} entities for city {selected_city_text}")
        except Exception as e:
            logging.error(f"Error getting entity options: {e}")
            entities = []
            
        if len(entities) <= 1:
            logging.warning(f"No entity options found for city {selected_city_text}, moving to next city")
            self.handle_select_chain(department_index, city_index + 1, 1, 1, 1)
            return
            
        if entity_index >= len(entities):
            logging.info(f"All entities processed for city {selected_city_text}")
            # Move to next city
            self.handle_select_chain(department_index, city_index + 1, 1, 1, 1)
            return
        
        try:
            entity_element_to_click = entities[entity_index]
            entity_element_to_click.click()
            
            selected_entity_text = entity_element_to_click.text            
            
            logging.info(f"Selected Entity: {entity_index} - {selected_entity_text}")
            #time.sleep(1)
        except Exception as e:
            logging.error(f"Error selecting entity {entity_index}: {e}")
            # Try to recover by moving to the next entity
            self.handle_select_chain(department_index, city_index, entity_index + 1, 1, 1)
            return
        
        #time.sleep(1)
        
        # Select Specialty (Especialidad)
        # Select Specialty (Especialidad) with retry logic
        for retry in range(max_retries):
            try:
                # Wait for specialty dropdown to be interactive
                specialty_element = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='list-101']"))
                )
                specialty_element.click()
                #time.sleep(1)  # Wait for the dropdown to open
                specialtyList = self.wait.until(EC.visibility_of_element_located((By.ID, "list-101")))
                break
            except (TimeoutException, StaleElementReferenceException) as e:
                if retry == max_retries - 1:
                    logging.error(f"Failed to select specialty after {max_retries} attempts: {e}")
                    raise
                logging.warning(f"Attempt {retry+1}/{max_retries} failed to select specialty: {e}")
                #time.sleep(2)

        # Get all specialty options for the selected entity
        try:
            logging.info("Getting specialty options...")
            specialties = specialtyList.find_elements(By.CSS_SELECTOR, ".v-list-item__title")
            logging.info(f"Found {len(specialties)-1} specialties for entity {selected_entity_text}")
        except Exception as e:
            logging.error(f"Error getting specialty options: {e}")
            specialties = []
            
        if len(specialties) <= 1:
            logging.warning(f"No specialty options found for entity {selected_entity_text}, moving to next entity")
            self.handle_select_chain(department_index, city_index, entity_index + 1, 1, 1)
            return
            
        if specialty_index >= len(specialties):
            logging.info(f"All specialties processed for entity {selected_entity_text}")
            # Move to next entity
            self.handle_select_chain(department_index, city_index, entity_index + 1, 1, 1)
            return
        
        try:
            specialty_element_to_click = specialties[specialty_index]
            specialty_element_to_click.click()
            
            selected_specialty_text = specialty_element_to_click.text
            
            logging.info(f"Selected Specialty: {specialty_index} - {selected_specialty_text}")
            #time.sleep(1)
        except Exception as e:
            logging.error(f"Error selecting specialty {specialty_index}: {e}")
            # Try to recover by moving to the next specialty
            self.handle_select_chain(department_index, city_index, entity_index, specialty_index + 1, 1)
            return
        
        #time.sleep(1)
        
        # Select Office (Despacho)
        # Select Office (Despacho) with retry logic
        for retry in range(max_retries):
            try:
                # Wait for office dropdown to be interactive
                office_element = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='list-107']"))
                )
                office_element.click()
                #time.sleep(1)  # Wait for the dropdown to open
                officeList = self.wait.until(EC.visibility_of_element_located((By.ID, "list-107")))
                break
            except (TimeoutException, StaleElementReferenceException) as e:
                if retry == max_retries - 1:
                    logging.error(f"Failed to select office after {max_retries} attempts: {e}")
                    raise
                logging.warning(f"Attempt {retry+1}/{max_retries} failed to select office: {e}")
                #time.sleep(2)
        
        # Get all office options for the selected specialty
        try:
            logging.info("Getting office options...")
            offices = officeList.find_elements(By.CSS_SELECTOR, ".v-list-item__title")
            logging.info(f"Found {len(offices)-1} offices for specialty {selected_specialty_text}")
        except Exception as e:
            logging.error(f"Error getting office options: {e}")
            offices = []
            
        if len(offices) <= 1:
            logging.warning(f"No office options found for specialty {selected_specialty_text}, moving to next specialty")
            self.handle_select_chain(department_index, city_index, entity_index, specialty_index + 1, 1)
            return
            
        if office_index >= len(offices):
            logging.info(f"All offices processed for specialty {selected_specialty_text}")
            # Move to next specialty
            self.handle_select_chain(department_index, city_index, entity_index, specialty_index + 1, 1)
            return
        
        try:
            office_element_to_click = offices[office_index]
            office_element_to_click.click()
            
            selected_office_text = office_element_to_click.text
            
            logging.info(f"Selected Office: {office_index} - {selected_office_text}")
            #time.sleep(1)
        except Exception as e:
            logging.error(f"Error selecting office {office_index}: {e}")
            # Try to recover by moving to the next office
            self.handle_select_chain(department_index, city_index, entity_index, specialty_index, office_index + 1)
            return
        
        # Click the search button
        # Click the search button with retry logic
        for retry in range(max_retries):
            try:
                search_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @aria-label= 'Consultar por nombre o razón social']"))
                )
                search_button.click()
                break
            except (TimeoutException, StaleElementReferenceException) as e:
                if retry == max_retries - 1:
                    logging.error(f"Failed to click search button after {max_retries} attempts: {e}")
                    raise
                logging.warning(f"Attempt {retry+1}/{max_retries} failed to click search button: {e}")
                #time.sleep(2)
        # Wait for results
        time.sleep(5)
        
        # Handle search results
        self.handle_search_results({
            'department': selected_dept_text,
            'city': selected_city_text,
            'entity': selected_entity_text,
            'specialty': selected_specialty_text,
            'office': selected_office_text
        })
        
        # Move to next office
        self.handle_select_chain(department_index, city_index, entity_index, specialty_index, office_index + 1)
    
    def handle_search_results(self, search_params):
        """
        Handle search results - save successful searches, handle no results case
        
        Args:
            search_params (dict): Dictionary containing the combination of search parameters
        """
        try:
            # Check if no results message is present
            time.sleep(3)
            modal_dialog = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog' and @aria-modal='true' and contains(@class, 'v-dialog__content--active')]")))
            no_results_message = "La consulta no generó resultados, por favor revisar las opciones ingresadas e intentarlo nuevamente."
            
            if(not modal_dialog.is_displayed()):
                logging.info("Error showing the result of the search")
                return    
            
            
            #modal_alert = modal_dialog.find_element(By.XPATH, "//div[@class='v-alert__content']")
            modal_message = modal_dialog.find_element(By.XPATH, "//p[@class='pl-1']")
            text_result = modal_message.text.strip()   
            logging.info(f"Modal message: {text_result}")             
            
            
            if no_results_message in text_result:
                print("        No results found, trying next combination")
                # Click the "Volver" button
                back_button = self.driver.find_element(By.XPATH, "//button[@type='button' and @class='v-btn v-btn--is-elevated v-btn--has-bg theme--dark v-size--default leading']")
                back_button.click()
                time.sleep(2)
                return
            
            # If we get here, we have results
            print("        Found results!")
            
            # Extract results table
            results_table = self.wait.until(
                EC.presence_of_element_located((By.ID, "ResultadoConsulta"))
            )
            
            rows = results_table.find_elements(By.TAG_NAME, "tr")
            table_data = []
            
            for row in rows[1:]:  # Skip header row
                cols = row.find_elements(By.TAG_NAME, "td")
                if cols:
                    row_data = {}
                    # Assuming the table has columns: Radicado, Fecha de Radicación, Despacho, Class, etc.
                    if len(cols) >= 5:
                        row_data['radicado'] = cols[0].text.strip()
                        row_data['fecha_radicacion'] = cols[1].text.strip()
                        row_data['despacho'] = cols[2].text.strip()
                        row_data['clase'] = cols[3].text.strip()
                        row_data['sujetos'] = cols[4].text.strip()
                    table_data.append(row_data)
            
            # Add to results with the search parameters
            result_entry = {
                'search_params': search_params,
                'search_name': self.search_name,
                'results': table_data
            }
            
            self.results.append(result_entry)
            
            # Click back to try next combination
            back_button = self.driver.find_element(By.ID, "btnNuevaConsulta")
            back_button.click()
            time.sleep(2)
            
        except Exception as e:
            print(f"Error handling search results: {e}")
            # Try to go back to search form
            try:
                self.driver.get(self.url)
                #time.sleep(3)
                self.initialize_search_form(max_retries=3)
            except Exception as inner_e:
                print(f"Error recovering from exception: {inner_e}")
    
    def save_results(self, filename="judicial_results.json"):
        """
        Save the scraped results to a JSON file
        
        Args:
            filename (str): The name of the file to save results to
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'search_name': self.search_name,
                'total_results': len(self.results),
                'results': self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"Results saved to {filename}")
    
    def run(self):
        """Run the complete scraping process"""
        try:
            logging.info(f"Starting scraping for name: {self.search_name}")
            
            # Initialize the search form
            self.initialize_search_form()
            
            # Start the recursive backtracking algorithm
            logging.info("Starting backtracking algorithm to try all combinations...")
            self.handle_select_chain()
            
            # Save results
            logging.info("Saving results...")
            self.save_results()
            
            logging.info(f"Scraping complete. Found {len(self.results)} results.")
            
        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}", exc_info=True)
        finally:
            try:
                if hasattr(self, 'driver'):
                    logging.info("Closing WebDriver...")
                    self.driver.quit()
            except Exception as e:
                logging.error(f"Error closing WebDriver: {str(e)}")
    
    def close(self):
        if hasattr(self, 'driver'):
            try:
                self.driver.title 
                self.driver.quit()
                logging.info("Browser closed successfully.")
            except Exception as e:
                logging.warning(f"Error closing browser: {str(e)}")

def main():
    """Main function to run the scraper"""
    scraper = None
    try:
        logging.info("Starting judicial process scraper")
        search_name = input("Enter the name to search for: ")
        logging.info(f"User entered search name: {search_name}")

        scraper = JudicialProcessScraper(search_name, headless=False)
        scraper.run()

    except KeyboardInterrupt:
        logging.warning("Scraping interrupted by user.")
        print("\nScraping interrupted by user.")

        if scraper and hasattr(scraper, 'results') and scraper.results:
            logging.info("Saving partial results...")
            scraper.save_results()

    except Exception as e:
        logging.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}")

    finally:
        if scraper:
            try:
                scraper.close()
            except Exception as e:
                logging.warning(f"Error while closing scraper: {str(e)}")


if __name__ == "__main__":
    main()

