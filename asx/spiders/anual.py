# -*- coding: utf-8 -*-
import scrapy
import scrapy_splash
import csv
from selenium import webdriver, common
import re

chromeOptions = webdriver.ChromeOptions()
prefs = {'profile.managed_default_content_settings.images': 2}
chromeOptions.add_experimental_option("prefs", prefs)


class AnualSpider(scrapy.Spider):
    name = 'anual'
    allowed_domains = ['asx.com.au']
    limit = 2
    rotate_user_agent = True

    def __init__(self):
        self.driver = webdriver.Chrome(chrome_options=chromeOptions)

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
                                request = scrapy.Request(
                                    url='https://www.asx.com.au/asx/share-price-research/company/' + row[1],
                                    callback=self.parse_price
                                )
                                request.meta['code'] = row[1]
                                line_count += 1
                                yield request

    def parse_price(self, response):
        self.driver.get(response.url)
        json = {}

        try:
            json[response.meta['code']] = {
                "summary": {
                    "Summary_Value": self.driver.find_element_by_xpath('//span[@ng-show="share.last_price"]').text,
                    "market_cap": self.driver.find_element_by_xpath('//div[@ng-switch="share.market_cap"]/span').text,
                    "dividens": {
                        "most_recent": self.driver.find_element_by_xpath(
                            '//company-summary/table/tbody/tr[3]/td[2]/table/tbody/tr[1]/td[2]/span[1]').text,
                        "Dividend ex-date": self.driver.find_element_by_xpath(
                            '//company-summary/table/tbody/tr[3]/td[2]/table/tbody/tr[2]/td[2]').text,
                        "Dividend pay date": self.driver.find_element_by_xpath(
                            '//company-summary/table/tbody/tr[3]/td[2]/table/tbody/tr[3]/td[2]').text,
                        "Franking": self.driver.find_element_by_xpath(
                            '//company-summary/table/tbody/tr[3]/td[2]/table/tbody/tr[4]/td[2]').text,
                        "Annual dividend yield": self.driver.find_element_by_xpath(
                            '//company-summary/table/tbody/tr[3]/td[2]/table/tbody/tr[5]/td[2]/span[1]').text,
                    },
                }
            }
        except:
            self.logger.error('Error while get summary for company : ' + response.meta['code'])
            json[response.meta['code']] = {
                "summary": {

                }
            }

        # Anual PDF

        try:
            self.driver.find_element_by_xpath('//div[@ng-show="annual_reports.length > 0"]/ul/li/a').click()
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # check if submit agreement
            if ".pdf" in self.driver.current_url:
                json[response.meta['code']]['summary']['annual_pdf_link'] = self.driver.current_url;
            else:
                self.driver.find_element_by_name('showAnnouncementPDFForm').submit()
                json[response.meta['code']]['summary']['annual_pdf_link'] = self.driver.current_url;

            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
        except:
            windows = self.driver.window_handles
            json[response.meta['code']]['summary']['annual_pdf_link'] = None;
            self.driver.switch_to.window(windows[0])

        request = scrapy.Request(
            url='https://www.asx.com.au/asx/share-price-research/company/' + response.meta[
                'code'] + '/statistics/shares',
            callback=self.parse_statistic,
        )
        request.meta['json'] = json
        request.meta['code'] = response.meta['code']

        yield request

    def parse_statistic(self, response):
        self.driver.get(response.url)

        try:
            response.meta['json'][response.meta['code']]['statistic'] = {
                "day": {
                    "open": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[3]/td[2]/span').text,
                    "day_high": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[4]/td[2]/span').text,
                    "day_low": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[5]/td[2]/span').text,
                    "Daily volume": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[6]/td[2]/span').text,
                    "Bid": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[7]/td[2]/span').text,
                    "Offer": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[8]/td[2]/span').text,
                    "Number of shares": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[9]/td[2]/span').text,
                },
                "year": {
                    "previouse_close": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[3]/td[4]/span').text,
                    "52_week_high": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[4]/td[4]/span').text,
                    "52 week low": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[5]/td[4]/span').text,
                    "Average volume": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[6]/td[4]/span').text,
                },
                "ratios": {
                    "p/e": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[3]/td[6]/span').text,
                    "eps": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[4]/td[6]/span').text,
                    "Annual dividend yield ": self.driver.find_element_by_xpath(
                        '/html/body/section[3]/article/div[1]/div/div/div[4]/div/div[3]/table/tbody/tr[5]/td[6]/span').text,
                }

            }
        except:
            self.logger.error('Error while get statistic for company : ' + response.meta['code'])
            response.meta['json'][response.meta['code']]['statistic'] = dict()

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
        self.driver.get(response.url)
        row = self.driver.find_elements_by_xpath('//announcement_data/table/tbody//tr')
        self.log(row)

        items = []
        for i in row:
            try:
                i.find_element_by_xpath('td[3]/a').click()
                date = re.sub(r"\s+", " ", i.find_element_by_xpath('td[1]').text);
                time = i.find_element_by_xpath('td[1]/span').text
                subject = re.sub(r"\s+", " ", i.find_element_by_xpath('td[3]/a').text)

                self.driver.switch_to.window(self.driver.window_handles[-1])
                # check if submit agreement
                if ".pdf" in self.driver.current_url:
                    items.append({
                        "date": date,
                        "time": time,
                        "subject": subject,
                        "link": self.driver.current_url
                    })
                else:
                    self.driver.find_element_by_name('showAnnouncementPDFForm').submit()
                    items.append({
                        "date": date,
                        "time": time,
                        "subject": subject,
                        "link": self.driver.current_url
                    })
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

            except:
                self.logger.error('Error while get announcement file for company : ' + response.meta['code'])
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

            response.meta['json'][response.meta['code']]['annountcements'] = items;

        yield response.meta['json']
