# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

    
class DuplicatesPipeline:
    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        model_number = adapter.get("Model Number", None)
        part_number = adapter.get("Manufacturer Part Number", None)
        
        if model_number is not None:
            identifier = model_number
        elif part_number is not None:
            identifier = part_number
        else:
            return item

        if identifier in self.ids_seen:
            raise DropItem(f"Duplicate item found")
        else:
            self.ids_seen.add(identifier)
            return item