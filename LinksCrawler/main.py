import logging
from LinksCrawler.config import *
from LinksCrawler.crawler import Crawler


def main():
    logging.basicConfig(
        format=LOGGING_FORMAT,
        level=logging.INFO)
    crawler = Crawler(INITIAL_URL, CRAWLER_THREAD_COUNT, CRAWLING_DEPTH)
    links_depth_report, broken_links = crawler.run()
    for link, depth in links_depth_report.items():
        print(f"url: {link}, depth: {depth}")

    print("\n Broken links:\n")
    for link in broken_links:
        print(link)


if __name__ == '__main__':
    main()
