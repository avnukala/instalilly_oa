from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import requests
from bs4 import BeautifulSoup
import json
import re
from langchain_core.tools import tool


def clean_text(text):
    html = re.compile('<.*?>')
    return re.sub(html, '', text)


def chromedriver_init():
    chrome_options = Options()
    chrome_options.add_argument('--headless') 
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def scrape_qa(driver):
    try: search_box = driver.find_element(By.XPATH, "//input[@placeholder='Search Q&A asked by others']")
    except NoSuchElementException: return None
    search_box.send_keys("install")
    search_box.send_keys(Keys.ENTER)
    time.sleep(0.1)

    try: qna_components = driver.find_elements(By.CLASS_NAME, "qna__question")
    except NoSuchElementException: return None
    data_list = []
    
    if not qna_components:
        return None

    for component in qna_components:
        question = clean_text(component.find_element(By.CLASS_NAME, "js-searchKeys").text.strip())
        answer = clean_text(component.find_element(By.CSS_SELECTOR, ".qna__ps-answer__msg .js-searchKeys").text.strip())
        data = {
            "question": question,
            "answer": answer
        }
        data_list.append(data)

    return data_list


# TODO: May want to add "Other parts used" to this 
def scrape_install_instr(driver):
    try: search_box = driver.find_element(By.XPATH, "//input[@placeholder='Search Installation Instructions left by others']")
    except NoSuchElementException: return None
    search_box.send_keys("install")
    search_box.send_keys(Keys.ENTER)
    time.sleep(0.1)

    try : repair_stories = driver.find_elements(By.CLASS_NAME, "repair-story")
    except NoSuchElementException: return None
    data_list = []

    if not repair_stories:
        return None

    for story in repair_stories:
        title = clean_text(story.find_element(By.CLASS_NAME, "repair-story__title").text.strip())
        instructions = clean_text(story.find_element(By.CLASS_NAME, "repair-story__instruction").text.strip())
        data = {
            "title": title,
            "instructions": instructions
        }
        data_list.append(data)

    return data_list


def search_part_number(part_id):
    driver = chromedriver_init()
    url = 'https://www.partselect.com/'
    driver.get(url)

    search_box = driver.find_element(By.XPATH, '//*[@id="searchboxInput"]')
    button = driver.find_element(By.XPATH, '//button[text()="SEARCH"]')
    search_box.click()
    search_box.send_keys(part_id)
    button.click()
    time.sleep(0.1)

    return driver


@tool
def scrape_part_install(part_id):
    driver = search_part_number(part_id) 
    output = scrape_qa(driver) or scrape_install_instr(driver)
    driver.quit()
    return output


@tool
def scrape_part_info(part_id):
    driver = search_part_number(part_id)
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')

    part_info = {}
    part_info['title'] = clean_text(soup.find('h1', class_='title-lg').text.strip())

    rating_div = soup.find('div', class_='rating')
    if rating_div:
        part_info['rating'] = clean_text(rating_div.find('span', class_='rating__count').text.strip())

    repair_rating_div = soup.find('div', class_='js-RepairRating')
    if repair_rating_div:
        rated_by = clean_text(repair_rating_div.find('p', id='PD_RatedByMsg--mobile').text.strip())
        part_info['rated_by'] = int(rated_by.split()[2])

    price_div = soup.find('div', itemprop='offers')
    if price_div:
        part_info['price'] = clean_text(price_div.find('span', class_='js-partPrice').text.strip())
        part_info['availability'] = clean_text(price_div.find('span', itemprop='availability').text.strip())

    descr_div = soup.find(class_='pd__description pd__wrap mt-3')
    if descr_div:
        part_info['description'] = clean_text(descr_div.get_text().strip())

    return part_info


# TODO, maybe make this dynamic? include the llm here so we can summarize
@tool
def scrape_model_symptoms(model_id):
    url = f'https://www.partselect.com/Models/{model_id}'
    html_content = requests.get(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    all_symptoms = soup.find_all(class_='symptoms__descr')
    symptoms = [clean_text(symptom.get_text()) for symptom in all_symptoms]
    return symptoms


@tool
def solve_model_symptoms(model_id, symptom):
    url = f'https://www.partselect.com/Models/{model_id}'
    driver = chromedriver_init()
    driver.get(url)

    try: symptom_elements = driver.find_elements(By.CSS_SELECTOR, "div.symptoms__descr")
    except NoSuchElementException: return None

    for symptom_element in symptom_elements:
        if symptom_element.text == desired_symptom:
            driver.execute_script("arguments[0].scrollIntoView();", symptom_element)
            show_all_link = symptom_element.find_element(By.XPATH, "./following-sibling::div[@class='symptoms__action']")
            show_all_link.click()
            time.sleep(0.1)
            break

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    parts_list = []
    items = soup.find_all('div', class_='symptoms align-items-center')

    for item in items:
        part_name = clean_text(item.find('a', class_='d-block bold').text.strip())
        part_number = clean_text(item.find('div', class_='text-sm').find('a').text.strip())
        price_currency = clean_text(item.find('span', class_='price__currency').text.strip())
        price_value = clean_text(item.find('div', class_='mega-m__part__price').text.strip().replace(price_currency, ''))

        part_info = {
            'name': part_name,
            'part number': part_number,
            'price': price_currency + price_value
        }

        parts_list.append(part_info)

    return parts_list




# TODO: search installation instructions for model parts 
# Can use llm to distill query into one word to search

# TODO: check compatability of tools -> models and models -> tools

# TODO: general QA e.g. The ice maker on my Whirlpool fridge is not working. How can I fix it?
# Can use general debugging tips on site and ask user for model number 

# TODO: tell customer how to find the model number on their fridge / dishwasher

# TODO: search for parts related to a model number, e.g. i need a new heating element what part do I want
# can do part search from "enter part description"

# TODO: more general queries i.e. what's the typical price for a screw for this model
# what are the dimensions of this washer
# 

# TODO: extract model / part number from noise and format for search as required 

# TODO: function to automatically ask a question about a model / part 

# TODO: last touch, add links to json outputs so users can click