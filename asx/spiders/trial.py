# -*- coding: utf-8 -*-
import scrapy
import csv
import scrapy_splash
from scrapy_selenium import SeleniumRequest
import re
from scrapy.spiders import CrawlSpider


class TrialSpider(scrapy.Spider):
    name = 'trial'
    # Limit test records
    limit = 2

    def start_requests(self):
        #  Download CSV file
        yield scrapy.Request(url="https://www.asx.com.au/asx/research/ASXListedCompanies.csv", callback=self.parse)

    def parse(self, response):
        # Store CSV file
        filename = 'companies.csv'
        with open(filename, 'wb') as f:
            f.write(response.body)
        self.log('Saved file %s' % filename)

        # Read CSV file
        with open(filename) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                else:
                    # for test only, process company code with TLS
                    if len(row) == 3:
                        if len(row[1]) == 3:
                            if line_count >= self.limit:
                                pass
                            else:
                                self.log('COMPANY ' + row[1])
                                request = scrapy_splash.SplashRequest(
                                    url='https://www.asx.com.au/asx/share-price-research/company/' + row[1],
                                    callback=self.parse_price,
                                    args={
                                        "wait": 10,
                                        'timeout': 1800,
                                        'images': 0,
                                    }

                                )
                                request.meta['code'] = row[1]
                                line_count += 1
                                yield request

    def parse_price(self, response):
        dividens = response.xpath('//td[@class="overview-dividends"]/table//tr')
        json = {}
        json[response.meta['code']] = {
            "summary": {
                "Summary_Value": response.xpath('//span[@ng-show="share.last_price"]/text()').extract_first(),
                "market_cap": response.xpath('//div[@ng-switch="share.market_cap"]/span/text()').extract_first(),
                "dividens": {
                    "most_recent": dividens[0].xpath('td[2]/span//text()').extract_first(),
                    "Dividend ex-date": dividens[1].xpath('td[2]//text()').extract_first(),
                    "Dividend pay date": dividens[2].xpath('td[2]//text()').extract_first(),
                    "Franking": dividens[3].xpath('td[2]//text()').extract_first(),
                    "Annual dividend yield": dividens[4].xpath('td[2]/span//text()').extract_first(),
                }
            }
        }

        request = scrapy_splash.SplashRequest(
            url='https://www.asx.com.au/asx/share-price-research/company/' + response.meta[
                'code'] + '/statistics/shares',
            callback=self.parse_statistic,
            args={
                # optional; parameters passed to Splash HTTP API
                'timeout': 1800,
                "wait": 10,
                'images': 0,
                # 'url' is prefilled from request url
                # 'http_method' is set to 'POST' for POST requests
                # 'body' is set to request body for POST requests
            },
        )
        request.meta['json'] = json
        request.meta['code'] = response.meta['code']

        yield request

    def parse_statistic(self, response):
        res = response.xpath('//table[@class="table-shares key-statistics ng-scope"]//tr')
        response.meta['json'][response.meta['code']]['statistic'] = {
            "statistic": {
                "day": {
                    "open": res[2].xpath('td[2]/span//text()').extract_first(),
                    "day_high": res[3].xpath('td[2]/span//text()').extract_first(),
                    "day_low": res[4].xpath('td[2]/span//text()').extract_first(),
                    "Daily volume": res[5].xpath('td[2]/span//text()').extract_first(),
                    "Bid": res[6].xpath('td[2]/span//text()').extract_first(),
                    "Offer": res[7].xpath('td[2]/span//text()').extract_first(),
                    "Number of shares": res[8].xpath('td[2]/span//text()').extract_first(),
                },
                "year": {
                    "previouse_close": res[2].xpath('td[4]/span//text()').extract_first(),
                    "52_week_high": res[3].xpath('td[4]/span//text()').extract_first(),
                    "52 week low": res[4].xpath('td[4]/span//text()').extract_first(),
                    "Average volume": res[5].xpath('td[4]/span//text()').extract_first(),
                },
                "ratios": {
                    "p/e": res[2].xpath('td[6]/span//text()').extract_first(),
                    "eps": res[3].xpath('td[6]/span//text()').extract_first(),
                    "Annual dividend yield ": res[4].xpath('td[6]/span//text()').extract_first(),
                }
            }

        }

        json = response.meta['json']

        # grab announcement
        request = scrapy.Request(
            url='https://www.asx.com.au/asx/statistics/announcements.do?by=asxCode&asxCode=' + response.meta[
                'code'] + '&timeframe=D&period=M6',
            callback=self.parse_announcement)
        request.meta['json'] = json
        request.meta['code'] = response.meta['code']
        yield request

    def parse_announcement(self, response):
        row = response.xpath('//announcement_data/table/tbody//tr')
        items = []
        for i in row:
            re.sub(r"\s+", " ", i.xpath('td[1]//text()').extract_first())
            items.append({
                "date": re.sub(r"\s+", " ", i.xpath('td[1]//text()').extract_first()),
                "time": i.xpath('td[1]/span//text()').extract_first(),
                "subject": re.sub(r"\s+", " ", i.xpath('td[3]/a//text()').extract_first())
            })
        response.meta['json'][response.meta['code']]['annountcements'] = items;

        yield response.meta['json']
