import logging
from LinksCrawler.config import *
from LinksCrawler.crawler import Crawler
import argparse


def main():
    logging.basicConfig(
        format=LOGGING_FORMAT,
        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--initial_url', required=True, help="The url from which the crawler will begin")
    parser.add_argument('-c', '--thread_count', default=2, type=int,
                        help="The amount of concurrent threads the crawler will run")
    parser.add_argument('-d', '--crawling_depth', default=2, type=int,
                        help="how deep the crawler will recursively look for links")
    args = parser.parse_args()
    crawler = Crawler(args.initial_url, args.thread_count, args.crawling_depth)
    links_depth_report, broken_links = crawler.run()
    for link, depth in links_depth_report.items():
        print(f"url: {link}, depth: {depth}")

    print("\n Broken links:\n")
    for link in broken_links:
        print(link)


if __name__ == '__main__':
    main()
