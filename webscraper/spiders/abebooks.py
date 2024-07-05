import scrapy
from datetime import datetime
import pandas as pd
from fake_headers import Headers
import random
import time
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.http import HtmlResponse
from twisted.internet.error import TimeoutError, DNSLookupError
from scrapy.core.downloader.handlers.http11 import TunnelError
from scrapy.utils.response import open_in_browser

class AbebooksSpider(scrapy.Spider):
    name = 'abebooks'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'FEED_FORMAT': 'csv',
        'FEED_URI': datetime.now().strftime('%Y_%m_%d__%H_%M') + 'abebooks.csv',
        'RETRY_TIMES': 15,
        'COOKIES_ENABLED': False,
        'FEED_EXPORT_ENCODING': "utf-8",
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 30,
        'DOWNLOAD_DELAY': random.uniform(1, 3),
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
    }

    def __init__(self, url=None, *args, **kwargs):
        super(AbebooksSpider, self).__init__(*args, **kwargs)
        self.url = url

    def start_requests(self):
        df = pd.read_csv(self.url)
        url_list = [i for i in df['url'].tolist() if i.strip() and not i.startswith('#VALUE')]

        for request_url in url_list:
            headers = Headers(browser="chrome", os="win", headers=True).generate()
            self.logger.info(f'Requesting URL: {request_url}')
            yield scrapy.Request(
                url=request_url,
                callback=self.parse,
                headers=headers,
                errback=self.errback_httpbin,
                dont_filter=True
            )

    def parse(self, response):
        self.logger.info(f'Processing URL: {response.url}')
        if isinstance(response, HtmlResponse):
            listings = response.xpath('//li[@data-cy="listing-item"]')
            self.logger.info(f'Found {len(listings)} listings on {response.url}')

            for rank, listing in enumerate(listings[:3]):
                title = listing.xpath('.//span[@data-cy="listing-title"]/text()').get('')
                price = listing.xpath('.//meta[@itemprop="price"]/@content').get('')
                isbn = listing.xpath('.//meta[@itemprop="isbn"]/@content').get('')
                seller_name = listing.xpath('.//a[@data-cy="listing-seller-link"]/text()').get('')
                shipping_cost = listing.xpath('.//span[contains(@id,"item-shipping-price-")]/text()').get('')
                image = listing.xpath('.//div[@data-cy="listing-image"]/img/@src').get('')

                self.logger.info(f'Listing found: {title} - {price} - {isbn} - {seller_name} - {shipping_cost} - {image}')
                yield {
                    'URL': response.url,
                    'Image URL': image,
                    'Product Title': title,
                    'Product Price': price,
                    'Shipping Fee': shipping_cost,
                    'Position': rank + 1,
                    'ISBN': isbn,
                    'Seller Name': seller_name,
                }
        else:
            self.logger.info(f"Non-HTML response received from {response.url}")

    def errback_httpbin(self, failure):
        self.logger.error(repr(failure))
        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error(f'HTTP Error occurred: {response.status} on {response.url}')
        elif failure.check(DNSLookupError):
            request = failure.request
            self.logger.error(f'DNS Lookup Error occurred: {request.url}')
        elif failure.check(TimeoutError):
            request = failure.request
            self.logger.error(f'Timeout Error occurred: {request.url}')
        elif failure.check(TunnelError):
            request = failure.request
            self.logger.error(f'Tunnel Error occurred: {request.url}')
        else:
            self.logger.error(f'Other Error occurred: {failure}')

### Middleware Script (middlewares.py):
```python
import random
from scrapy import signals

class WebscraperSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    def process_start_requests(self, start_requests, spider):
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class WebscraperDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def __init__(self):
        self.proxies = [
            'http://xavigv:ee3ee0580b725494@proxy.packetstream.io:31112'
        ]

    def process_request(self, request, spider):
        proxy = random.choice(self.proxies)
        request.meta['proxy'] = proxy
        spider.logger.info(f'Using proxy: {proxy}')
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.error(f'Error with proxy: {request.meta.get("proxy")}, error: {exception}')
        proxy = random.choice(self.proxies)
        new_request = request.copy()
        new_request.meta['proxy'] = proxy
        new_request.dont_filter = True
        spider.logger.info(f'Retrying {request.url} with proxy: {proxy}')
        return new_request

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
