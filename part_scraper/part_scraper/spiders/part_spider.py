import scrapy

class PartScraperSpider(scrapy.Spider):
    name = 'part_scrape'
    start_urls = [
        # "https://www.partselect.com/Pole-Saw-Models.htm"
        # 'https://www.partselect.com/Dishwasher-Models.htm',
        'https://www.partselect.com/Refrigerator-Models.htm'
    ]


    def parse(self, response):
        for link in response.css('a[href*="/Models/"]'):
            url = response.urljoin(link.attrib['href'])
            model_name = link.css('::text').get().strip() 
            yield scrapy.Request(url, callback=self.parse_model_urls, meta={'model_name': model_name})

        next_page_url = response.css('li.next a::attr(href)').extract_first()
        if next_page_url:
            yield response.follow(next_page_url, callback=self.parse)
    
    
    def parse_model_urls(self, response):
        model_name = response.meta['model_name']
        model_number = model_name.split()[0].strip()
        
        model_info = {
            'Model Name': model_name,
            'Model Number': model_number,
            "Model URL": response.url,
        }
        
        # for link in response.css('a.bold.mb-1.mega-m__part__name::attr(href)'):
        #     part_url = response.urljoin(link.get())
        #     yield scrapy.Request(part_url, callback=self.parse_parts_page)
        
        master_id = response.css('[data-model-master-id]::attr(data-model-master-id)').get()
        qa_url = f'{response.url}?currentPage=1&modelMasterID={master_id}&model_number={model_number}&handler=QuestionsAndAnswers&pageSize=5&sortColumn=rating&sortOrder=desc&'
        
        for symptom_url in response.css('a.symptoms::attr(href)').getall():
            yield response.follow(symptom_url, callback=self.parse_model_symptoms, meta={'model_info': model_info.copy()})
        
        yield scrapy.Request(qa_url, 
                            callback=self.parse_model_qa,
                            meta={
                                'model_info': model_info.copy(),
                                'base_url': response.url,
                                'master_id': master_id,
                                'cur_page': 1
                                }
                            )
            
    def parse_model_qa(self, response):
        orig_info = response.meta['model_info']
        model_info = response.meta['model_info']
        base_url = response.meta['base_url']
        master_id = response.meta['master_id']
        model_number= model_info['Model Number']
        cur_page = response.meta['cur_page']
        model_info["Questions and Answers"] = []
        if (response.css('.qna__question.js-qnaResponse')):
            for qa in response.css('.qna__question.js-qnaResponse'):
                question = qa.css('.js-searchKeys::text').get()
                answer = qa.css('.qna__ps-answer__msg .js-searchKeys::text').get()
                model_info['Questions and Answers'].append({
                    'Question': question.strip() if question else None, 
                    'Answer': answer.strip() if answer else None}
                )
            next_page_url =  f'{base_url}?currentPage=1&modelMasterID={master_id}&model_number={model_number}&handler=QuestionsAndAnswers&pageSize=5&sortColumn=rating&sortOrder=desc&'
            cur_page += 1
            yield model_info
            yield scrapy.Request(next_page_url, 
                                callback=self.parse_model_qa,
                                meta={
                                    'model_info': orig_info.copy(),
                                    'base_url': base_url,
                                    'master_id': master_id,
                                    'cur_page': cur_page
                                    }
                                )
    
        
    def parse_model_symptoms(self, response):
        model_info = response.meta['model_info']
        symptom_title = response.css('main div.bold.mb-2::text').get()
        model_info[symptom_title] = []
        for fix in response.css('.symptoms'):
            sym_fix_rate = fix.css('.symptoms__percent span::text').get()
            part_name = fix.css('a.bold::text').get()
            part_number = fix.css('div.text-sm a::text').get()
            solution = {
                "Symptom Fix Rate": sym_fix_rate,
                "Part Name": part_name,
                "Part Number": part_number
            }
            model_info[symptom_title].append(solution)
        yield model_info
            

    def parse_parts_page(self, response):
        part_name = response.css('h1.title-lg.mt-1.mb-3[itemprop="name"]::text').get()
        part_price = response.css('span.price.pd__price span.js-partPrice::text').get()
        ps_number = response.css('span[itemprop="productID"]::text').get()
        mpn = response.css('span[itemprop="mpn"]::text').get()
        manufacturer = response.css('span[itemprop="brand"] span[itemprop="name"]::text').get()
        description = response.css('div.pd__description.pd__wrap.mt-3 [itemprop="description"]::text').get()
        rating = response.css('.pd__cust-review__header__rating__chart--border::text').get()
        tb = ''
        for section in response.css('div.pd__wrap.row').css('div.col-md-6.mt-3'):
            replace_text = section.css('div[data-collapse-container]::text').get()
            normal_text = section.css("::text").extract()[-1]
            tb_text = normal_text if normal_text else replace_text
            tb += f'{section.css("div.bold.mb-1::text").get()}\n{tb_text.strip() if tb_text else None}\n\n'
        
        part_info = {
            'PartSelect Number': ps_number,
            'Manufacturer Part Number': mpn,
            'Manufacturer': manufacturer,
            'Part Name': part_name,
            'Part URL': response.url,
            'Part Price': f'${part_price}' if part_price else None,
            'Rating': rating.strip() if rating else None,
            'Product Description': description,
            'Troubleshooting': tb if tb else None,
            "Availability": "No Longer Available" if not description else "Available",
        }
        
        passed_part_info = {
            'PartSelect Number': ps_number,
            'Manufacturer Part Number': mpn,
            'Manufacturer': manufacturer,
            'Part Name': part_name,
            'Part URL': response.url,
            "Questions and Answers": [],
        }
        
        yield part_info
        
        inv_id = response.css('div#main::attr(data-inventory-id)').get() 
        base_url = response.url.split('?')[0]
        qa_url = f'{base_url}?currentPage=1&inventoryID={inv_id}&handler=QuestionsAndAnswers&pageSize=10&sortColumn=rating&sortOrder=desc&'
        yield scrapy.Request(qa_url, 
                             callback=self.parse_parts_qa,
                             meta={
                                 'part_info': passed_part_info.copy(),
                                 'base_url': base_url,
                                 'inv_id': inv_id if inv_id else 0,
                                 'cur_page': 1,
                                 }
                            )


    def parse_parts_qa(self, response):
        orig_info = response.meta['part_info']
        part_info = response.meta['part_info']
        base_url = response.meta['base_url']
        inv_id = response.meta['inv_id']
        cur_page = response.meta['cur_page']
        if (response.css('.qna__question.js-qnaResponse')):
            for qa in response.css('.qna__question.js-qnaResponse'):
                question = qa.css('.js-searchKeys::text').get()
                answer = qa.css('.qna__ps-answer__msg .js-searchKeys::text').get()
                part_info['Questions and Answers'].append({
                    'Question': question.strip() if question else None, 
                    'Answer': answer.strip() if answer else None}
                )
                
            
            next_page_url = f'{base_url}?currentPage={cur_page}&inventoryID={inv_id}&handler=QuestionsAndAnswers&pageSize=10&sortColumn=rating&sortOrder=desc&'
            cur_page += 1
            yield part_info
            yield scrapy.Request(next_page_url, 
                                callback=self.parse_parts_qa,
                                meta={
                                    'part_info': orig_info.copy(),
                                    'base_url': base_url,
                                    'inv_id': inv_id,
                                    'cur_page': cur_page, 
                                    }
                                )
        