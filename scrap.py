# Description: This script scrapes the APA website to extract information about accredited programs.
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
from selenium.common import exceptions

# local imports
from src.common import Program, parse_programs
from src.logger import create_logger

fname = os.path.splitext(os.path.basename(__file__))[0]
logger = create_logger(f"{fname}.log")
APA_URL = "https://accreditation.apa.org/accredited-programs"
SELECT_LISTBOX = "ctl00_DefaultContentPlaceHolder_ListBox2"
SELECT_OPTION = "Psy.D."
ID_SEARCH_BUTTON = "ctl00_DefaultContentPlaceHolder_btnSearch"
ID_WEBSITE = "ctl00_DefaultContentPlaceHolder_hlWebsite"
ID_INITIAL_ACCREDITATION_DATE = "ctl00_DefaultContentPlaceHolder_lblAccredDate"


def lanuch_driver(APA_URL) -> webdriver.Chrome:
    # Initialize the WebDriver (e.g., for Chrome)
    driver = webdriver.Chrome()

    # Open the APA website
    driver.get(APA_URL)

    # Wait for the page to load
    start_search = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.LINK_TEXT, "Start Your Search")
        )  # Replace with actual link text or other locator
    )

    # Click the "Start Your Search" button
    start_search.click()
    return driver


def select_option(driver: webdriver.Chrome, select_id: str, option: str) -> Select:
    # Step 1: Locate the multi-select listbox
    select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.ID, select_id)
        )  # Replace with the actual ID or locator of the listbox
    )

    select = Select(select_element)
    # Step 3: Select an option by value
    select.deselect_all()
    select.select_by_value(option)  # Replace with the actual value attribute
    return select


def click_search_button(driver: webdriver.Chrome) -> str:
    search = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, ID_SEARCH_BUTTON))
    )
    search.click()
    time.sleep(2)
    return driver.page_source


def switch_to_new_window(driver: webdriver.Chrome) -> None:
    original_window = driver.current_window_handle
    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

    # Switch to the new window
    for window_handle in driver.window_handles:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break


# switch to the most recent window
def switch_to_recent_window(driver: webdriver.Chrome) -> None:
    driver.switch_to.window(driver.window_handles[-1])


# click on the program link to open the modal window
def open_modal(driver: webdriver.Chrome, id_modal: str) -> None:
    # Find the program link by id
    program_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, id_modal))
    )
    program_link.click()
    time.sleep(2)


# extract the program information (website, address, info) from the modal window
def extract_program_info(driver: webdriver.Chrome, program: Program) -> Program:
    open_modal(driver, program.id_modal)
    try:
        # Find the elements containing the program information
        extract_program_website(driver, program)
        extract_view_info_link(driver, program)
        extract_initial_accreditation_date(driver, program)
    except exceptions.TimeoutException:
        print("The element 'View Info' was not found.")
    # Extract the text content of the elements
    finally:
        close_modal(driver)
    return program


def extract_program_website(driver: webdriver.Chrome, program: Program):
    website_element = driver.find_element(By.ID, ID_WEBSITE)
    website = website_element.get_attribute("href")
    program.website = website


def extract_view_info_link(driver: webdriver.Chrome, program: Program):
    view_info = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "View Info"))
    )
    # Proceed with actions on view_info
    info_href = view_info.get_attribute("href")
    program.assign_info_href(info_href)


# Extract initial accreditation date from the html table
def extract_initial_accreditation_date(
    driver: webdriver.Chrome, program: Program
) -> Program:
    initial_accreditation_date = driver.find_element(
        By.ID, ID_INITIAL_ACCREDITATION_DATE
    ).text
    program.initial_accreditation_date = initial_accreditation_date
    return program


# Close the modal window
def close_modal(driver: webdriver.Chrome) -> None:
    # find element in driver that has the class of modal-footer
    modal_footer = driver.find_element(By.CLASS_NAME, "modal-footer")
    try:
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                modal_footer.find_element(By.CLASS_NAME, "btn.btn-default")
            )
        )
        close_button.click()
    except exceptions.TimeoutException:
        logger.error("Element not clickable after waiting")
    time.sleep(1)
    return


# detect which the recent window is valid
def check_and_process_url(pdf_save_folder_path: str, program: Program) -> None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4343.0 Safari/537.36",
    }
    request_timeout = 10
    # try-except block to handle exceptions
    try:
        response = requests.get(
            program.info_href, headers=headers, timeout=request_timeout, stream=True  # type: ignore
        )
        program.request_code = response.status_code
        if program.request_code == 200:
            logger.info("View info url is valid!")
            pdf_filename = os.path.join(
                pdf_save_folder_path,
                program.pdf_basename,
            )
            program.has_pdf = download_pdf(response, pdf_filename)
        else:
            program.has_pdf = False
            logger.warning(f"The url is not valid with code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to check url: {e}")
        program.has_pdf = False
    return


# download the pdf file from the url and save it to the local folder\
def download_pdf(response: requests.Response, filename: str) -> bool:
    try:
        response.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"PDF downloaded successfully and saved as {filename}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download PDF: {e}")
        return False


def export_programs_to_excel(programs: list[Program], excel_file_path: str) -> None:
    df = pd.DataFrame([program.to_series() for program in programs])
    # save the programs to an excel file named "apa_programs.xlsx" in the result folder.
    # If result folder does not exist, create it.
    result_folder = os.path.basename(excel_file_path)
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)
    df.to_excel(excel_file_path, index=False)
    return


def test_driver():
    driver = lanuch_driver(APA_URL)
    switch_to_new_window(driver)
    select_option(driver, SELECT_LISTBOX, SELECT_OPTION)
    click_search_button(driver)
    # Extract program information from the HTML content using parse_programs
    programs = parse_programs(driver.page_source)
    return driver, programs


def main(excel_file_path: str, pdf_save_folder_path: str):
    driver = lanuch_driver(APA_URL)
    switch_to_new_window(driver)
    select_option(driver, SELECT_LISTBOX, SELECT_OPTION)
    click_search_button(driver)
    # Extract program information from the HTML content using parse_programs
    programs = parse_programs(driver.page_source)
    # check pdf_save_folder_path exists
    if not os.path.exists(pdf_save_folder_path):
        os.makedirs(pdf_save_folder_path)
    for program in programs[10:]:
        logger.info(program)
        extract_program_info(driver, program)
        if program.info_href:
            check_and_process_url(pdf_save_folder_path, program)
    export_programs_to_excel(programs, excel_file_path)
    driver.quit()
    return


if __name__ == "__main__":
    excel_file_path = "results/apa_programs_raw.xlsx"
    pdf_save_folder_path = "assets/pdfs"
    main(excel_file_path, pdf_save_folder_path)
