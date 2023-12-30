import os
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

def clean_content(raw_content):
    # Remove HTML tags using regex
    clean_content = re.sub('<.*?>', '', raw_content)

    # Remove newline characters
    clean_content = clean_content.replace('\n', ' ')

    return clean_content

# Define the range of docIDs you want to scrape
start_doc_id = 1
end_doc_id = 7027

# Create a new instance of the Chrome driver
driver = webdriver.Chrome()

for doc_id in range(start_doc_id, end_doc_id + 1):
    # Construct the URL for the current docID
    url = f"http://lebriz.com/pages/doc_View.aspx?docID={doc_id}&lang=TR"

    # Navigate to the URL
    driver.get(url)

    try:
        # Wait for the page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "dov_docPage_lblBody1")))

        # Extract docID from the URL using urlparse and parse_qs
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        doc_id = query_params.get('docID', [None])[0]

        # Create a dictionary to store page content
        page_content = {}

        saved_page_number = 1
        previous_content = set()  # Use a set to store unique content for each page

        # Find the "Next" button outside the loop
        next_button = driver.find_element(By.ID, 'dov_Pager2_butRight')

        # Extract options from the select box
        select_box = driver.find_element(By.ID, 'dov_pager1_drpPage')
        last_page_number = int(select_box.find_elements(By.TAG_NAME, 'option')[-1].get_attribute('value'))

        while saved_page_number < last_page_number:
            try:
                # Extract the content with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # Extract content from the <div align="justify"> element
                div_content = soup.find('div', {'align': 'justify'})

                if div_content:
                    # Extract inner HTML of all child elements within the div
                    raw_content = ''.join(str(child) for child in div_content.children)

                    # Clean the content
                    content = clean_content(raw_content)

                    # Compare with the content of the previous page
                    if content not in previous_content:
                        # Initialize the dictionary entry for the current page number
                        page_content[saved_page_number] = {'url': url, 'content': content}

                        # Update the set of previous content
                        previous_content.add(content)

                        # Extract images from the table with id "dov_docPage_itemtable1"
                        table_content = soup.find('table', {'id': 'dov_docPage_itemtable1'})
                        if table_content:
                            # Extract images from the first td of the table
                            images = table_content.find('td').find_all('img')
                            image_urls = [img['src'] for img in images]

                            # Add image URLs to the dictionary
                            page_content[saved_page_number]['images'] = image_urls

                        saved_page_number += 1

                # Click the "Next" button using Selenium
                next_button.click()

                # Wait for the page to load
                wait.until(EC.presence_of_element_located((By.ID, "dov_docPage_lblBody1")))

            except StaleElementReferenceException:
                # If the element becomes stale, find it again
                next_button = driver.find_element(By.ID, 'dov_Pager2_butRight')
            except Exception as ex:
                print(f"Error during scraping: {ex}")

        # Process the content of the last page after the loop
        last_page_element = soup.find('div', {'align': 'justify'})
        if last_page_element:
            # Extract inner HTML of all child elements within the div
            raw_last_page_content = ''.join(str(child) for child in last_page_element.children)

            # Clean the content
            last_page_content = clean_content(raw_last_page_content)

            if last_page_content not in previous_content:
                # Initialize the dictionary entry for the last page
                page_content[saved_page_number] = {'url': url, 'content': last_page_content}

                # Extract images from the last page
                last_page_table_content = soup.find('table', {'id': 'dov_docPage_itemtable1'})
                if last_page_table_content:
                    # Extract images from the first td of the table
                    last_page_images = last_page_table_content.find('td').find_all('img')
                    last_page_image_urls = [img['src'] for img in last_page_images]

                    # Add image URLs to the dictionary
                    page_content[saved_page_number]['images'] = last_page_image_urls

        # Save the content to a JSON file in the "docs/" folder
        json_file_path = os.path.join(os.getcwd(), 'docs', f"{doc_id}_content.json")
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(page_content, json_file, ensure_ascii=False, indent=2)

        print(f"Content saved to {json_file_path}")

    except NoSuchElementException as e:
        print(f"Error for docID {doc_id}: {e}. Skipping JSON file creation.")
    except Exception as ex:
        print(f"Error for docID {doc_id}: {ex}. Skipping JSON file creation.")

# Close the browser window after scraping all pages
driver.quit()