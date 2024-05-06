import scrapy


class PartScraperSpider(scrapy.Spider):
    name = 'part_scrape'
    start_urls = [
        # "https://www.partselect.com/Pole-Saw-Models.htm"
        'https://www.partselect.com/Dishwasher-Parts.htm',
        'https://www.partselect.com/Refrigerator-Parts.htm'
    ]

    # main parser for appliance page links, can be configured for "Dishwasher-Parts"
    # to run a complete scrape on all appliance models
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
        
        for link in response.css('a.bold.mb-1.mega-m__part__name::attr(href)'):
            part_url = response.urljoin(link.get())
            yield scrapy.Request(part_url, callback=self.parse_parts_page, meta={'model_number': model_number})
        
        master_id = response.css('[data-model-master-id]::attr(data-model-master-id)').get()
        qa_url = f'{response.url}?currentPage=1&modelMasterID={master_id}&model_number={model_number}&handler=QuestionsAndAnswers&pageSize=5&sortColumn=rating&sortOrder=desc&'
        
        for symptom in response.css('a.symptoms'):
            symptom_title = symptom.css('.symptoms__descr::text').get()
            symptom_link = symptom.css('a.symptoms::attr(href)').get()
            yield response.follow(symptom_link, 
                                  callback=self.parse_model_symptoms, 
                                  meta={
                                      'model_info': model_info.copy(),
                                      'symptom_title': symptom_title
                                      })
        
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
        model_info = response.meta['model_info']
        base_url = response.meta['base_url']
        master_id = response.meta['master_id']
        model_number= model_info['Model Number']
        cur_page = response.meta['cur_page']
        
        if (response.css('.qna__question.js-qnaResponse')):
            for qa in response.css('.qna__question.js-qnaResponse'):
                qa_info = model_info.copy()
                question = qa.css('.js-searchKeys::text').get()
                answer = qa.css('.qna__ps-answer__msg .js-searchKeys::text').get()
                qa_info['Question'] =  question.strip() if question else None, 
                qa_info['Answer'] =  answer.strip() if answer else None
                yield qa_info
                
            next_page_url =  f'{base_url}?currentPage=1&modelMasterID={master_id}&model_number={model_number}&handler=QuestionsAndAnswers&pageSize=5&sortColumn=rating&sortOrder=desc&'
            cur_page += 1
            yield scrapy.Request(next_page_url, 
                                callback=self.parse_model_qa,
                                meta={
                                    'model_info': model_info.copy(),
                                    'base_url': base_url,
                                    'master_id': master_id,
                                    'cur_page': cur_page
                                    }
                                )
    
        
    def parse_model_symptoms(self, response):
        model_info = response.meta['model_info']
        symptom_title = response.meta['symptom_title']
        
        # two different types of symptom pages
        for fix in response.css('.symptoms'):
            symptom_info = model_info.copy()
            sym_fix_rate = fix.css('.symptoms__percent span::text').get()
            # only get info on fixes that are valid more than 15% of the time
            try: is_significant = float(sym_fix_rate[:-1]) > 15
            except ValueError: is_significant = False
            if is_significant:
                pname_redesign = fix.css('.header.bold.d-flex.justify-content-start a::text').get()
                part_name = pname_redesign if pname_redesign else fix.css('a.bold::text').get()
                
                pnum_redesign = fix.css('.bold.text-teal[itemprop="mpn"]::text').get()
                part_number = pnum_redesign if pnum_redesign else fix.css('div.text-sm a::text').get()
                
                purl_redesign = fix.css('.header.bold.d-flex.justify-content-start a::attr(href)').get()
                part_url = purl_redesign if purl_redesign else '/PS11738134-Whirlpool-W10874836-Pantry-End-Cap-Kit-LH-and-RH.htm?SourceCode=22&SearchTerm=MFI2568AES&ModelNum=MFI2568AES'
                repair_guide = fix.css('p.mb-4::text').get()
                solution = {
                    "Appliance Problem": symptom_title,
                    "Problem Fix Rate": sym_fix_rate,
                    "Part Name": part_name,
                    "Manufacturer Part Number": part_number,
                    "Part URL": response.urljoin(part_url) if part_url else None,
                    "Repair Guide": repair_guide
                }
                symptom_info.update(solution)
                yield symptom_info
            

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
            tb_text = replace_text if replace_text else normal_text
            tb += f'{section.css("div.bold.mb-1::text").get()} {tb_text.strip() if tb_text else None}\n'
        
        part_info = {
            'PartSelect Number': ps_number,
            'Manufacturer Part Number': mpn,
            'Manufacturer': manufacturer,
            'Part Name': part_name,
            'Part URL': response.url,
            'Part Price': f'${part_price}' if part_price else None,
            'Rating': rating.strip() if rating else None,
            'Description': description,
            'Troubleshooting': tb if tb else None,
            "Related Model Number": response.meta["model_number"],
            "Valid": "No" if not description else "Yes",
        }
        
        passed_part_info = {
            'PartSelect Number': ps_number,
            'Manufacturer Part Number': mpn,
            'Manufacturer': manufacturer,
            "Related Model Number": response.meta["model_number"],
            'Part Name': part_name,
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
        part_info = response.meta['part_info']
        base_url = response.meta['base_url']
        inv_id = response.meta['inv_id']
        cur_page = response.meta['cur_page']
        if (response.css('.qna__question.js-qnaResponse')):
            for qa in response.css('.qna__question.js-qnaResponse'):
                qa_info = part_info.copy()
                question = qa.css('.js-searchKeys::text').get()
                answer = qa.css('.qna__ps-answer__msg .js-searchKeys::text').get()
                qa_info['Question'] =  question.strip() if question else None, 
                qa_info['Answer'] =  answer.strip() if answer else None
                yield qa_info
                
            next_page_url = f'{base_url}?currentPage={cur_page}&inventoryID={inv_id}&handler=QuestionsAndAnswers&pageSize=10&sortColumn=rating&sortOrder=desc&'
            cur_page += 1
            yield scrapy.Request(next_page_url, 
                                callback=self.parse_parts_qa,
                                meta={
                                    'part_info': part_info.copy(),
                                    'base_url': base_url,
                                    'inv_id': inv_id,
                                    'cur_page': cur_page, 
                                    }
                                )
        