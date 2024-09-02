import os
import bs4 
import pandas as pd
import PyPDF2
from PyPDF2.errors import (
    PdfReadError,
)  # Ensure you're using a version of PyPDF2 that includes this exception
from camelot import read_pdf
import requests
import numpy as np
from bs4 import BeautifulSoup
from numpy import mean

from src.logger import create_logger

fname = os.path.splitext(os.path.basename(__file__))[0]
logger = create_logger(f"{fname}.log")


verified_excel = "scrap/result/apa_programs_licensure.xlsx"
df = pd.read_excel(verified_excel)


# function to save df to an excel file
def save_df_to_excel_result_folder(df: pd.DataFrame, file_name: str) -> None:
    # save the programs to an excel file named "apa_programs.xlsx" in the result folder.
    # If result folder does not exist, create it.
    result_folder = os.path.basename(file_name)
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)

    df.to_excel(file_name, index=False)
    return


# function to read pdf file
def parse_pdf_file(file_name:str) -> tuple:
    tables = []
    format_indicators = 'df'
    try:
        format_indicators = determine_pdf_format(file_name)
        if format_indicators == 'ocr':
            return format_indicators, None
        elif format_indicators == 'df':
            tables = read_pdf(file_name, pages= "all",lattice = True)  # read all tables in the pdf file
            if len(tables) == 0:
                logger.error(f"No tables found in the pdf file {file_name}")
                return format_indicators, None
            else:
                return format_indicators, tables
    except FileNotFoundError:
        logger.error("File not found")
        logger.error(file_name)
    except PdfReadError:
        logger.error("Error reading PDF file.")
        # delete the pdf file if it is not readable
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    return ('', None)

def determine_pdf_format(file_name):
    with open(file_name, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)
        for page_num in range(num_pages):
                # check if the pdf is scanned or not
            if pdf_reader.pages[page_num].extract_text().strip() == "":
                format_indicators = 'ocr'
            else:
                format_indicators = 'df'
    return format_indicators



table_keywords = {
    "Mean number of years to complete" : "time_to_complete",
    "Tuition for full-time students" : "tuition",
    "Students who obtained APA/CPA" : "internship",
    "Students for whom this" : "attrition",
    "Licensure percentage" : "licensure",
}

# find effective tables from the tables scrap from html
def find_effective_html_tables(tables: list):
    effective_tables = dict()
    for table in tables:
        # check if table is a string 
        if isinstance(table, bs4.element.Tag):
            try:
                df = pd.read_html(str(table).replace('%', ''))[0]
            except Exception as e:
                print(f"Failed to convert html table to pandas dataframe: {e}")
                continue
        else:
            df = table.df
        assert isinstance(df, pd.DataFrame)
        # remove the '\n' in the dataframe
        df = df.replace(r'\n','', regex=True)
        for key, title in table_keywords.items():
            if key.replace(' ','') in df.to_string().replace(' ',''):
                effective_tables[title] = df
    return effective_tables

# function to process tables outputed from parse_pdf_file function
def save_tables_txt(tables: dict,file_name:str):
    file_folder = os.path.basename(file_name)
    if not os.path.exists(file_folder):
        os.makedirs(file_folder)
    with open(file_name, "x") as out:
        for title , df in tables.items():
            if df is not None:
                # search for the keywords in the table
                out.write("="*100)
                out.write("\n")
                out.write('title: ')
                out.write(title)
                out.write("\n")
                out.write("="*200)
                out.write("\n")
                # new line for each table            
                out.write(df.to_string())   
                out.write("\n")
                out.write("="*200)
                out.write("\n")

# extract information from the effective tables

def extract_licensure(df: pd.DataFrame):
    info = {}
    for ir, x in enumerate(df.iloc[:,0]):
        if "The total number of program graduates".replace(" ", '') in x.replace(" ", ''):
            total = df.iloc[ir, 1:].to_list()
            total = [y for y in total if y]
            if len(total) == 0:
                print("No result found in the table")
            else:    
                info['lic_total'] = total[-1]
        if "became licensed psychologists".replace(" ", '') in x.replace(" ", ''):
            total = df.iloc[ir, 1:].to_list()
            total = [y for y in total if y]
            if len(total) == 0:
                print("No result found in the table")
            else:
                info['licensed'] = total[-1]
        if "Licensure percentage".replace(" ", '') in x.replace(" ", ''):
            total = df.iloc[ir, 1:].to_list()
            total = [y for y in total if y]
            if len(total) == 0:
                print("No result found in the table")
            else:
                info['licensure_extracted'] = total[-1]
    return info
