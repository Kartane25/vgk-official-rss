#!/usr/bin/env python3
"""Generate an image-aware RSS feed of articles linked from the official VGK news page."""
import datetime as dt
import email.utils
import html
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

SOURCE = 'https://www.nhl.com/goldenknights/news/'
OUT = Path('site/feed.xml')
MAX_ARTICLES = 25
HEADERS = {'User-Agent': 'VGKOfficialNewsRSS/1.0 (+personal feed reader)', 'Accept': 'text/html,application/xhtml+xml'}
NS_MEDIA = 'http://search.yahoo.com/mrss/'
NS_CONTENT = 'http://purl.org/rss/1.0/modules/content/'
ET.register_namespace('media', NS_MEDIA)
ET.register_namespace('content', NS_CONTENT)


def get_soup(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')


def meta(soup, *names):
    for name in names:
        node = soup.find('meta', attrs={'property': name}) or soup.find('meta', attrs={'name': name})
        if node and node.get('content'):
            return node['content'].strip()
    return ''


def clean_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))


def get_article_links(soup):
    links = []
    seen = set()
    for a in soup.select('a[href]'):
        url = clean_url(urljoin(SOURCE, a['href']))
        p = urlparse(url)
        # Limit to team-owned news articles, excluding category landing pages.
        if p.netloc not in ('nhl.com', 'www.nhl.com'):
            continue
        if not p.path.startswith('/goldenknights/news/'):
            continue
        subpath = p.path[len('/goldenknights/news/'):]
        if not subpath or subpath.startswith('topic/') and subpath.count('/') < 2:
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def parse_date(soup):
    raw = meta(soup, 'article:published_time', 'datePublished', 'pubdate', 'date', 'dateCreated')
    if not raw:
        node = soup.find('time', attrs={'datetime': True})
        raw = node.get('datetime') if node else ''
    if not raw:
        # NHL team articles usually show e.g. 'October 21, 2026'.
        txt = soup.get_text(' ', strip=True)[:4500]
        match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}\b', txt)
        raw = match.group(0) if match else ''
    if not raw:
        return None
    try:
        date = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        try:
            date = dt.datetime.strptime(raw, '%B %d, %Y')
        except ValueError:
            return None
    if date.tzinfo is None:
        date = date.replace(tzinfo=dt.timezone.utc)
    return date


def article_data(session, url):
    soup = get_soup(session, url)
    title = meta(soup, 'og:title', 'twitter:title')
    if not title:
        title = soup.h1.get_text(' ', strip=True) if soup.h1 else ''
    title = re.sub(r'\s*\|\s*(?:Vegas Golden Knights|NHL\.com).*$','',title).strip()
    summary = meta(soup, 'og:description', 'description', 'twitter:description')
    image = meta(soup, 'og:image', 'twitter:image')
    if image:
        image = urljoin(url, html.unescape(image))
    if not summary:
        article = soup.find('article') or soup.find('main')
        if article:
            paragraphs = [p.get_text(' ', strip=True) for p in article.select('p')]
            summary = next((p for p in paragraphs if len(p)>65), '')
    if not image:
        main = soup.find('article') or soup.find('main')
        pic = main.find('img', src=True) if main else None
        if pic:
            image = urljoin(url, pic['src'])
    summary = re.sub(r'\s+', ' ', html.unescape(summary)).strip()[:520]
    if not title:
        return None
    return {'title': title, 'link': url, 'description': summary, 'image': image, 'date': parse_date(soup)}


def build():
    session = requests.Session()
    session.headers.update(HEADERS)
    homepage = get_soup(session, SOURCE)
    urls = get_article_links(homepage)
    if not urls:
        raise RuntimeError('No VGK news links discovered. Check whether NHL.com changed its HTML or restricted access.')
    print(f'Found {len(urls)} candidate news links')
    articles = []
    for url in urls[:45]:
        try:
            item = article_data(session, url)
            if item:
                articles.append(item)
        except requests.RequestException as exc:
            print(f'Skipped {url}: {exc}')
        if len(articles)>=MAX_ARTICLES:
            break
    if not articles:
        raise RuntimeError('No articles parsed; refusing to publish an empty RSS feed.')
    articles.sort(key=lambda a: a['date'] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),reverse=True)
    rss = ET.Element('rss', {'version':'2.0'})
    channel = ET.SubElement(rss,'channel')
    for tag,value in [('title','Vegas Golden Knights | Official Team News'),('link',SOURCE),('description','Official Vegas Golden Knights news, photos and summaries'),('language','en-US')]:
        ET.SubElement(channel,tag).text=value
    ET.SubElement(channel,'lastBuildDate').text=email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))
    for a in articles:
        item=ET.SubElement(channel,'item')
        for tag,value in [('title',a['title']),('link',a['link']),('guid',a['link']),('description',a['description'])]:
            el=ET.SubElement(item,tag)
            if tag=='guid': el.set('isPermaLink','true')
            el.text=value
        if a['date']:
            ET.SubElement(item,'pubDate').text=email.utils.format_datetime(a['date'])
        if a['image']:
            ET.SubElement(item,f'{{{NS_MEDIA}}}content',{'url':a['image'],'medium':'image'})
            body = '<p>' + html.escape(a['description']) + '</p><p><img src="'+html.escape(a['image'],quote=True)+'" alt="" /></p>'
            ET.SubElement(item,f'{{{NS_CONTENT}}}encoded').text=body
    OUT.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(rss).write(OUT,encoding='utf-8',xml_declaration=True)
    print(f'Wrote {len(articles)} articles; {sum(bool(a["image"]) for a in articles)} have image URLs -> {OUT}')

if __name__ == '__main__':
    build()
