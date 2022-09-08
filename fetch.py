import requests
import codecs
from bs4 import BeautifulSoup as bs
from urllib.parse import unquote

host = 'https://ru.wikipedia.org'
base_url = '/wiki/Darling_in_the_Franxx'
depth = 1
get_h1_instead_of_anchor_text = False

def normalize_url(url):
    if not url.startswith('http'):
        return host + url
    else:
        return url

def get_header(url):
    inner_html = requests.get(normalize_url(url))
    inner_soup = bs(inner_html.text, "html.parser")
    return inner_soup.find('h1')

def get_words(url, depth):
    print(normalize_url(unquote(url)))
    r = requests.get(normalize_url(url))
    soup = bs(r.text, "html.parser")
    anchors = [{'text':x.text, 'href':x['href']} for x in soup.find_all('a') if x.parent.name == 'p']
    result = []
    for a in anchors:
        try:
            if get_h1_instead_of_anchor_text:
                result.append(get_header(a['href']).text)
            else:
                result.append(a['text'])
            if depth > 0:
                result += get_words(a['href'], depth-1)
        except:
            pass
    return result

filename = f'{base_url.split("/")[-1]}.txt'
with codecs.open(filename, "w", "utf-8") as f:
    words = get_words(base_url, depth)
    f.write(','.join([x.replace(',', ' ') for x in words if '\n' not in x and x != 'англ.']))