def extract_time_to_complete(df: pd.DataFrame):
    info = {}
    for ir, x in enumerate(df.iloc[:,0]):
        if "Mean number of years to complete".replace(" ", '') in x.replace(" ", ''):
            years = df.iloc[ir, 1:].to_list()
            years = [y for y in years if y]
            if len(years) == 0:
                print("No years found in the table")
                break
            info['years_long'] = max(years)
            info['years_short'] = min(years)    
            info['years_mean'] = years[-1]
            break
    return info
def extract_tuition(df: pd.DataFrame):
    info = {}
    for ir, x in enumerate(df.iloc[:,0]):
        if "out-of-state" in x.lower():
            fees = df.iloc[ir, 1:].to_list()
            fees = [y for y in fees if y]
            if len(fees) == 0:
                print("No tuition found in the table")
                break
            tuition = fees[-1]
            # if tuition is not precedented by a $ sign, add it
            if "$" not in tuition:
                tuition = "$" + tuition
            info['tuition'] = tuition
            break
    return info
def extract_internship(df: pd.DataFrame):
    info = {}
    for ir, x in enumerate(df.iloc[:,0]):
        if "Students who obtained APA/CPA-accredited internships".replace(" ", '') in x.replace(" ", ''):
            interns = df.iloc[ir, 1:].to_list()
            if isinstance(interns[0], str):
                interns = [y for y in interns if y.isnumeric()]
            if len(interns) == 0:
                print("No internship rate found in the table")
                break
            info['internship_rate_lastest'] = interns[-1]
            break
    return info
def extract_attrition(df: pd.DataFrame):
    info = {}
    for ir, x in enumerate(df.iloc[:,0]):
        if "Students for whom this is the year of first enrollment".replace(" ", '') in x.replace(" ", ''):
            enrollment = df.iloc[ir, 1:].to_list()
            # only keep numeric values
            if isinstance(enrollment[0], str):
                enrollment = [int(y) for y in enrollment if y.isnumeric()]
            if len(enrollment) == 0:
                print("No enrollment found in the table")
                break
            info['enrollment_latest'] = str(enrollment[-1])
            info['enrollment_ave'] = str(mean(enrollment))
        if "Students no longer enrolled for any reason".replace(" ", '') in x.replace(" ", ''):
            attrition = df.iloc[ir, 1:].to_list()
            # only keep numeric values
            if isinstance(attrition[0], str):
                attrition = [int(y) for y in attrition if y.isnumeric()]
            if len(attrition) == 0:
                print("No attrition found in the table")
                break
            info['attrition_rate_high'] = str(max(attrition[1::2]))
            info['attrition_ave'] = str(mean(attrition[::2]))
            info['attrition_latest'] = str(attrition[-1])
    return info

# extract info from effective tables
def extract_effective_tables(tables: dict):
    info = {}
    for title, df in tables.items():
        
        if "licensure" in title.lower():
            try:
                info.update(extract_licensure(df))
            except Exception as e:
                print(f"Failed to extract licensure information: {e}")
        if "time" in title.lower():
            try:
                info.update(extract_time_to_complete(df))
            except Exception as e:
                print(f"Failed to extract time to complete information: {e}")
        if "tuition" in title.lower():
            try:
                info.update(extract_tuition(df))
            except Exception as e:
                print(f"Failed to extract tuition information: {e}")
        if "internship" in title.lower():
            try:
                info.update(extract_internship(df))
            except Exception as e:
                print(f"Failed to extract internship information: {e}")
        if "attrition" in title.lower():
            try:
                info.update(extract_attrition(df))
            except Exception as e:
                print(f"Failed to extract attrition information: {e}")
    return info

def get_table_from_url(url:str, file_name:str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4343.0 Safari/537.36",
    }
    request_timeout = 10
    # try-except block to handle exceptions
    try:
        response = requests.get(
            url, headers=headers, timeout=request_timeout, stream=True  
        )
        if response.status_code == 200:
            print("View info url is valid!")
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all("table")
            return tables
        else:
            print(f"The url is not valid with code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to check url: {e}")
    return False

