# Web scrapting for APA accredited programs


This script scrapes the APA website to extract information about accredited programs.
It uses **Selenium** to interact with the website and extract the information.

The extracted information includes the program's website, initial accreditation date, city, state, etc.
The script also downloads the disclosure PDF files associated with the programs and saves them locally.
The PDF files can be parsed by `parse_pdf.py`
The script is divided into several functions to perform the following tasks:
- Launch the WebDriver and open the APA website
- Select an option from a multi-select listbox
- Click the search button to display the results
- Switch to a new window
- Switch to the most recent window
- Click on a program link to open a modal window
- Extract program information from the modal window
- Close the modal window
- Check if the URL is valid and process it
- Download the PDF file from the URL and save it locally
- Export the program information to an Excel file