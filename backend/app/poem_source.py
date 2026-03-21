"""
External poem source integration.
Fetches poems from external websites when local DB doesn't have enough content.
"""
from __future__ import annotations

import os
import re
import random
import json
from dataclasses import dataclass
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup


@dataclass
class ExternalPoem:
    title: str
    author: str
    text: str
    language: str = "ru"
    tags: str = ""
    difficulty: int = 2


class LiteraRuSearch:
    """Search for poems on litera.ru (has classical poetry)."""
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    def search_poems(self, query: str, limit: int = 5) -> List[ExternalPoem]:
        """Search for poems on litera.ru."""
        poems = []
        
        try:
            # Try to find by author first
            author_poems = self._search_by_author(query, limit)
            poems.extend(author_poems)
            
            if len(poems) < limit:
                # Try full text search
                text_poems = self._search_by_text(query, limit - len(poems))
                poems.extend(text_poems)
            
            return poems[:limit]
            
        except Exception as e:
            print(f"[DEBUG] Litera.ru search error: {e}")
            return []
    
    def _search_by_author(self, query: str, limit: int) -> List[ExternalPoem]:
        """Search by author name."""
        try:
            # Search for author page
            search_url = f"https://litera.ru/search?q={query.replace(' ', '+')}"
            response = self.client.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for author links
            author_links = soup.find_all('a', href=re.compile(r'/author/'))
            
            for link in author_links[:3]:
                href = link.get('href', '')
                author_name = link.get_text(strip=True)
                
                if href and author_name:
                    author_url = f"https://litera.ru{href}"
                    author_poems = self._get_poems_from_author_page(author_url, author_name, limit)
                    poems.extend(author_poems)
                    
                    if len(poems) >= limit:
                        break
            
            return poems[:limit]
            
        except Exception:
            return []
    
    def _search_by_text(self, query: str, limit: int) -> List[ExternalPoem]:
        """Search by poem text/title."""
        try:
            # Try to construct direct URL for famous poems
            query_lower = query.lower()
            
            # Known poems mapping
            known_poems = {
                'мороз и солнце': 'https://litera.ru/poem/aleksandr-pushkin/zimnee-utro',
                'зимнее утро': 'https://litera.ru/poem/aleksandr-pushkin/zimnee-utro',
                'учись у них': 'https://litera.ru/poem/mihail-lermontov/uchis-u-nih-ot-oreha',
                'парус': 'https://litera.ru/poem/mihail-lermontov/parus',
                'белеет парус одинокой': 'https://litera.ru/poem/mihail-lermontov/parus',
                'я помню чудное мгновенье': 'https://litera.ru/poem/aleksandr-pushkin/ya-pomnyu-chudnoe-mgnovenie',
                'к***': 'https://litera.ru/poem/aleksandr-pushkin/k',
                'пророк': 'https://litera.ru/poem/aleksandr-pushkin/prorok',
                'демон': 'https://litera.ru/poem/mihail-lermontov/demon',
                'мцыри': 'https://litera.ru/poem/mihail-lermontov/mcyri',
                'песнь о вещем олеге': 'https://litera.ru/poem/aleksandr-pushkin/pesn-o-veschem-olege',
                'сказка о царе салтане': 'https://litera.ru/poem/aleksandr-pushkin/skazka-o-care-saltane',
                'евгений онегин': 'https://litera.ru/poem/aleksandr-pushkin/evgeniy-onegin',
                'руслан и людмила': 'https://litera.ru/poem/aleksandr-pushkin/ruslan-i-lyudmila',
                'медный всадник': 'https://litera.ru/poem/aleksandr-pushkin/mednyy-vsadnik',
                'ангел': 'https://litera.ru/poem/mihail-lermontov/angel',
                'сосна': 'https://litera.ru/poem/mihail-lermontov/sosna',
                'на севере диком': 'https://litera.ru/poem/mihail-lermontov/sosna',
                'тучи': 'https://litera.ru/poem/mihail-lermontov/tuchi',
                'лес': 'https://litera.ru/poem/sergey-esenin/les',
                'береза': 'https://litera.ru/poem/sergey-esenin/bereza',
                'пугачев': 'https://litera.ru/poem/sergey-esenin/pugachev',
                'сергей есенин': 'https://litera.ru/poem/sergey-esenin/bereza',
                'есенин': 'https://litera.ru/poem/sergey-esenin/bereza',
                'пушкин': 'https://litera.ru/poem/aleksandr-pushkin/zimnee-utro',
                'лермонтов': 'https://litera.ru/poem/mihail-lermontov/parus',
                'тютчев': 'https://litera.ru/poem/fedor-tutchev/silentium',
                'фет': 'https://litera.ru/poem/afanasiy-fet/ya-prishel-k-tebe-s-poluvzdoxnoyu',
                'некрасов': 'https://litera.ru/poem/nikolay-nekrasov/komu-na-rusi-zhit-xorosho',
                'блок': 'https://litera.ru/poem-aleksandr-blok/night',
                'ахматова': 'https://litera.ru/poem/anna-ahmatova/muzhke',
                'цветаева': 'https://litera.ru/poem/marina-cvetaeva/moy-pushkin',
                'пастернак': 'https://litera.ru/poem/boris-pasternak/zimnie-nochi',
                'маяковский': 'https://litera.ru/poem/vladimir-mayakovskiy/poslushaite',
                'епрефьев': 'https://litera.ru/poem/ilya-eprefev/slovo-o-poraboshennom',
            }
            
            for key, url in known_poems.items():
                if key in query_lower:
                    poem = self._parse_poem_page(url)
                    if poem:
                        return [poem]
            
            return []
            
        except Exception:
            return []
    
    def _get_poems_from_author_page(self, author_url: str, author_name: str, limit: int) -> List[ExternalPoem]:
        """Get poems from author page."""
        poems = []
        
        try:
            response = self.client.get(author_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for poem links
            poem_links = soup.find_all('a', href=re.compile(r'/poem/'))
            
            for link in poem_links[:limit]:
                href = link.get('href', '')
                if href:
                    poem_url = f"https://litera.ru{href}"
                    poem = self._parse_poem_page(poem_url)
                    if poem:
                        poem.author = author_name
                        poems.append(poem)
            
            return poems
            
        except Exception:
            return []
    
    def _parse_poem_page(self, url: str) -> Optional[ExternalPoem]:
        """Parse a single poem page."""
        try:
            response = self.client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = "Unknown"
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
            
            # Extract author
            author = "Unknown"
            author_elem = soup.find('a', href=re.compile(r'/author/'))
            if author_elem:
                author = author_elem.get_text(strip=True)
            
            # Extract poem text
            text = ""
            # Look for poem content in various selectors
            for selector in ['.poem-text', '.text-content', '.poem', 'pre', 'blockquote']:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text('\n', strip=True)
                    if len(text) > 50:
                        break
            
            if not text:
                # Fallback: find div with multiple lines
                for elem in soup.find_all('div'):
                    content = elem.get_text('\n', strip=True)
                    if len(content) > 100 and '\n' in content and not elem.find('a'):
                        text = content
                        break
            
            if not text or len(text) < 30:
                return None
            
            return ExternalPoem(
                title=title,
                author=author,
                text=text,
                language="ru"
            )
            
        except Exception:
            return None


class HardcodedPoems:
    """Fallback hardcoded poems for famous works."""
    
    POEMS = [
        ExternalPoem(
            title="Зимнее утро",
            author="Александр Пушкин",
            text="Мороз и солнце; день чудесный!\nЕще ты дремлешь, друг прелестный —\nПора, красавица, проснись:\nОткрой сомкнуты негой взоры\nНавстречу северной Авроры,\nЗвездою севера явись!\n\nВечор, ты помнишь, вьюга злилась,\nНа мутном небе мгла носилась;\nЛуна, как бледное пятно,\nСквозь тучи мрачные желтела,\nИ ты печальная сидела —\nА нынче... погляди в окно:\n\nПод голубыми небесами\nВеликолепными коврами,\nБлестя на солнце, снег лежит;\nПрозрачный лес один чернеет,\nИ ель сквозь иней зеленеет,\nИ речка подо льдом блестит.\n\nВся комната янтарным блеском\nОзарена. Весёлым треском\nТрещит затопленная печь.\nПриятно думать у лежанки.\nНо знаешь: не велеть ли в санки\nКобылку бурую запречь?\n\nСкользя по утреннему снегу,\nДруг милый, предадимся бегу\nНетерпеливого коня\nИ навестим поля пустые,\nЛеса, недавно столь густые,\nИ берег, милый для меня.",
            language="ru",
            tags="природа,зима",
            difficulty=2
        ),
        ExternalPoem(
            title="Парус",
            author="Михаил Лермонтов",
            text="Белеет парус одинокой\nВ тумане моря голубом!..\nЧто ищет он в стране далекой?\nЧто кинул он в краю родном?..\n\nИграют волны — ветер свищет,\nИ мачта гнется и скрыпит...\nУвы! он счастия не ищет\nИ не от счастия бежит!\n\nПод ним струя светлей лазури,\nНад ним луч солнца золотой...\nА он, мятежный, просит бури,\nКак будто в бурях есть покой!",
            language="ru",
            tags="море,одиночество",
            difficulty=1
        ),
        ExternalPoem(
            title="Я помню чудное мгновенье",
            author="Александр Пушкин",
            text="Я помню чудное мгновенье:\nПередо мной явилась ты,\nКак мимолетное виденье,\nКак гений чистой красоты.\n\nВ томленьях грусти безнадежной,\nВ тревогах шумной суеты,\nЗвучал мне долго голос нежный\nИ снились милые черты.\n\nШли годы. Бурь порыв мятежный\nРассеял прежние мечты,\nИ я забыл твой голос нежный,\nТвои небесные черты.\n\nВ глуши, во мраке заточенья\nТянулись тихо дни мои\nБез божества, без вдохновенья,\nБез слез, без жизни, без любви.\n\nДуше настало пробужденье:\nИ вот опять явилась ты,\nКак мимолетное виденье,\nКак гений чистой красоты.\n\nИ сердце бьется в упоенье,\nИ для него воскресли вновь\nИ божество, и вдохновенье,\nИ жизнь, и слезы, и любовь.",
            language="ru",
            tags="любовь,лирика",
            difficulty=2
        ),
        ExternalPoem(
            title="Ангел",
            author="Михаил Лермонтов",
            text="По небу полуночи ангел летел,\nИ тихую песню он пел;\nИ месяц, и звезды, и тучи толпой\nВнимали той песне святой.\n\nОн пел о блаженстве безгрешных духов\nПод кущами райских садов;\nО Боге великом он пел, и хвала\nЕго непритворна была.\n\nОн душу младую в объятиях нес\nДля мира печали и слез;\nИ звук его песни в душе молодой\nОстался — без слов, но живой.\n\nИ долго на свете томилась она,\nЖеланием чудным полна;\nИ звуков небес заменить не могли\nЕй скучные песни земли.",
            language="ru",
            tags="философия,духовность",
            difficulty=2
        ),
        ExternalPoem(
            title="Берёза",
            author="Сергей Есенин",
            text="Белая берёза\nПод моим окном\nПринакрылась снегом,\nТочно серебром.\n\nНа пушистых ветках\nСнежною каймой\nРаспустились кисти\nБелой бахромой.\n\nИ стоит берёза\nВ сонной тишине,\nИ горят снежинки\nВ золотом огне.\n\nА заря, лениво\nОбходя кругом,\nОбсыпает ветки\nНовым серебром.",
            language="ru",
            tags="природа,зима",
            difficulty=1
        ),
        ExternalPoem(
            title="Ночь, улица, фонарь, аптека",
            author="Александр Блок",
            text="Ночь, улица, фонарь, аптека,\nБессмысленный и тусклый свет.\nЖиви ещё хоть четверть века —\nВсё будет так. Исхода нет.\n\nУмрёшь — начнёшь опять сначала\nИ повторится всё, как встарь:\nНочь, ледяная рябь канала,\nАптека, улица, фонарь.",
            language="ru",
            tags="философия,город",
            difficulty=1
        ),
        ExternalPoem(
            title="На севере диком",
            author="Михаил Лермонтов",
            text="На севере диком стоит одиноко\nНа голой вершине сосна\nИ дремлет, качаясь, и снегом сыпучим\nОдета, как ризой, она.\n\nИ снится ей всё, что в пустыне далёкой —\nВ том крае, где солнца восход,\nОдна и грустна на утёсе горючем\nПрекрасная пальма растёт.",
            language="ru",
            tags="одиночество,природа",
            difficulty=1
        ),
        ExternalPoem(
            title="Тучи",
            author="Михаил Лермонтов",
            text="Тучки небесные, вечные странники!\nСтепью лазурною, цепью жемчужною\nМчитесь вы, будто как я же, изгнанники\nС милого севера в сторону южную.\n\nКто же вас гонит: судьбы ли решение?\nЗависть ли тайная? злоба ль открытая?\nИли на вас тяготит преступление?\nИли друзей клевета ядовитая?\n\nНет, вам наскучили нивы бесплодные...\nЧужды вам страсти и чужды страдания;\nВечно холодные, вечно свободные,\nНет у вас родины, нет вам изгнания.",
            language="ru",
            tags="философия,изгнание",
            difficulty=2
        ),
        ExternalPoem(
            title="Послушайте!",
            author="Владимир Маяковский",
            text="Послушайте!\nВедь, если звёзды зажигают —\nзначит — это кому-нибудь нужно?\nЗначит — кто-то хочет, чтобы они были?\nЗначит — кто-то называет эти плевочки\nжемчужиной?\n\nИ, надрываясь\nв метелях полуденной пыли,\nврывается к богу,\nбоится, что опоздал,\nплачет,\nцелует ему жилистую руку,\nпросит —\nчтоб обязательно была звезда! —\nклянётся —\nне перенесёт эту беззвёздную муку!\n\nА после\nходит тревожный,\nно спокойный наружно.\nГоворит кому-то:\n«Ведь теперь тебе ничего?\nНе страшно?\nДа?!»\n\nПослушайте!\nВедь, если звёзды\nзажигают —\nзначит — это кому-нибудь нужно?\nЗначит — это необходимо,\nчтобы каждый вечер\nнад крышами\nзагоралась хоть одна звезда?!",
            language="ru",
            tags="философия,лирика",
            difficulty=3
        ),
        # === ENGLISH POEMS ===
        ExternalPoem(
            title="Shall I compare thee to a summer's day?",
            author="William Shakespeare",
            text="Shall I compare thee to a summer's day?\nThou art more lovely and more temperate:\nRough winds do shake the darling buds of May,\nAnd summer's lease hath all too short a date:\n\nSometime too hot the eye of heaven shines,\nAnd often is his gold complexion dimm'd;\nAnd every fair from fair sometime declines,\nBy chance, or nature's changing course untrimm'd;\n\nBut thy eternal summer shall not fade,\nNor lose possession of that fair thou ow'st;\nNor shall death brag thou wander'st in his shade,\nWhen in eternal lines to time thou grow'st:\n\nSo long as men can breathe, or eyes can see,\nSo long lives this, and this gives life to thee.",
            language="en",
            tags="love,beauty",
            difficulty=2
        ),
        ExternalPoem(
            title="Because I could not stop for Death",
            author="Emily Dickinson",
            text="Because I could not stop for Death –\nHe kindly stopped for me –\nThe Carriage held but just Ourselves –\nAnd Immortality.\n\nWe slowly drove – He knew no haste\nAnd I had put away\nMy labor and my leisure too,\nFor His Civility –\n\nWe passed the School, where Children strove\nAt Recess – in the Ring –\nWe passed the Fields of Gazing Grain –\nWe passed the Setting Sun –\n\nSince then – 'tis Centuries – and yet\nFeels shorter than the Day\nI first surmised the Horses' Heads\nWere toward Eternity –",
            language="en",
            tags="death,philosophy",
            difficulty=2
        ),
        ExternalPoem(
            title="The Road Not Taken",
            author="Robert Frost",
            text="Two roads diverged in a yellow wood,\nAnd sorry I could not travel both\nAnd be one traveler, long I stood\nAnd looked down one as far as I could\nTo where it bent in the undergrowth;\n\nThen took the other, as just as fair,\nAnd having perhaps the better claim,\nBecause it was grassy and wanted wear;\nThough as for that the passing there\nHad worn them really about the same,\n\nAnd both that morning equally lay\nIn leaves no step had trodden black.\nOh, I kept the first for another day!\nYet knowing how way leads on to way,\nI doubted if I should ever come back.\n\nI shall be telling this with a sigh\nSomewhere ages and ages hence:\nTwo roads diverged in a wood, and I—\nI took the one less traveled by,\nAnd that has made all the difference.",
            language="en",
            tags="choice,nature",
            difficulty=2
        ),
        ExternalPoem(
            title="I Wandered Lonely as a Cloud",
            author="William Wordsworth",
            text="I wandered lonely as a cloud\nThat floats on high o'er vales and hills,\nWhen all at once I saw a crowd,\nA host, of golden daffodils;\nBeside the lake, beneath the trees,\nFluttering and dancing in the breeze.\n\nContinuous as the stars that shine\nAnd twinkle on the milky way,\nThey stretched in never-ending line\nAlong the margin of a bay:\nTen thousand saw I at a glance,\nTossing their heads in sprightly dance.\n\nThe waves beside them danced; but they\nOut-did the sparkling waves in glee:\nA poet could not but be gay,\nIn such a jocund company:\nI gazed — and gazed — but little thought\nWhat wealth the show to me had brought:\n\nFor oft, when on my couch I lie\nIn vacant or in pensive mood,\nThey flash upon that inward eye\nWhich is the bliss of solitude;\nAnd then my heart with pleasure fills,\nAnd dances with the daffodils.",
            language="en",
            tags="nature,joy",
            difficulty=2
        ),
        ExternalPoem(
            title="The Tyger",
            author="William Blake",
            text="Tyger Tyger, burning bright,\nIn the forests of the night;\nWhat immortal hand or eye,\nCould frame thy fearful symmetry?\n\nIn what distant deeps or skies,\nBurnt the fire of thine eyes?\nOn what wings dare he aspire?\nWhat the hand, dare seize the fire?\n\nAnd what shoulder, & what art,\nCould twist the sinews of thy heart?\nAnd when thy heart began to beat,\nWhat dread hand? & what dread feet?\n\nWhat the hammer? what the chain,\nIn what furnace was thy brain?\nWhat the anvil? what dread grasp,\nDare its deadly terrors clasp!\n\nWhen the stars threw down their spears\nAnd water'd heaven with their tears:\nDid he smile his work to see?\nDid he who made the Lamb make thee?\n\nTyger Tyger burning bright,\nIn the forests of the night:\nWhat immortal hand or eye,\nDare frame thy fearful symmetry?",
            language="en",
            tags="nature,philosophy",
            difficulty=2
        ),
    ]
    
    def search_poems(self, query: str, limit: int = 5) -> List[ExternalPoem]:
        """Search in hardcoded poems."""
        query_lower = query.lower()
        results = []
        
        for poem in self.POEMS:
            # Check if query matches title, author, or contains text
            author_lower = poem.author.lower()
            title_lower = poem.title.lower()
            
            # Direct author match (handle different forms)
            if (query_lower in author_lower or 
                author_lower in query_lower or
                self._normalize_name(query_lower) in self._normalize_name(author_lower) or
                self._normalize_name(author_lower) in self._normalize_name(query_lower)):
                results.append(poem)
                if len(results) >= limit:
                    break
            
            # Direct title match
            elif query_lower in title_lower or title_lower in query_lower:
                results.append(poem)
                if len(results) >= limit:
                    break
            
            # Word match in text (for longer queries)
            elif any(word in poem.text.lower() for word in query_lower.split() if len(word) > 3):
                results.append(poem)
                if len(results) >= limit:
                    break
        
        return results
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name by removing common endings and prefixes."""
        # Remove common endings: -ский, -ая, -ов, -ев, -ого
        name = re.sub(r'(ский|ская|ов|ев|ая|ий|ый|ого)$', '', name)
        # Remove common words
        name = name.replace('владимир', '').replace('александр', '').replace('михаил', '').replace('сергей', '').strip()
        return name


class StihiRuSearch:
    """Search for poems on stihi.ru."""
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    def search_poems(self, query: str, limit: int = 5) -> List[ExternalPoem]:
        """Search for poems on stihi.ru."""
        poems = []
        
        try:
            # Try direct search URL
            encoded_query = query.replace(' ', '+')
            search_url = f"https://www.stihi.ru/search.html?str={encoded_query}"
            
            response = self.client.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for poem links
            poem_links = soup.find_all('a', href=re.compile(r'/poem/'))
            
            for link in poem_links[:limit]:
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                if href and title:
                    poem_url = f"https://www.stihi.ru{href}"
                    poem = self._parse_poem_page(poem_url, title)
                    if poem:
                        poems.append(poem)
            
            return poems
            
        except Exception as e:
            print(f"[DEBUG] Stihi.ru search error: {e}")
            return []
    
    def _parse_poem_page(self, url: str, title: str) -> Optional[ExternalPoem]:
        """Parse a single poem page."""
        try:
            response = self.client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract author
            author = "Unknown"
            author_elem = soup.find('div', class_='author')
            if author_elem:
                author = author_elem.get_text(strip=True)
            
            # Extract poem text
            text = ""
            # Look for poem content
            for selector in ['.text', '.poem', 'pre', 'div[class*="text"]']:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text('\n', strip=True)
                    if len(text) > 50:
                        break
            
            if not text:
                # Fallback: look for div with multiple lines
                for elem in soup.find_all('div'):
                    content = elem.get_text('\n', strip=True)
                    if len(content) > 100 and '\n' in content and not elem.find('a'):
                        text = content
                        break
            
            if not text or len(text) < 30:
                return None
            
            return ExternalPoem(
                title=title,
                author=author,
                text=text,
                language="ru"
            )
            
        except Exception:
            return None


class DuckDuckGoPoemSearch:
    """Fallback search using DuckDuckGo (no API key required)."""
    
    def __init__(self):
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
            self.available = True
        except Exception:
            self.available = False
            self.ddgs = None
    
    def is_available(self) -> bool:
        return self.available
    
    def search_poems(self, query: str, limit: int = 5) -> List[ExternalPoem]:
        """Search for poems using DuckDuckGo."""
        if not self.is_available():
            return []
        
        try:
            # Search for poem
            search_query = f"{query} стихотворение stihi.ru"
            results = self.ddgs.text(search_query, max_results=limit * 2)
            
            poems = []
            for result in results:
                try:
                    url = result.get('href', '')
                    title = result.get('title', '').replace(' - стихотворение', '').strip()
                    
                    # Only process stihi.ru URLs
                    if 'stihi.ru' not in url.lower():
                        continue
                    
                    poem = self._fetch_poem_from_url(url, title)
                    if poem:
                        poems.append(poem)
                        if len(poems) >= limit:
                            break
                except Exception:
                    continue
            
            return poems
            
        except Exception as e:
            print(f"[DEBUG] DuckDuckGo search error: {e}")
            return []
    
    def _fetch_poem_from_url(self, url: str, title: str) -> Optional[ExternalPoem]:
        """Fetch and parse poem from stihi.ru URL."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            client = httpx.Client(timeout=10.0)
            response = client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find author
            author = "Unknown"
            author_elem = soup.select_one('.authorname, .poet-name, [class*="author"]')
            if author_elem:
                author = author_elem.get_text(strip=True)
            
            # Try to find poem text - stihi.ru uses different selectors
            text = ""
            for selector in ['.poem', '.text', '.stih', '[class*="poem"]', 'pre', '.main']:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text('\n', strip=True)
                    if len(text) > 50:
                        break
            
            if not text or len(text) < 30:
                return None
            
            return ExternalPoem(
                title=title,
                author=author,
                text=text,
                language="ru"
            )
        except Exception:
            return None


class GooglePoemSearch:
    """Fallback search using Google Custom Search API."""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.cx = os.getenv("GOOGLE_CX")
        self.client = httpx.Client(timeout=30.0)
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.cx)
    
    def search_poems(self, query: str, limit: int = 5) -> List[ExternalPoem]:
        """Search for poems using Google Custom Search."""
        if not self.is_available():
            return []
        
        try:
            # Search for poem on stihi.ru or other sources
            search_query = f"{query} стихотворение"
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': search_query,
                'num': min(limit * 2, 10)
            }
            
            response = self.client.get(url, params=params)
            data = response.json()
            
            poems = []
            if 'items' in data:
                for item in data['items']:
                    poem = self._try_parse_poem(item)
                    if poem:
                        poems.append(poem)
                        if len(poems) >= limit:
                            break
            
            return poems
            
        except Exception as e:
            print(f"[DEBUG] Google search error: {e}")
            return []
    
    def _try_parse_poem(self, item: dict) -> Optional[ExternalPoem]:
        """Try to parse a poem from a search result."""
        try:
            url = item.get('link', '')
            title = item.get('title', '').replace(' - стихотворение', '').strip()
            snippet = item.get('snippet', '')
            
            # Skip if not a poem URL
            if not any(x in url.lower() for x in ['stihi.ru', 'poetory.ru', 'rupoem.ru']):
                return None
            
            # Try to fetch the poem
            return self._fetch_poem_from_url(url, title)
        except Exception:
            return None
    
    def _fetch_poem_from_url(self, url: str, title: str) -> Optional[ExternalPoem]:
        """Fetch and parse poem from URL."""
        try:
            response = self.client.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find author
            author = "Unknown"
            for selector in ['.author', '.poet', '[class*="author"]', '[class*="poet"]']:
                elem = soup.select_one(selector)
                if elem:
                    author = elem.get_text(strip=True)
                    break
            
            # Try to find poem text
            text = ""
            for selector in ['.poem', '.text', '[class*="poem"]', '[class*="text"]', 'pre']:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text('\n', strip=True)
                    if len(text) > 50:
                        break
            
            if not text or len(text) < 30:
                return None
            
            return ExternalPoem(
                title=title,
                author=author,
                text=text,
                language="ru"
            )
        except Exception:
            return None


