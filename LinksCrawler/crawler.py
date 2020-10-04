import logging
import time
from queue import Queue
import requests
import threading
import concurrent.futures
from bs4 import BeautifulSoup

from LinksCrawler import config

LOGGER = logging.getLogger('Crawler')


class Crawler:
    """
    A class that represent the crawler
    """
    def __init__(self, init_url, thread_count, crawling_depth, logger=LOGGER):
        self.q = Queue()
        self.url_dict = dict()
        self.broken_links = set()
        self.init_url = init_url
        self.thread_count = thread_count
        self.crawling_depth = crawling_depth
        self.logger = logger
        self._dict_lock = threading.Lock()
        self.initialize_crawler()

    def initialize_crawler(self):
        """
        putting the initial link in the queue
        """
        self.url_dict[self.init_url] = 0
        self.q.put(self.init_url)
        self.logger.info(f"queue initialized with link: {self.init_url}")

    def run(self):
        """
        initlize all threads and return the result
        :return: tuple of dictionary and list
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_count) as executor:

            for i in range(self.thread_count):
                executor.submit(self.crwal_thread)
                time.sleep(3)

        self.q.join()
        return self.url_dict, self.broken_links

    def crwal_thread(self):
        """
        take a link from the queue, find its depth, process it
        """
        while not self.q.empty():

            print(threading.active_count())
            url = self.q.get()
            self.logger.info(f'working on url: {url}')
            url_depth = self.url_dict.get(url)
            self.process_url(url, url_depth)
            self.q.task_done()
            self.logger.info(f"finished working on {url}")

    def process_url(self, url, url_depth):
        """
        get all links in the page and if valid and non existent add to dict,
        if broken add to list
        :param url: str
        :param url_depth: int
        """
        try:
            for new_url in self.get_urls_from_url(url):
                new_url_depth = url_depth + 1
                valid_url = self.check_valid(new_url)
                with self._dict_lock:
                    dict_new_url_depth = self.url_dict.get(new_url, -1)
                    if dict_new_url_depth != -1: # url was already found
                        self.logger.info(f"{new_url} already exists in th dict")
                        if new_url_depth < dict_new_url_depth:
                            self.logger.warning(f"the new depth {new_url_depth} is better than {dict_new_url_depth}, updating")
                            self.url_dict[new_url] = new_url_depth
                        continue

                    elif valid_url:
                        self.url_dict[new_url] = new_url_depth
                        self.logger.info(f"{new_url} was added to the dict with value {new_url_depth}")

                    else:
                        self.broken_links.add(new_url)
                        self.logger.info(f"{new_url} is a broken and was added to the list")

                if new_url_depth < self.crawling_depth and valid_url:
                    self.q.put(new_url)
                    self.logger.info(f"{new_url} was inserted to queue with depth: {new_url_depth}")

        except Exception as e:
            self.logger.warning(f'caught and unexpected exception while processing new_url: {url}')

    @staticmethod
    def get_urls_from_url(url):
        """
        return list of links from given utl
        :param url: str
        :return: list
        """
        response = requests.get(url=url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.startswith('http'):
                if href.startswith('/'):
                    href = url + href
                links.append(href)
        return set(links)


    @staticmethod
    def check_valid(url):
        """
        check if link is broken
        :param url: str
        :return: bool
        """
        response = requests.get(url)
        if response.status_code in config.BAD_STATUS_CODES:
            return False
        return True


