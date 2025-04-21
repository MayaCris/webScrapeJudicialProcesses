from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

class SelectionLevel(Enum):
    DEPARTMENT = ("list-83", "department")
    CITY = ("list-89", "city")
    ENTITY = ("list-95", "entity")
    SPECIALTY = ("list-101", "specialty")
    OFFICE = ("list-107", "office")

    def __init__(self, list_id: str, level_name: str):
        self.list_id = list_id
        self.level_name = level_name

@dataclass
class SelectionState:
    """Class to maintain the current state of selections"""
    department: Optional[str] = None
    city: Optional[str] = None
    entity: Optional[str] = None
    specialty: Optional[str] = None
    office: Optional[str] = None
    department_index: Optional[int] = None
    city_index: Optional[int] = None
    entity_index: Optional[int] = None
    specialty_index: Optional[int] = None
    office_index: Optional[int] = None
    
    def reset_from_level(self, level: SelectionLevel):
        """Reset all selections from the given level onwards"""
        levels = list(SelectionLevel)
        start_idx = levels.index(level)
        
        for lvl in levels[start_idx:]:
            setattr(self, lvl.level_name, None)
            setattr(self, f"{lvl.level_name}_index", None)

class JudicialProcessScraper:
    def __init__(self, search_name, target_department: Optional[str] =None, headless=False):
        self.url = "https://consultaprocesos.ramajudicial.gov.co/Procesos/NombreRazonSocial"
        self.search_name = search_name
        self.target_department = target_department
        self.results = []
        self.selection_state = SelectionState()
        
        # Initialize Chrome
        self._setup_chrome(headless)
        
    def _setup_chrome(self, headless):
        """Set up Chrome driver with appropriate options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1400,800")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        try:
            driver_path = os.path.abspath("chromedriver-win64/chromedriver.exe")
            if not os.path.exists(driver_path):
                raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")
            
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            self.short_wait = WebDriverWait(self.driver, 5)
            
        except Exception as e:
            logging.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    def _initialize_form(self):
        """Initialize the search form with initial values"""
        try:
            # Wait for page load
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Select "Todos los procesos" radio button
            radio = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//label[@for='input-67']")))
            radio.click()
            
            # Set "Tipo Persona" to "Natural"
            tipo_persona = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[@role='button' and @aria-haspopup='listbox' and @aria-owns='list-72']")
            ))
            tipo_persona.click()
            
            natural_option = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class, 'v-list-item')][.//div[contains(@class, 'v-list-item__title') and normalize-space()='Natural']]")
            ))
            natural_option.click()
            
            # Fill name field
            nombre_input = self.wait.until(EC.presence_of_element_located((By.ID, "input-78")))
            nombre_input.clear()
            nombre_input.send_keys(self.search_name)
            
        except Exception as e:
            logging.error(f"Error initializing form: {e}")
            raise

    def _find_and_select_target_department(self) -> Optional[int]:
        """
        Finds the index of the target department, selects it, and returns the index.
        Returns None if the department is not found or an error occurs.
        """
        if not self.target_department:
            return None # Should not be called if no target is set, but safe check

        level = SelectionLevel.DEPARTMENT
        target_name_upper = self.target_department.strip().upper()
        logging.info(f"Attempting to find and select target department: {target_name_upper}")

        try:
            # Click dropdown to open it
            button_xpath = f"//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='{level.list_id}']"
            dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
            self.driver.execute_script("arguments[0].click();", dropdown)

            # Wait for list to be visible
            option_list = self.wait.until(EC.visibility_of_element_located((By.ID, level.list_id)))
            options = option_list.find_elements(By.CSS_SELECTOR, ".v-list-item__title")

            found_index = -1
            for index, option in enumerate(options):
                option_text = option.text.strip().upper()
                if option_text == target_name_upper:
                    logging.info(f"Found target department '{target_name_upper}' at index {index}.")
                    # Select the option
                    self.short_wait.until(EC.visibility_of(option))
                    self.short_wait.until(EC.element_to_be_clickable(option))
                    self.driver.execute_script("arguments[0].click();", option)

                    # Update state
                    setattr(self.selection_state, level.level_name, option.text) # Use original case text
                    setattr(self.selection_state, f"{level.level_name}_index", index)
                    logging.info(f"Selected {level.level_name}: {option.text} (Index: {index}) (Pending: {len(options) - index - 1})")

                    # Wait for dropdown to close
                    try:
                        self.short_wait.until(EC.invisibility_of_element_located((By.ID, level.list_id)))
                    except TimeoutException:
                        logging.warning(f"Dropdown list {level.list_id} did not become invisible after selection.")

                    found_index = index
                    break # Exit loop once found and selected

            if found_index == -1:
                logging.error(f"Target department '{target_name_upper}' not found in the list.")
                # Close dropdown if still open
                try:
                    if dropdown.get_attribute("aria-expanded") == "true":
                         self.driver.execute_script("arguments[0].click();", dropdown) # Click again to close
                except: # Ignore errors trying to close
                    pass
                return None

            return found_index

        except Exception as e:
            logging.error(f"Error finding or selecting target department '{target_name_upper}': {e}", exc_info=True)
            return None
      
    
    def _select_dropdown_option(self, level: SelectionLevel, option_index: int) -> bool:
        """
        Select an option from a dropdown at the specified level
        Returns True if selection was successful
        """
        try:
            # Click dropdown to open it
            button_xpath = f"//div[@role='button' and @aria-haspopup='listbox' and @aria-expanded='false' and @aria-owns='{level.list_id}']"
            dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
            self.driver.execute_script("arguments[0].click();", dropdown)
            #dropdown.click()
            
            # Wait for list to be visible
            option_list = self.wait.until(EC.visibility_of_element_located((By.ID, level.list_id)))
            options = option_list.find_elements(By.CSS_SELECTOR, ".v-list-item__title")
            
            if len(options) <= 1 or option_index >= len(options):
                logging.info(f"No more options at {level.level_name} level")
                setattr(self.selection_state, level.level_name, None)
                setattr(self.selection_state, f"{level.level_name}_index", None)
                return False
                
            # Select the option
            option = options[option_index]
            option_text = option.text
            self.short_wait.until(EC.visibility_of(option))
            self.short_wait.until(EC.element_to_be_clickable(option))
            self.driver.execute_script("arguments[0].click();", option)
            #option.click()
            
            # Update state
            setattr(self.selection_state, level.level_name, option_text)
            setattr(self.selection_state, f"{level.level_name}_index", option_index)
            logging.info(f"Selected {level.level_name}: {option_text} (Index: {option_index}) (Pending: {len(options) - option_index - 1})")
            
            try:
                self.short_wait.until(EC.invisibility_of_element_located((By.ID, level.list_id)))
            except TimeoutException:
                logging.warning(f"Dropdown list {level.list_id} did not become invisible after selection.")
                # Might need a different wait strategy if invisibility isn't reliable
            
            return True
        
        except StaleElementReferenceException:
            logging.warning(f"Stale element reference encountered while selecting {level.level_name} index {option_index}. Retrying might be needed or adjust waits.")
            return False # Indicate failure on stale element
        except Exception as e:
            logging.error(f"Error selecting {level.level_name}: {e}")
            return False

    def _navigate_selection_chain(self, level: SelectionLevel, index: int = 1) -> None:
        """
        Navigate through the selection chain with smart backtracking
        """
        logging.debug(f"Navigating level: {level.level_name}, attempting index: {index}") # Add debug logging
        
        if not self._select_dropdown_option(level, index):
            # No more options at this level, go back one level
            prev_levels = list(SelectionLevel)
            current_idx = prev_levels.index(level)
            
            if current_idx > 0:
                prev_level = prev_levels[current_idx - 1]
                
                prev_index = getattr(self.selection_state, f"{prev_level.level_name}_index", 1)
                logging.debug(f"Backtracking from {level.level_name} to {prev_level.level_name}. Previous index was {prev_index}. Trying next: {prev_index + 1}")
                
                self.selection_state.reset_from_level(prev_level)
                self._navigate_selection_chain(prev_level, prev_index + 1)
            else:
                # We are at the first level (DEPARTMENT) and ran out of options
                logging.info("Finished processing all departments.")
            
            return
            
        # Successfully selected at this level, move to next level
        next_levels = list(SelectionLevel)
        current_idx = next_levels.index(level)
        
        if current_idx < len(next_levels) - 1:
            next_level = next_levels[current_idx + 1]
            logging.debug(f"Moving to next level: {next_level.level_name}")
            self._navigate_selection_chain(next_level, 1)
        else:
            # We've reached the end of the chain, perform search
            logging.debug(f"Reached end of chain ({level.level_name} index {index}). Performing search.")
            self._perform_search()
            # Try next option at current level
            logging.debug(f"Search complete for {level.level_name} index {index}. Trying next index: {index + 1}")
            self._navigate_selection_chain(level, index + 1)

    def _perform_search(self) -> None:
        """
        Perform the search with current selections and handle results
        """
        try:
            search_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @aria-label='Consultar por nombre o razón social']"))
            )
            search_button.click()
            
            #time.sleep(5)  # Wait for results
            
            # Handle results...
            self._handle_search_results({
                level.level_name: getattr(self.selection_state, level.level_name)
                for level in SelectionLevel
            })
            
        except Exception as e:
            logging.error(f"Error performing search: {e}")

    def _handle_search_results(self, search_params: Dict[str, str]) -> None:
        """Handle the search results and save them"""
        try:
            modal = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, "//div[@role='dialog' and @aria-modal='true' and @class='v-dialog__content v-dialog__content--active']")
            ))
            
            message = modal.find_element(By.XPATH, "//p[@class='pl-1']").text.strip()
            
            if "no generó resultados" in message:
                logging.info("No results found")
                self._click_back_button()
                return
                
            # Process results...
            self._extract_and_save_results(search_params)
            self._click_back_button()
        
        except TimeoutException:
            # Specific handling for when the modal doesn't appear in time
            logging.error("Timeout waiting for results modal or its content.")
            self._recover_from_error()
        except NoSuchElementException:
            # Handle case where the modal or its content is not found
            logging.error("Modal or its content not found in the DOM.")
            try:
                self._click_back_button()
            except Exception as back_err:
                logging.error(f"Failed to click back button after NoSuchElementException: {back_err}")
                self._recover_from_error()
        except Exception as e:
            logging.error(f"Unexpected error handling results: {e}")
            self._recover_from_error()

    def _click_back_button(self):
        """Click the back button after viewing results"""
        try:
            back_button_xpath = "//button[@type='button' and contains(@class, 'v-btn v-btn--is-elevated v-btn--has-bg theme--dark v-size--default leading')]"
            back_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, back_button_xpath)
            ))
            self.driver.execute_script("arguments[0].click();", back_button)
            #back_button.click()
            
            try:
                modal_xpath = "//div[@role='dialog' and @aria-modal='true' and @class='v-dialog__content v-dialog__content--active']"
                self.wait.until(EC.invisibility_of_element_located((By.XPATH, modal_xpath)))
                logging.debug("Modal dialog became invisible after clicking back.")
            except TimeoutException:
                logging.warning("Modal dialog did not become invisible after clicking back.")
            
        except TimeoutException:
            logging.error("Timeout waiting for the back button to become clickable.")
            # Consider recovery if the back button isn't found/clickable
            self._recover_from_error()
           
        except Exception as e:
            logging.error(f"Error clicking back button: {e}", exc_info=True)

    def _recover_from_error(self):
        """Recover from errors by refreshing the page and reinitializing"""
        try:
            self.driver.get(self.url)
            self._initialize_form()
        except Exception as e:
            logging.error(f"Error recovering from error: {e}")

    def _extract_and_save_results(self, search_params: Dict[str, str]) -> None:
        """Extract results from the table and save them"""
        try:
            table = self.wait.until(EC.presence_of_element_located((By.ID, "ResultadoConsulta")))
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header
            
            results = []
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 5:
                    results.append({
                        'radicado': cols[0].text.strip(),
                        'fecha_radicacion': cols[1].text.strip(),
                        'despacho': cols[2].text.strip(),
                        'clase': cols[3].text.strip(),
                        'sujetos': cols[4].text.strip()
                    })
            
            self.results.append({
                'search_params': search_params,
                'search_name': self.search_name,
                'results': results
            })
            
            self.save_results()  # Save after each successful search
            
        except Exception as e:
            logging.error(f"Error extracting results: {e}")

    def save_results(self, filename="judicial_results.json"):
        """Save the scraped results to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'search_name': self.search_name,
                    'total_results': len(self.results),
                    'results': self.results
                }, f, ensure_ascii=False, indent=2)
            logging.info(f"Results saved to {filename}")
        except Exception as e:
            logging.error(f"Error saving results: {e}")

    def run(self):
        """Main execution method"""
        try:
            self.driver.get(self.url)
            self._initialize_form()
            
            if self.target_department:
                target_dept_index = self._find_and_select_target_department()
                
                if target_dept_index is not None:
                    logging.info(f"Starting navigation from CITY level for selected department.")
                    self._navigate_selection_chain(SelectionLevel.CITY, 1)
                else:
                    logging.error(f"Could not proceed: Target department '{self.target_department}' not found or failed to select.")
                    return
            else:
                logging.info("Starting full navigation chain from DEPARTMENT level.")
                self._navigate_selection_chain(SelectionLevel.DEPARTMENT, 1)
                    
            self.save_results()
        except Exception as e:
            logging.error(f"Error during execution: {e}")
        finally:
            self.close()

    def close(self):
        """Close the browser and clean up resources"""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
                logging.info("Browser closed successfully")
            except Exception as e:
                logging.error(f"Error closing browser: {e}")

def main():
    """Main function to run the scraper"""
    scraper = None
    try:
        logging.info("Starting judicial process scraper")
        search_name = input("Enter the name to search for: ")
        logging.info(f"User entered search name: {search_name}")

        target_dept_input = input("Enter target department (leave blank to scan all): ").strip()
        target_department = target_dept_input if target_dept_input else None
        
        if target_department:
            logging.info(f"Target department specified: {target_department}")
        else:
            logging.info("No target department specified, scanning all.")
        
        scraper = JudicialProcessScraper(search_name, target_department=target_department, headless=False)
        scraper.run()

    except KeyboardInterrupt:
        logging.warning("Scraping interrupted by user")
        if scraper and hasattr(scraper, 'results') and scraper.results:
            scraper.save_results()

    except Exception as e:
        logging.critical(f"Unhandled exception in main: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")

    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()