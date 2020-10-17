import logging
from queue import Queue, Empty
import requests
import threading
import concurrent.futures
from bs4 import BeautifulSoup
from typing import Tuple, Dict, Set

from LinksCrawler import config

LOGGER = logging.getLogger('Crawler')


class URLD:
    """
    Info holder class to prevent additional access to the url-depth dict while extracting a link from the queue
    """
    def __init__(self, url, depth):
        self.url = url
        self.depth = depth

    @classmethod
    def get_url_d(cls, url, depth):
        return cls(url, depth)


class Crawler:
    """
    A class that represent the crawler
    """
    def __init__(self, init_url, thread_count, crawling_depth, logger=LOGGER):
        self.q = Queue()
        self.url_dict = dict()
        self.broken_links = set()
        self.scraped_pages = set()
        self.init_url = init_url
        self.thread_count = thread_count
        self.crawling_depth = crawling_depth
        self.logger = logger
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_count)
        self._dict_lock = threading.Lock()

    def initialize_crawler(self) -> None:
        """
        putting the initial link in the queue
        """
        self.url_dict[self.init_url] = 0
        self.q.put(URLD(self.init_url, 0))
        self.logger.info(f"queue initialized with link: {self.init_url}")

    def run(self) -> Tuple[Dict, Set]:
        """
        Main function of the crawler, extracts a link from the queue, initiates scraping and callback
        """
        self.initialize_crawler()
        with self.pool:
            while True:
                try:
                    urld = self.q.get(timeout=30)
                    self.scraped_pages.add(urld.url)
                    job = self.pool.submit(self.scrape_page, urld)
                    job.add_done_callback(self.post_scrape_callback)
                    self.q.task_done()
                except (Empty, KeyboardInterrupt):
                    break
                except Exception:
                    self.logger.exception("Caught an unexpected exception in the main loop")

            self.q.join()
        return self.url_dict, self.broken_links

    def scrape_page(self, urld: URLD) -> Tuple[requests.models.Response, str, int]:
        """
        Gets the page content and passes it with the urld to the callback
        """
        try:
            response = requests.get(urld.url)
            if response.status_code not in config.BAD_STATUS_CODES:
                return response, urld.url, urld.depth
            else:
                return response, urld.url, -1
        except requests.ConnectionError:
            self.logger.warning(f"There was a connection error to {urld.url}")
            raise

    def post_scrape_callback(self, res: concurrent.futures.Future) -> None:
        """
        The post I/O function, calls for sub-links insertion if crawling depth is not reached and results dict update
        """
        possible_exception = res.exception()
        if possible_exception:
            self.logger.exception("canceling the callback due to exception in the previous function")
            return
        response, url, url_depth = res.result()
        if url_depth != -1:
            if url_depth < self.crawling_depth:
                self.insert_sub_url_to_q(response, url, url_depth)
            self.update_dict(url, url_depth)
        else:
            self.broken_links.add(url)

    def update_dict(self, url: str, url_depth: int) -> None:
        """
        updates the result dict with lock protection to prevent bugs of simultaneous update for a given link
        """
        with self._dict_lock:
            dict_url_depth = self.url_dict.get(url, -1)
            if dict_url_depth != -1:  # url was already found
                self.logger.info(f"{url} already exists in th dict")
                if url_depth < dict_url_depth:
                    self.logger.warning(f"the new depth {url_depth} is better than {dict_url_depth}, updating")
                    self.url_dict[url] = url_depth

            else:
                self.url_dict[url] = url_depth
                self.logger.info(f"{url} was added to the dict with value {url_depth}")

    def insert_sub_url_to_q(self, request_response: requests.models.Response, url: str, url_depth: int) -> None:
        """
        parses the response and iterates over the links in the page, inserts the relevant ones as URLD to the queue
        """
        soup = BeautifulSoup(request_response.text, 'lxml')
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.startswith('http'):
                if href.startswith('/'):
                    href = url + href
                if href not in self.scraped_pages:
                    self.q.put(URLD.get_url_d(href, url_depth + 1))
