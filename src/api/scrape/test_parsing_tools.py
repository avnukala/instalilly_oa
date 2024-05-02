from parsing_tools import *
import time

# simple tests for parsing tools
driver = chromedriver_init()
        
# test search part number
start_time = time.time()
driver = search_part_number(driver, "PS11752778")
url = driver.current_url
print(f'Part URL: {url}')
print(f'Time: {time.time() - start_time}')

# test scrape part info
start_time = time.time()
parts_desc = scrape_part_info(driver, "PS11752778")
print(f'Part description: {parts_desc}')
print(f'Time: {time.time() - start_time}')

# test part install instructions
start_time = time.time()
install_data = scrape_install_instr(driver)
print(f'Part Install: {install_data}')
print(f'Time: {time.time() - start_time}')

# test scrape part Q/A
start_time = time.time()
qa_data = scrape_qa(driver)
print(f'Part QA: {qa_data}')
print(f'Time: {time.time() - start_time}')

# test scrape part info
start_time = time.time()
part_info = scrape_qa(driver)
print(f'Part info: {part_info}')
print(f'Time: {time.time() - start_time}')

# test scrape model symptoms
start_time = time.time()
symptoms = scrape_model_symptoms('WDT780SAEM1')
print(f'Model Symptoms: {symptoms}')
print(f'Time: {time.time() - start_time}')

# test find sol to model symptoms
start_time = time.time()
parts_list = solve_model_symptoms(driver, 'WDT780SAEM1', symptoms[0])
print(f'Solution Parts: {parts_list}')
print(f'Time: {time.time() - start_time}')

