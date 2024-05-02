from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
import time
import requests
from bs4 import BeautifulSoup
import re
from langchain_core.tools import tool
from .args_schema import PartSearch, ModelSearch, SymptomSearch


def clean_text(text):
    html = re.compile('<.*?>')
    return re.sub(html, '', text)


def chromedriver_init():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)
    return driver


main_driver = chromedriver_init()


def scrape_qa(driver):
    driver.refresh()
    try: search_box = driver.find_element(By.XPATH, "//input[@placeholder='Search Q&A asked by others']")
    except NoSuchElementException: return None
    search_box.send_keys("install")
    search_box.send_keys(Keys.ENTER)
    time.sleep(0.5)

    try: qna_components = driver.find_elements(By.CLASS_NAME, "qna__question")
    except NoSuchElementException: return None
    data_list = []
    if not qna_components:
        return None

    for component in qna_components:
        qa = component.find_elements(By.CLASS_NAME, "js-searchKeys")
        question = clean_text(qa[0].text.strip())
        answer = clean_text(qa[1].text.strip())
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
    time.sleep(0.5)

    try : repair_stories = driver.find_elements(By.CLASS_NAME, "repair-story")
    except NoSuchElementException: return None
    data_list = []

    if not repair_stories:
        return None
        #### TODO : Sort by most helpful
    for story in repair_stories:
        title = clean_text(story.find_element(By.CLASS_NAME, "repair-story__title").text.strip())
        instructions = clean_text(story.find_element(By.CLASS_NAME, "repair-story__instruction").text.strip())
        data = {
            "title": title,
            "instructions": instructions
        }
        data_list.append(data)

    return data_list


def search_part_number(driver, part_id):
    url = 'https://www.partselect.com/'
    driver.get(url)

    driver.implicitly_wait(5)
    search_box = driver.find_element(By.XPATH, "//input[@placeholder='Search model or part number']")
    search_box.click()
    search_box.send_keys(part_id)
    search_box.send_keys(Keys.ENTER)

    return driver


@tool("get part install instructions", args_schema=PartSearch)
def scrape_part_install(part_id: str) -> str:
    """Provide the user with installation instructions for a certain
    part given the part ID. """
    driver = search_part_number(main_driver, part_id) 
    output = scrape_qa(driver) or scrape_install_instr(driver)
    return output


@tool("get part information", args_schema=PartSearch)
def scrape_part_info(part_id: str) -> str:
    """Provide the user with information related to the part if given
    the part ID. """
    driver = search_part_number(main_driver, part_id)
    html_content = requests.get(driver.current_url).content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    title = soup.find("h1", class_="title-lg mt-1 mb-3", itemprop="name")
    print(title)
    # title = soup.find("h1", class_="title-lg mt-1 mb-3")
    title = clean_text(title.text.strip()) if title else ""
    
    price_currency = soup.find('span', class_='price__currency')
    price_currency = clean_text(price_currency.text.strip()) if price_currency else ""
    
    price_value = soup.find('span', class_='js-partPrice')
    price_value = clean_text(price_value.text.strip()) if price_value else "NO PRICE AVAILABLE"
    
    part_id = soup.find("span", class_="bold text-teal", itemprop="mpn")
    part_id = clean_text(part_id.text.strip()) if part_id else "NO PART ID AVAILABLE"
    
    # manufacturer = soup.find("span", class_="bold text-teal", itemprop="brand", itemprop="name")
    # part_id = clean_text(manufacturer.text.strip()) if manufacturer else "Unknown"
    
    description = soup.find("div", class_="pd__description", itemprop="description")
    description = clean_text(description.text.strip()) if description else ""

    part_info = {
        'title': title,
        'description': description,
        'part id': part_id,
        'price': price_currency + price_value
    }

    return part_info


@tool("generate list of possible appliance symptoms to select from", args_schema=ModelSearch)
def scrape_model_symptoms(model_id: str) -> str:
    """When a user asks how they can fix their model of refridgerator or 
    dishwasher, given the model ID, provide the user with a list of possible
    symptoms. """
    url = f'https://www.partselect.com/Models/{model_id}/'
    html = requests.get(url)
    if html:
        soup = BeautifulSoup(html.content, 'html.parser')
        all_symptoms = soup.find_all(class_='symptoms__descr')
        symptoms = [clean_text(symptom.get_text()) for symptom in all_symptoms]
        return symptoms
    return "No solutions found"


@tool("solve fridge / dishwasher symptoms", args_schema=SymptomSearch)
def solve_model_symptoms(model_id: str, symptom: str) -> str:
    """Given a specific model symptom and a fridge/dishwasher model ID,
    find parts to help solve the users issues. """
    url = f'https://www.partselect.com/Models/{model_id}'

    driver = main_driver.get(url)

    try: symptom_elements = driver.find_elements(By.CLASS_NAME, "symptoms")
    except NoSuchElementException: return None

    for symptom_element in symptom_elements:
        cur_sympt = symptom_element.find_element(By.CLASS_NAME, "symptoms__descr")
        if cur_sympt.text.strip() == symptom:
            cur_sympt.click()
            break

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    parts_list = []
    items = soup.find_all('div', class_='symptoms')

    # top 10 items
    for item in items[:10]:
        part_name = item.find('div', class_='header').find('a')
        part_name = clean_text(part_name.text.strip()) if part_name else ""
        
        sympt_fix_perc = item.find('div', class_='symptoms__percent')
        sympt_fix_perc = clean_text(sympt_fix_perc.text.strip()) if sympt_fix_perc else ""
        
        part_id = item.find("div", class_="mb-2 bold").find("span", itemprop="mpn")
        part_id = clean_text(part_id.text.strip()) if part_id else "NO PART ID AVAILABLE"
        
        price_currency = item.find('span', class_='price__currency')
        price_currency = clean_text(price_currency.text.strip()) if price_currency else ""
        price_value = item.find('span', class_='js-partPrice')
        price_value = clean_text(price_value.text.strip()) if price_value else "NO PRICE AVAILABLE"

        part_info = {
            'name': part_name,
            'symptom fix percentage': sympt_fix_perc,
            'part id': part_id,
            'price': price_currency + price_value
        }

        parts_list.append(part_info)

    return parts_list


@tool("determine if an id is a model or part number")


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
