# Define a class Program to represent an accredited program
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bs4 import BeautifulSoup, Tag
import pandas as pd
from dataclasses import dataclass


# define a new class Program
@dataclass
class Program:
    index: int
    university: str
    program: str
    state: str
    city: str
    status: str
    id_modal: str = ""
    initial_accreditation_date: str = ""
    website: str | None = None
    info_href: str | None = None
    request_code: int | None = None
    has_pdf: bool | None = None

    def __post_init__(self):
        self.university = self.university.replace("/", "_")
        self.pdf_basename = (
            f"{program.index:03d}-{program.university}-{program.city}.pdf"
        )

    def assign_info_href(self, info_href: str | None) -> bool:
        if info_href is None:
            self.info_href = None
            return False
        else:
            # remove substrings before https:// or http:// in the info_href
            if "http://" in info_href:
                self.info_href = info_href[info_href.index("http://") :]
                return True
            elif "https://" in info_href:
                self.info_href = info_href[info_href.index("https://") :]
                return True
            else:
                self.info_href = None
                return False

    # method to convert the object to a pd.Series
    def to_series(self) -> pd.Series:
        return pd.Series(
            {
                "Index": self.index,
                "University": self.university,
                "Program": self.program,
                "State": self.state,
                "City": self.city,
                "Status": self.status,
                "Initial Accreditation Date": self.initial_accreditation_date,
                "website": self.website,
                "info_href": self.info_href,
                "request_code": self.request_code,
                "has_pdf": self.has_pdf,
                "pdf_basename": self.pdf_basename,
            }
        )


"""
Parse APA credit website to extract program information
"""
CLASS_TABLE = "table customtableidentifier cf"


def parse_programs(html: str) -> list[Program]:
    soup = BeautifulSoup(html, "html.parser")
    programs = parse_soup(soup)
    return programs


def parse_soup(soup: BeautifulSoup) -> list[Program]:
    """
    Extract program information from the BeautifulSoup object

    Args:
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML content

    Returns:
        list: A list of Program objects representing the accredited programs
    """
    programs = []
    table = soup.find("table", class_=CLASS_TABLE)
    if table is not None:
        rows = table.find_all("tr")[1:]  # type: ignore # Skip the header row
    else:
        rows = []

    for ind, row in enumerate(rows):
        columns = row.find_all("td")
        state = columns[0].get_text().strip()
        university = columns[1].get_text().strip()
        city = columns[2].get_text().strip()
        if isinstance(columns[3], Tag):
            program = columns[3].get_text().strip()
        else:
            program = ""
        # extract the id attribute from columns[3] tag "a"
        id_modal = columns[3].find("a")["id"]
        status = columns[4].get_text().strip()
        program = Program(ind, university, program, state, city, status, id_modal)
        programs.append(program)
    return programs


def test(html_file: str) -> list[Program]:
    with open(html_file, "r") as f:
        programs = parse_programs(f.read())
    return programs


if __name__ == "__main__":
    html_file = "assets/html/accredited-programs.html"
    programs = test(html_file)
    for program in programs:
        print(program)
