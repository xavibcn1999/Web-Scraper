# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime
import pandas as pd
from fake_headers import Headers

header = Headers(browser="chrome",  # Generate only Chrome UA
                 os="win",  # Generate only Windows platform
                 headers=True)

class ebay_top3(scrapy.Spider):
    name = 'ebay_top3'
    custom_settings = {
        'CONCURRENT_REQUESTS': 16,
        'FEED_FORMAT': 'csv',
        'FEED_URI': datetime.now().strftime('%Y_%m_%d__%H_%M') + 'ebay.csv',
        'RETRY_TIMES': 15,
        'COOKIES_ENABLED': True,  # Enable cookies to see if it helps
        'FEED_EXPORT_ENCODING': "utf-8"
    }
    headers = {
        'authority': 'www.ebay.com',
        'upgrade-insecure-requests': '1',
        'user-agent': header.generate()['User-Agent'],
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-gpc': '1',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-US,en;q=0.9',
    }

    proxy = 'http://xavigv:ee3ee0580b725494_country-UnitedKingdom@proxy.packetstream.io:31112'

    def __init__(self, url=None, *args, **kwargs):
        super(ebay_top3, self).__init__(*args, **kwargs)
        self.url = url

    def start_requests(self):
        df = pd.read_csv(self.url)
        url_list = [i for i in df['url'].tolist() if i.strip()]

        for request_url in url_list:
            try:
                nkw = request_url.split('_nkw=')[1].split('&')[0]
            except:
                nkw = ''
            yield scrapy.Request(url=request_url, callback=self.parse, headers=self.headers, 
                                 meta={'proxy': self.proxy, 'nkw': nkw})

    def parse(self, response):
        nkw = response.meta['nkw']
        listings = response.xpath('//ul//div[@class="s-item__wrapper clearfix"]')

        for listing in listings:
            if listing.xpath('.//li[contains(@class,"srp-river-answer--REWRITE_START")]').get():
                self.logger.info("Found international sellers separator. Stopping extraction for this URL.")
                break

            link = listing.xpath('.//a/@href').get('')
            title = listing.xpath('.//span[@role="heading"]/text()').get('')
            price = listing.xpath('.//span[@class="s-item__price"]/text()').get('')
            if not price:
                price = listing.xpath('.//span[@class="s-item__price"]/span/text()').get('')

            image = listing.xpath('.//div[contains(@class,"s-item__image")]//img/@src').get('')
            image = image.replace('s-l225.webp', 's-l500.jpg')

            # Multiple XPath expressions for shipping cost
            shipping_cost = listing.xpath('.//span[contains(text(),"postage") or contains(text(),"shipping")]/text()').re_first(r'\+\s?[£$€][\d,.]+')
            if not shipping_cost:
                shipping_cost = listing.xpath('.//span[contains(@class,"s-item__shipping") or contains(@class,"s-item__logisticsCost") or contains(@class,"s-item__freeXDays")]/text()').re_first(r'\+\s?[£$€][\d,.]+')

            try:
                item_number = listing.xpath('.//a/@href').get('').split('/itm/')[1].split('?')[0]
            except:
                item_number = ''

            # Extract seller name
            seller_name = listing.xpath('.//span[@class="s-item__seller-info-text"]//text()').get('')
            if not seller_name:
                seller_name = listing.xpath('.//span[@class="s-item__seller-info"]//text()').get('')

            if seller_name:
                seller_name = seller_name.split('(')[0].strip()
                self.logger.info(f"Extracted seller name: {seller_name}")
            else:
                self.logger.warning(f"Could not extract seller name for listing: {link}")
                with open(f"listing_{item_number}.html", "w") as f:
                    f.write(listing.get())

            item = {
                'URL': response.url,
                'NKW': "'" + nkw,
                'Image URL': image,
                'Product Title': title,
                'Product Price': price,
                'Shipping Fee': shipping_cost,
                'Item Number': "'" + item_number,
                'Seller Name': seller_name,
            }
            yield item
