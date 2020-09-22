import logging
from queue import Queue
import requests
import threading
from bs4 import BeautifulSoup

from LinksCrawler import config

LOGGER = logging.getLogger('Crawler')


class Crawler:
    """
    A class that represent the crawler
    """
    def __init__(self, init_url, thread_count, crawling_depth, logger=LOGGER):
        self.q = Queue()
        self.links_dict = dict()
        self.broken_links = set()
        self.init_url = init_url
        self.thread_count = thread_count
        self.crawling_depth = crawling_depth
        self.logger = logger
        self.initialize_crawler()

    def initialize_crawler(self):
        """
        putting the initial link in the queue
        """
        self.links_dict[self.init_url] = 0
        self.q.put(self.init_url)
        self.logger.info(f"queue initialized with link: {self.init_url}")

    def run(self):
        """
        initlize all threads and return the result
        :return: tuple of dictionary and list
        """
        threads = []
        for i in range(self.thread_count):
            t = threading.Thread(target=self.crwal_thread, name=f"worker {i}")
            t.start()
            threads.append(t)

        self.logger.info("initialized all threads")
        for t in threads:
            t.join()

        self.q.join()
        return self.links_dict, self.broken_links

    def crwal_thread(self):
        """
        take a link from the queue, find its depth, process it
        """
        while True:
            print(threading.active_count())
            url = self.q.get()
            self.logger.info(f'working on url: {url}')
            url_depth = self.links_dict.get(url) + 1
            if url_depth > self.crawling_depth:
                self.logger.info(f'url: {url} is at maximum depth, not working on it')
                break
            self.process_link(url, url_depth)
            self.q.task_done()

    def process_link(self, url, url_depth):
        """
        get all links in the page and if valid and non existent add to dict,
        if broken add to list
        :param url: str
        :param url_depth: int
        """
        try:
            for link in self.get_links(url):
                if self.check_valid(link):
                    link_depth = self.links_dict.get(link, 0)
                    if not link_depth:
                        self.links_dict[link] = url_depth
                        self.q.put(link)
                    elif link_depth > url_depth:
                        self.links_dict[link] = url_depth
                else:
                    self.broken_links.add(link)
        except Exception as e:
            self.logger.warning(f'caught and unexpected exception while processing link: {url}')

    @staticmethod
    def get_links(url):
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