class RupoemClient:
    """Client for fetching poems from rupoem.ru"""
    
    BASE_URL = "https://rupoem.ru"
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    def _get_soup(self, url: str) -> BeautifulSoup:
        response = self.client.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    
    def search_poems(self, query: str, limit: int = 5) -> List[ExternalPoem]:
        """Search for poems by query (title/author)."""
        poems = []
        
        # Try rupoem.ru poets pages as fallback
        try:
            # Search in poets list
            url = f"{self.BASE_URL}/poets"
            response = self.client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find poets matching query
            poet_links = []
            for link in soup.find_all('a', href=re.compile(r'/poets/')):
                poet_name = link.get_text(strip=True).lower()
                if any(word in poet_name for word in query.lower().split()[:3]):
                    href = link.get('href', '')
                    if href:
                        poet_links.append(f"{self.BASE_URL}{href}")
            
            # Get poems from matching poets
            for poet_url in poet_links[:2]:
                try:
                    poet_poems = self._get_poems_from_poet_page(poet_url)
                    poems.extend(poet_poems)
                    if len(poems) >= limit:
                        break
                except Exception:
                    continue
            
        except Exception as e:
            print(f"[DEBUG] Rupoem search error: {e}")
        
        return poems[:limit]
    
    def _get_poems_from_poet_page(self, poet_url: str) -> List[ExternalPoem]:
        """Extract poems from a poet's page."""
        poems = []
        
        response = self.client.get(poet_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract poet name from h1 or title
        poet_name = "Unknown"
        h1 = soup.find('h1')
        if h1:
            poet_name = h1.get_text(strip=True)
        
        # Look for poem content
        # rupoem.ru uses /poem/ links
        poem_links = soup.find_all('a', href=re.compile(r'/poem/'))
        
        for link in poem_links[:10]:
            href = link.get('href', '')
            title = link.get_text(strip=True)
            
            if href and title:
                full_url = f"{self.BASE_URL}{href}" if not href.startswith('http') else href
                try:
                    poem = self._parse_poem_page(full_url, poet_name)
                    if poem:
                        poems.append(poem)
                except Exception:
                    continue
        
        return poems
    
    def _parse_poem_page(self, url: str, poet_name: str) -> Optional[ExternalPoem]:
        """Parse a single poem page."""
        response = self.client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = "Unknown"
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        
        # Extract poem text
        text = ""
        # Look for main content
        for selector in ['.poem-text', '.poem-content', '.text', 'article', 'main']:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text('\n', strip=True)
                if len(text) > 50:
                    break
        
        if not text:
            # Fallback: look for large text blocks
            for elem in soup.find_all(['div', 'p', 'pre']):
                content = elem.get_text(strip=True)
                if len(content) > 100 and '\n' in content:
                    text = content
                    break
        
        if not text or len(text) < 50:
            return None
        
        return ExternalPoem(
            title=title,
            author=poet_name,
            text=text,
            language="ru"
        )
    
    def get_random_poem(self) -> Optional[ExternalPoem]:
        """Fetch a random poem."""
        try:
            # Get random poet
            url = f"{self.BASE_URL}/poets"
            response = self.client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            poet_links = soup.find_all('a', href=re.compile(r'/poets/'))
            if poet_links:
                random_poet = random.choice(poet_links[:50])
                href = random_poet.get('href', '')
                if href:
                    poet_url = f"{self.BASE_URL}{href}"
                    poems = self._get_poems_from_poet_page(poet_url)
                    if poems:
                        return random.choice(poems)
            
            return None
            
        except Exception:
            return None


# Singleton instances
_rupoem_client: Optional[RupoemClient] = None
_google_search: Optional[GooglePoemSearch] = None
_duckduckgo_search: Optional[DuckDuckGoPoemSearch] = None
_litera_search: Optional[LiteraRuSearch] = None
_stihi_search: Optional[StihiRuSearch] = None
_hardcoded_poems: Optional[HardcodedPoems] = None


def get_rupoem_client() -> RupoemClient:
    """Get or create RupoemClient singleton."""
    global _rupoem_client
    if _rupoem_client is None:
        _rupoem_client = RupoemClient()
    return _rupoem_client


def get_google_search() -> GooglePoemSearch:
    """Get or create GooglePoemSearch singleton."""
    global _google_search
    if _google_search is None:
        _google_search = GooglePoemSearch()
    return _google_search


def get_duckduckgo_search() -> DuckDuckGoPoemSearch:
    """Get or create DuckDuckGoPoemSearch singleton."""
    global _duckduckgo_search
    if _duckduckgo_search is None:
        _duckduckgo_search = DuckDuckGoPoemSearch()
    return _duckduckgo_search


def get_litera_search() -> LiteraRuSearch:
    """Get or create LiteraRuSearch singleton."""
    global _litera_search
    if _litera_search is None:
        _litera_search = LiteraRuSearch()
    return _litera_search


def get_stihi_search() -> StihiRuSearch:
    """Get or create StihiRuSearch singleton."""
    global _stihi_search
    if _stihi_search is None:
        _stihi_search = StihiRuSearch()
    return _stihi_search


def get_hardcoded_poems() -> HardcodedPoems:
    """Get or create HardcodedPoems singleton."""
    global _hardcoded_poems
    if _hardcoded_poems is None:
        _hardcoded_poems = HardcodedPoems()
    return _hardcoded_poems


def fetch_poems_for_user(query: Optional[str] = None, limit: int = 5) -> List[ExternalPoem]:
    """
    Fetch multiple poems for a user. Tries multiple sources.
    """
    if not query:
        # Return random poems
        client = get_rupoem_client()
        poems = []
        for _ in range(min(limit, 3)):
            poem = client.get_random_poem()
            if poem and poem not in poems:
                poems.append(poem)
        return poems
    
    # Try hardcoded poems first (guaranteed to work)
    print(f"[DEBUG] Searching hardcoded poems for: {query}")
    hardcoded = get_hardcoded_poems()
    poems = hardcoded.search_poems(query, limit=limit)
    
    if poems:
        print(f"[DEBUG] Found {len(poems)} poems in hardcoded collection")
        return poems
    
    # Try StihiRu second
    print(f"[DEBUG] Searching stihi.ru for: {query}")
    stihi = get_stihi_search()
    poems = stihi.search_poems(query, limit=limit)
    
    if poems:
        print(f"[DEBUG] Found {len(poems)} poems on stihi.ru")
        return poems
    
    # Try litera.ru third for classical poetry
    print(f"[DEBUG] Searching litera.ru for: {query}")
    litera = get_litera_search()
    poems = litera.search_poems(query, limit=limit)
    
    if poems:
        print(f"[DEBUG] Found {len(poems)} poems on litera.ru")
        return poems
    
    # Try rupoem.ru fourth
    print(f"[DEBUG] Searching rupoem.ru for: {query}")
    client = get_rupoem_client()
    poems = client.search_poems(query, limit=limit)
    
    if poems:
        print(f"[DEBUG] Found {len(poems)} poems on rupoem.ru")
        return poems
    
    # Try DuckDuckGo search (no API key needed)
    print(f"[DEBUG] Trying DuckDuckGo search for: {query}")
    ddg = get_duckduckgo_search()
    if ddg.is_available():
        poems = ddg.search_poems(query, limit=limit)
        if poems:
            print(f"[DEBUG] Found {len(poems)} poems via DuckDuckGo")
            return poems
    
    # Try Google search as last fallback (requires API key)
    print(f"[DEBUG] Trying Google search for: {query}")
    google = get_google_search()
    if google.is_available():
        poems = google.search_poems(query, limit=limit)
        if poems:
            print(f"[DEBUG] Found {len(poems)} poems via Google")
            return poems
    
    print(f"[DEBUG] No poems found for: {query}")
    return []
