# Judicial Process Scraper

This is a web scraping tool that extracts information about judicial processes from the Colombian Rama Judicial website.

## Requirements

- Python 3.6+
- Chrome browser installed
- Required Python packages (install using `pip install -r requirements.txt`):
  - selenium
  - webdriver-manager

## Setup

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script using Python:

```
python scrape_judicial_processes.py
```

When prompted, enter the name you want to search for.

The script will:
1. Open a Chrome browser window
2. Navigate to the judicial processes search page
3. Systematically try all combinations of search filters
4. Save any results to a JSON file named `judicial_results.json`

## Features

- Iterates through all possible combinations of search parameters
- Implements backtracking to efficiently explore all search options
- Handles errors gracefully
- Saves results with the search parameters that produced them
- Can be interrupted at any time with Ctrl+C and will save partial results

## Notes

- The scraping process can take a long time depending on the number of combinations to try
- The website may implement rate limiting, so the script includes delays between requests
- For headless operation, change `headless=False` to `headless=True` in the script