def main():
    # os.makedirs(os.path.join(f'scrap/materials'), exist_ok=True)
    for index, row in df.iterrows():
        if row["has_pdf"]:
            # define pdf_filename as concatenation of the index, university and city
            # with leading zeros 3 digits
            pdf_filename = os.path.join(
               "scrap",
              "pdfs",
              f"{row['Index']:03d}-{row['University']}-{row['City']}.pdf", 
            )
            print(pdf_filename)
            # assign pdf_filename to the df
            # df.at[index, "pdf_filename"] = pdf_filename
            # check if the pdf file exists
            if not os.path.exists(pdf_filename):
                pdf_filename_short = os.path.join(
                "scrap",
                "pdfs",
                f"{row['Index']:03d}.pdf", 
                )
                if not os.path.exists(pdf_filename_short):
                    print(f"PDF file does not exist: {pdf_filename}")
                    df.at[index, "has_pdf"] = False
                    continue
                
                # rename the pdf file
                os.rename(pdf_filename_short, pdf_filename)

            # parse the pdf file
            format_indicators, tables = parse_pdf_file(pdf_filename)
            if tables:
                # df.at[index, "format_indicators"] = format_indicators
                effective_tables = find_effective_html_tables(tables)
                df.at[index, "pdf_table_found"] = len(effective_tables)
                info = extract_effective_tables(effective_tables)
                # process the tables
                # save_tables_txt(effective_tables, pdf_filename)
                for key, value in info.items():
                    df.at[index, key] = value
    output_excel = "apa_programs_licensure.xlsx"
    save_df_to_excel_result_folder(df, output_excel)
    return

def main_html(txt_file_folder:str):
    excel_file = "scrap/result/apa_programs_licensure.xlsx"
    df = pd.read_excel(excel_file)
    for index, row in df.iterrows():
        if not row['has_pdf']:
            if row['special'] is not np.nan:
                continue
            if row['html_table'] == 1:
                file_name = f"{row['Index']:03d}-{row['University']}-{row['City']}"
                print(f"Processing row {file_name}")
                tables = get_table_from_url(row['info_href'], file_name)
                if tables:
                    effective_tables = find_effective_html_tables(tables)
                    df.at[index, "html_table_found"] = len(effective_tables)
                    info = extract_effective_tables(effective_tables)
                    # process the tables
                    txt_file_path = txt_file_folder + file_name.replace(".pdf", ".txt")
                    save_tables_txt(effective_tables, txt_file_path)
                    for key, value in info.items():
                        df.at[index, key] = value
                # if tables:
                #     df.loc[ind, "special"] = 1
    # save the updated dataframe
    df.to_excel(excel_file, index=False)


# test parse_pdf_file function
def test_parse_pdf_file():
    pdf_filename = os.path.join(
        "scrap",
        "pdfs",
        f"002-National University, Pleasant Hill, CA-John F. Kennedy University Teach-Out-Pleasant Hill.pdf",
    )
    folder_name = f'scrap/materials/{pdf_filename.split('/')[-1][:-4]}'
    format_indicators, tables = parse_pdf_file(pdf_filename)
    # save_grouped_table(form, tables, folder_name)
    print(format_indicators)
    print(tables)
    return 

# function to convert date from string in the format "MM/DD/YYYY" to "YYYY-MM-DD"
def convert_date(date: str) -> str:
    """
    Convert a date string from "MM/DD/YYYY" format to "YYYY-MM-DD" format

    Args:
        date (str): The date string in "MM/DD/YYYY" format

    Returns:
        str: The date string in "YYYY-MM-DD" format
    """
    month, day, year = date.split("/")
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


# function to read excel file to df, change date format and save to a new excel file
def convert_date_in_excel():
    verified_excel = "scrap/result/initial_date.xlsx"
    df = pd.read_excel(verified_excel)
    df["Initial Accreditation Date"] = df["Initial Accreditation Date"].apply(
        convert_date
    )
    save_df_to_excel_result_folder(df, "initial_date_new.xlsx")
    return df

if __name__ == "__main__":
    # test_parse_pdf_file()
    # main()
    txt_file_folder = "scrap/materials/"
    main_html(txt_file_folder)
