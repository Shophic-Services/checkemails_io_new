import re
import requests
import requests.exceptions
from urllib.parse import urlsplit
from collections import deque
from bs4 import BeautifulSoup
import pandas as pd

def fetch_emails(starting_url):
    unprocessed_urls = deque([starting_url ])

    # set of already crawled urls for email
    processed_urls = set()

    # a set of fetched emails
    emails = set()

    # process urls one by one from unprocessed_url queue until queue is empty
    while len(unprocessed_urls):

        # move next url from the queue to the set of processed urls
        url = unprocessed_urls.popleft()
        processed_urls.add(url)

        # extract base url to resolve relative links
        parts = urlsplit(url)
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/')+1] if '/' in parts.path else url

        # get url's content
        # print("Crawling URL %s" % url)
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
        # except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
            # ignore pages with errors and continue with next url
            continue

        # extract all email addresses and add them into the resulting set
        # You may edit the regular expression as per your requirement
        new_emails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", response.text, re.I))
        emails.update(new_emails)
        # create a beutiful soup for the html document
        soup = BeautifulSoup(response.text, 'lxml')

        # Once this document is parsed and processed, now find and process all the anchors i.e. linked urls in this document
        for anchor in soup.find_all("a"):
            # extract link url from the anchor
            link = anchor.attrs["href"] if "href" in anchor.attrs else ''
            # resolve relative links (starting with /)
            if link.startswith('/'):
                link = base_url + link
            elif not link.startswith('http'):
                link = path + link
            # add the new url to the queue if it was not in unprocessed list nor in processed list yet
            if not link in unprocessed_urls and not link in processed_urls and link.startswith(base_url) and 'cdn-cgi' not in link and 'tel:' not in link:
                unprocessed_urls.append(link)
    # try:
    #     response = requests.get(url, timeout=10)  # Added timeout parameter
    #     response.raise_for_status()

    #     soup = BeautifulSoup(response.text, 'html.parser')
    #     # Find all email addresses using a regular expression
    #     email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    #     emails = set(re.findall(email_pattern, soup.text))

    return emails

    # except requests.exceptions.RequestException as e:
    #     print(f"Error fetching data from {url}: {e}")
    #     return None

def fetch_emails_bulk(urls):
    results = []

    for url in urls:
        emails = fetch_emails(url)

        if emails:
            result = {"url": url, "emails": emails}
            results.append(result)

    return results

def write_results_to_excel(results, output_file):
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)

# Example usage with an Excel file
input_excel_file = "input_websites.xlsx"
output_excel_file = "output_emails.xlsx"

# Read URLs from Excel
try:
    df_websites = pd.read_excel(input_excel_file, engine='openpyxl')
except pd.errors.EmptyDataError:
    print(f"Error: The input Excel file '{input_excel_file}' is empty.")
    exit()

# Print column names to identify the correct column name
print(df_websites.columns)

# Update the column name according to your Excel file
# Replace 'Website' with the correct column name
websites_to_scrape = df_websites['Website'].tolist()

# Fetch emails
results = fetch_emails_bulk(websites_to_scrape)

# Write results to Excel
write_results_to_excel(results, output_excel_file)

print(f"Emails extracted successfully and saved to '{output_excel_file}'.")
