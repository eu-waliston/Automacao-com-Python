from bs4 import BeautifulSoup
import requests

url = "https://www.youtube.com"
soup = BeautifulSoup(requests.get(url).content, 'html.parser')

# Extrair dados
titles = [h2.text for h2 in soup.find_all('h2')]
links = [a['href'] for a in soup.find_all('a', href=True)]