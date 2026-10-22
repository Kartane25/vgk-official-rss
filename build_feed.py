"""Republish MissConduct.vegas's public RSS with image metadata for Discord feed bots."""
import html
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import feedparser
import requests
from bs4 import BeautifulSoup

SOURCE = 'https://missconduct.sinbin.vegas/feed/'
DEST = Path('site/feed.xml')
NS_MEDIA = 'http://search.yahoo.com/mrss/'
NS_CONTENT = 'http://purl.org/rss/1.0/modules/content/'
ET.register_namespace('media', NS_MEDIA)
ET.register_namespace('content', NS_CONTENT)


def plain(value):
    soup = BeautifulSoup(value or '', 'html.parser')
    return ' '.join(soup.get_text(' ', strip=True).split())


def choose_image(entry):
    # WordPress embeds an image in content:encoded; try that before summaries.
    content = entry.get('content') or []
    pieces = [x.get('value', '') for x in content]
    pieces.extend([entry.get('summary', ''), entry.get('description', '')])
    for piece in pieces:
        soup = BeautifulSoup(piece, 'html.parser')
        for img in soup.find_all('img'):
            url = img.get('data-src') or img.get('src')
            if not url:
                srcset = img.get('srcset')
                if srcset:
                    url = srcset.split(',')[0].strip().split(' ')[0]
            if url:
                url = urljoin(entry.get('link', SOURCE), url)
                if urlparse(url).scheme in ('http', 'https') and not url.startswith('data:'):
                    return url
    for media in entry.get('media_content', []):
        if media.get('url'):
            return media['url']
    return None


def main():
    response = requests.get(SOURCE, timeout=35, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; MissConductRSSReader/1.0; public RSS feed)',
        'Accept': 'application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.5',
    })
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if not parsed.entries or (parsed.bozo and not parsed.entries):
        raise RuntimeError('RSS source unavailable or blocked. Check for a CAPTCHA. Refusing to publish empty feed.')
    if b'sgcaptcha' in response.content.lower() or b'captcha' in response.content[:1000].lower():
        raise RuntimeError('RSS request returned website security challenge; do not deploy invalid data.')

    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', 'MissConduct.vegas | News'), ('link', 'https://missconduct.sinbin.vegas/'),
                       ('description', 'Articles from MissConduct.vegas, including photos where available.'),
                       ('language', 'en-US'), ('lastBuildDate', format_datetime(datetime.now(timezone.utc)))]:
        ET.SubElement(channel, key).text = value

    count_images = 0
    for entry in parsed.entries[:40]:
        link = entry.get('link') or ''
        if not link.startswith('https://missconduct.sinbin.vegas/'):
            continue
        item = ET.SubElement(channel, 'item')
        title = plain(entry.get('title', 'Untitled'))
        desc = plain(entry.get('summary', '') or entry.get('description', ''))
        desc = re.sub(r'\s+', ' ', desc).strip()[:450]
        for tag, value in [('title', title), ('link', link), ('guid', entry.get('id') or link), ('description', desc)]:
            elem = ET.SubElement(item, tag)
            if tag == 'guid':
                elem.set('isPermaLink', 'false')
            elem.text = value
        if entry.get('published'):
            ET.SubElement(item, 'pubDate').text = entry.published
        img = choose_image(entry)
        if img:
            count_images += 1
            ET.SubElement(item, f'{{{NS_MEDIA}}}content', {'url': img, 'medium': 'image'})
            # The extra image tag is useful to parsers that read HTML content.
            ET.SubElement(item, f'{{{NS_CONTENT}}}encoded').text = f'<img src="{html.escape(img, quote=True)}" alt="" />'
    if not channel.findall('item'):
        raise RuntimeError('No usable MissConduct articles found.')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(rss, space='  ')
    ET.ElementTree(rss).write(DEST, encoding='utf-8', xml_declaration=True)
    print(f'Generated {len(channel.findall("item"))} articles, {count_images} images to {DEST}')


if __name__ == '__main__':
    main()
