"""
Сервис модерации: проверка сообщений на соответствие черному списку
"""
import logging
import re
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import BlacklistRepository
from typing import List, Dict, Pattern

logger = logging.getLogger(__name__)

# Регулярные выражения для русских матерных слов
# Учитывают различные варианты написания, замены букв на похожие символы
RUSSIAN_PROFANITY_PATTERNS: Dict[str, Pattern] = {
    # Базовые оскорбления
    "идиот": re.compile(r'[иi1l][дd][иi1l][оo0][тt]', re.IGNORECASE),
    "дурак": re.compile(r'[дd][уy][рr][аa@][кk]', re.IGNORECASE),
    "тупой": re.compile(r'[тt][уy][пp][оo0][йy]', re.IGNORECASE),
    "лох": re.compile(r'[лl][оo0][хx]', re.IGNORECASE),
    
    # Матерные слова (основные)
    # Паттерн "еб" - только отдельное слово (используем \b для границ слова)
    # В Python \b работает только с ASCII, но для кириллицы это не проблема,
    # так как паттерн проверяет начало слова, и "еб" в "тебя" не является началом слова
    "еб": re.compile(r'\b[её]б[а-яё]*\b', re.IGNORECASE),
    "наеб": re.compile(r'на[её]б[а-яё]*', re.IGNORECASE),
    "поеб": re.compile(r'поеб[а-яё]*', re.IGNORECASE),
    "еблан": re.compile(r'[еe][бb6][лl][аa@][нn]', re.IGNORECASE),
    "ебан": re.compile(r'[еe][бb6][аa@][нn]', re.IGNORECASE),
    "ебанутый": re.compile(r'[еe][бb6][аa@][нn][уy][тt][ыy][йy]', re.IGNORECASE),
    "ебануть": re.compile(r'[еe][бb6][аa@][нn][уy][тt][ьь]', re.IGNORECASE),
    "ебанулся": re.compile(r'[еe][бb6][аa@][нn][уy][лl][сc][яя]', re.IGNORECASE),
    "ебтвом": re.compile(r'е[бb6]\s*тво[юю]?м[а-яё]*\b|ебтв[оо]м', re.IGNORECASE),
    "ебищ": re.compile(r'[её]бищ[еу]', re.IGNORECASE),
    "уеб": re.compile(r'у[её]б[окун]*', re.IGNORECASE),
    "уёбищ": re.compile(r'уёбищ[еу]', re.IGNORECASE),
    
    "блядь": re.compile(r'[бb6][лl][яя][дd][ьь]', re.IGNORECASE),
    "бля": re.compile(r'\bбл[яяд][ди]*\b', re.IGNORECASE),
    "блядин": re.compile(r'блядин[а-яё]*', re.IGNORECASE),
    "бляд": re.compile(r'б[лль][я@][дд][иі][нтна]?', re.IGNORECASE),
    
    "хуй": re.compile(r'\bху[еи][йя]*\b|х[уу][йи][еес]?[оосу]?', re.IGNORECASE),
    "хуйня": re.compile(r'[хx][уy][йy][нn][яя]', re.IGNORECASE),
    "хуес": re.compile(r'ху[еи]с[оа]*', re.IGNORECASE),
    "хуйло": re.compile(r'х[уу][йи]л[оы]', re.IGNORECASE),
    "нахуй": re.compile(r'нах[ую][йи]*', re.IGNORECASE),
    "пошёл нахуй": re.compile(r'пош[еє]л.*нах[ую][йи]', re.IGNORECASE),
    
    "пизда": re.compile(r'\bп[ие]зд[а-яё]*\b', re.IGNORECASE),
    "пиздец": re.compile(r'[пp][иi1l][зz3][дd][еe][цc]', re.IGNORECASE),
    "пиздабол": re.compile(r'[пp][иi1l][зz3][дd][аa@][бb6][оo0][лl]', re.IGNORECASE),
    "запизде": re.compile(r'зап[ие]зд[ее]*', re.IGNORECASE),
    "пиздет": re.compile(r'\bп[еи]зд[еи]т[еь]*\b|п[еи]зд[еи]т[еь]*', re.IGNORECASE),
    "пиздеол": re.compile(r'пизд[еи][юо]л', re.IGNORECASE),
    "пиздост": re.compile(r'пиздост[оую]*', re.IGNORECASE),
    "пиздострад": re.compile(r'пиздостра[д]*', re.IGNORECASE),
    "пизд": re.compile(r'[пб][іі][зз3][дд][еецак]?[ау]?', re.IGNORECASE),
    
    "гондон": re.compile(r'[гg][оo0][нn][дd][оo0][нn]', re.IGNORECASE),
    "гандон": re.compile(r'\bганд[оон]*\b|[\b\s]гандон[ау\s.!?]+', re.IGNORECASE),
    "резингандон": re.compile(r'рез[іі]нганд[оон]', re.IGNORECASE),
    
    "сука": re.compile(r'[сc][уy][кk][аa@]', re.IGNORECASE),
    "сукин": re.compile(r'сук[ау][ны]*', re.IGNORECASE),
    "сукины дети": re.compile(r'сукин[ау]дети', re.IGNORECASE),
    "сучка": re.compile(r'сучк[ау]', re.IGNORECASE),
    "сучар": re.compile(r'сучар[н]*', re.IGNORECASE),
    
    "заебись": re.compile(r'[зz3][аa@][еe][бb6][иi1l][сc][ьь]', re.IGNORECASE),
    "охуеть": re.compile(r'[оo0][хx][уy][еe][тt][ьь]', re.IGNORECASE),
    "охуел": re.compile(r'[оo0][хx][уy][еe][лl]', re.IGNORECASE),
    "похуй": re.compile(r'пох[еуи][рст]*', re.IGNORECASE),
    "похуист": re.compile(r'поху[иі]ст', re.IGNORECASE),
    
    # Дополнительные матерные слова
    "бздеть": re.compile(r'\bбзд[ееть]*\b', re.IGNORECASE),
    "оббздеть": re.compile(r'об[оі]бзд[ееть]*', re.IGNORECASE),
    "елдак": re.compile(r'\bелд[ау][к]*\b', re.IGNORECASE),
    "говно": re.compile(r'\bговн[оую]*\b', re.IGNORECASE),
    "обосрать": re.compile(r'об[оі]ср[ау][ться]*', re.IGNORECASE),
    "жопа": re.compile(r'\bжоп[ау][н]*\b', re.IGNORECASE),
    "поджоп": re.compile(r'поджоп[н]*', re.IGNORECASE),
    "манда": re.compile(r'\bм[аанд][да]*\b', re.IGNORECASE),
    "мандавошка": re.compile(r'мандавош[к]*', re.IGNORECASE),
    "мудак": re.compile(r'\bмуд[а-яё]+[кн]*\b', re.IGNORECASE),
    "пердеть": re.compile(r'\bперд[еетьу]*\b', re.IGNORECASE),
    "пердун": re.compile(r'пердун', re.IGNORECASE),
    "срать": re.compile(r'\bср[ау][ться]*\b', re.IGNORECASE),
    "срака": re.compile(r'срака', re.IGNORECASE),
    "ссать": re.compile(r'\bсс[ау][ни]*\b', re.IGNORECASE),
    "ссанина": re.compile(r'ссанина', re.IGNORECASE),
    "шлюха": re.compile(r'\bшлюх[ау]*\b', re.IGNORECASE),
    "шлюхнуть": re.compile(r'шлюх[ну]*', re.IGNORECASE),
    "пидор": re.compile(r'\bп[иі]дор[аас]*\b', re.IGNORECASE),
    "педик": re.compile(r'п[еи]д[иі]к', re.IGNORECASE),
    "педофил": re.compile(r'\bп[еи]д[оо]ф[иі]л\b', re.IGNORECASE),
    "педофила": re.compile(r'педоф[иі]л[ау]', re.IGNORECASE),
    "наебал": re.compile(r'наебал[оу]', re.IGNORECASE),
    "чмо": re.compile(r'\bчм[оу]\b', re.IGNORECASE),
    "чмошник": re.compile(r'чмошник', re.IGNORECASE),
    "залупа": re.compile(r'\bзалуп[ау]\b', re.IGNORECASE),
    "залупоглаз": re.compile(r'залупогл[ааз]', re.IGNORECASE),
    "петух": re.compile(r'\bп[еи]тух[ау]\b', re.IGNORECASE),
    "муда": re.compile(r'[\b\s]муд[ау\s.!?]+', re.IGNORECASE),
    "ебать": re.compile(r'\b[её]б[а-яё]*[ая]ть\b', re.IGNORECASE),
    "тварь": re.compile(r'\bтвар[ьюи][ш]*\b', re.IGNORECASE),
    "тварьщи": re.compile(r'твар[ьюи]щ', re.IGNORECASE),
    "придурок": re.compile(r'\bп[рз]идурок\b', re.IGNORECASE),
    "придурка": re.compile(r'придур[ко]*', re.IGNORECASE),
    "шизо": re.compile(r'\bш[иы]з[оа]\b', re.IGNORECASE),
    "шизофр": re.compile(r'шиз[оа][фд]р', re.IGNORECASE),
    "плед": re.compile(r'\b[пб]л[еи]д[оау]\b', re.IGNORECASE),
    "кастрат": re.compile(r'\bкастр[аат][т]*\b', re.IGNORECASE),
    "кастрату": re.compile(r'кастр[оую]*', re.IGNORECASE),
    "свинья": re.compile(r'\bсвин[ьяью][тусн]*\b', re.IGNORECASE),
    "свинотус": re.compile(r'свин[оо]тус', re.IGNORECASE),
    "малпай": re.compile(r'\b[мж]а[лч]па[йи]\b', re.IGNORECASE),
    "малпайй": re.compile(r'мал[ч]па[йи]й', re.IGNORECASE),
    "урод": re.compile(r'\bур[оо]д[лг][ив]*\b', re.IGNORECASE),
    "уродливый": re.compile(r'урод[лг]ив[ый]', re.IGNORECASE),
    "дерьмо": re.compile(r'\bдер[ьм][омо]*\b', re.IGNORECASE),
    "дерьмовина": re.compile(r'дер[ьм]овин[а-яё]*', re.IGNORECASE),
    "поздило": re.compile(r'\bп[оі]зд[еи]л[оы]\b', re.IGNORECASE),
    "поздизо": re.compile(r'поздиз[оы]', re.IGNORECASE),
    "падла": re.compile(r'\bпад[л][ау]\b', re.IGNORECASE),
    "падлюга": re.compile(r'пад[л]юг[ау]', re.IGNORECASE),
    "тормоз": re.compile(r'\bторм[оо]з[ил]*\b', re.IGNORECASE),
    "тормозил": re.compile(r'тормоз[иіл]', re.IGNORECASE),
    "хрен": re.compile(r'\bхр[еен][овину]*\b', re.IGNORECASE),
    "хреновина": re.compile(r'хр[еен]овина', re.IGNORECASE),
}

# Регулярные выражения для английских матерных слов
# Учитывают возможные замены букв (o на 0, a на @, i на 1, и т.д.) и множественные повторы
ENGLISH_PROFANITY_PATTERNS: Dict[str, Pattern] = {
    "fuck": re.compile(r'f+u+c+k+', re.IGNORECASE),
    "fuck off": re.compile(r'f+u+c+k+\s*o+f+f+', re.IGNORECASE),
    "fuck you": re.compile(r'f+u+c+k+\s*y+o+u+', re.IGNORECASE),
    "fucking": re.compile(r'f+u+c+k+i+n+g+', re.IGNORECASE),
    "fucked": re.compile(r'f+u+c+k+e+d+', re.IGNORECASE),
    "fucker": re.compile(r'f+u+c+k+e+r+', re.IGNORECASE),
    "shit": re.compile(r's+h+i+t+', re.IGNORECASE),
    "shitting": re.compile(r's+h+i+t+t+i+n+g+', re.IGNORECASE),
    "damn": re.compile(r'd+a+m+n+', re.IGNORECASE),
    "bitch": re.compile(r'b+i+t+c+h+', re.IGNORECASE),
    "bitches": re.compile(r'b+i+t+c+h+e+s+', re.IGNORECASE),
    "asshole": re.compile(r'a+s+s+h+o+l+e+', re.IGNORECASE),
    "ass": re.compile(r'\ba+s+s+\b', re.IGNORECASE),  # \b для границ слова, чтобы не ловить "class", "pass" и т.д.
    "bastard": re.compile(r'b+a+s+t+a+r+d+', re.IGNORECASE),
    "crap": re.compile(r'c+r+a+p+', re.IGNORECASE),
    "piss off": re.compile(r'p+i+s+s+\s*o+f+f+', re.IGNORECASE),
    "piss": re.compile(r'p+i+s+s+', re.IGNORECASE),
    "dick": re.compile(r'd+i+c+k+', re.IGNORECASE),
    "cock": re.compile(r'c+o+c+k+', re.IGNORECASE),
    "pussy": re.compile(r'p+u+s+s+y+', re.IGNORECASE),
    "whore": re.compile(r'w+h+o+r+e+', re.IGNORECASE),
    "slut": re.compile(r's+l+u+t+', re.IGNORECASE),
    "motherfucker": re.compile(r'm+o+t+h+e+r+f+u+c+k+e+r+', re.IGNORECASE),
    "motherfucking": re.compile(r'm+o+t+h+e+r+f+u+c+k+i+n+g+', re.IGNORECASE),
    "son of a bitch": re.compile(r's+o+n+\s+o+f+\s+a+\s+b+i+t+c+h+', re.IGNORECASE),
    "bullshit": re.compile(r'b+u+l+l+s+h+i+t+', re.IGNORECASE),
    "damn it": re.compile(r'd+a+m+n+\s+i+t+', re.IGNORECASE),
    "goddamn": re.compile(r'g+o+d+d+a+m+n+', re.IGNORECASE),
    "hell": re.compile(r'\bh+e+l+l+\b', re.IGNORECASE),  # \b для границ слова
}


def create_regex_from_phrase(phrase: str) -> Pattern:
    """
    Создает регулярное выражение из фразы, учитывая возможные замены букв.
    
    :param phrase: Фраза для создания регулярного выражения
    :return: Скомпилированное регулярное выражение
    """
    # Маппинг букв на возможные замены (для обхода фильтров)
    char_map = {
        'a': '[аa@4]',
        'б': '[бb6]',
        'в': '[вv]',
        'г': '[гg]',
        'д': '[дd]',
        'е': '[еe]',
        'ё': '[ёe]',
        'ж': '[жz]',
        'з': '[зz3]',
        'и': '[иi1l]',
        'й': '[йy]',
        'к': '[кk]',
        'л': '[лl]',
        'м': '[мm]',
        'н': '[нn]',
        'о': '[оo0]',
        'п': '[пp]',
        'р': '[рr]',
        'с': '[сc]',
        'т': '[тt]',
        'у': '[уy]',
        'ф': '[фf]',
        'х': '[хx]',
        'ц': '[цc]',
        'ч': '[чch]',
        'ш': '[шsh]',
        'щ': '[щsch]',
        'ъ': '[ъ]',
        'ы': '[ыy]',
        'ь': '[ьь]',
        'э': '[эe]',
        'ю': '[юyu]',
        'я': '[яya]',
        ' ': r'\s*',  # Пробелы могут быть заменены на любые пробельные символы
    }
    
    # Строим регулярное выражение
    pattern_parts = []
    for char in phrase.lower():
        if char in char_map:
            pattern_parts.append(char_map[char])
        elif char.isalnum():
            # Для английских букв, которых нет в маппинге, используем как есть с возможными повторами
            pattern_parts.append(f'{re.escape(char)}+')
        else:
            # Для знаков препинания и других символов
            pattern_parts.append(re.escape(char))
    
    pattern = ''.join(pattern_parts)
    return re.compile(pattern, re.IGNORECASE)

async def check_message_for_blacklist(text: str) -> bool:
    """
    Проверяет, содержит ли текст запрещённые выражения из blacklist.
    Использует регулярные выражения для более надежного обнаружения матерных слов.
    
    :param text: Текст для проверки
    :return: True если найдено нарушение, False если все ОК
    """
    if not text:
        return False
    
    text_lower = text.lower()
    logger.info(f"🔍 Проверяем blacklist: текст='{text[:100]}...'")
    
    # 1. Проверяем предопределенные регулярные выражения для матерных слов
    # Сначала проверяем русские матерные слова
    for word, pattern in RUSSIAN_PROFANITY_PATTERNS.items():
        if pattern.search(text):
            logger.warning(f"⚠️ НАЙДЕНО НАРУШЕНИЕ! Русское матерное слово '{word}' найдено в тексте (regex)")
            return True
    
    # Затем проверяем английские матерные слова
    for word, pattern in ENGLISH_PROFANITY_PATTERNS.items():
        if pattern.search(text):
            logger.warning(f"⚠️ НАЙДЕНО НАРУШЕНИЕ! Английское матерное слово '{word}' найдено в тексте (regex)")
            return True
    
    # 2. Проверяем фразы из базы данных (blacklist)
    async with get_async_session() as session:
        blacklist = await BlacklistRepository.get_all(session)
        logger.info(f"   Проверяем фразы из БД blacklist: {len(blacklist)} фраз")
        
        for item in blacklist:
            phrase = item.phrase.strip()
            if not phrase:
                continue
            
            # Создаем регулярное выражение из фразы
            phrase_lower = phrase.lower()
            try:
                # Сначала пробуем простое совпадение (для обратной совместимости)
                if phrase_lower in text_lower:
                    logger.warning(f"⚠️ НАЙДЕНО НАРУШЕНИЕ! Фраза из БД '{phrase}' найдена в тексте (простой поиск)")
                    return True
                
                # Затем пробуем регулярное выражение
                regex_pattern = create_regex_from_phrase(phrase)
                if regex_pattern.search(text):
                    logger.warning(f"⚠️ НАЙДЕНО НАРУШЕНИЕ! Фраза из БД '{phrase}' найдена в тексте (regex)")
                    return True
            except Exception as e:
                logger.error(f"⚠️ Ошибка при проверке фразы '{phrase}': {e}")
                # В случае ошибки используем простой поиск
                if phrase_lower in text_lower:
                    logger.warning(f"⚠️ НАЙДЕНО НАРУШЕНИЕ! Фраза из БД '{phrase}' найдена в тексте (fallback)")
                    return True
    
    logger.info(f"✅ Проверка blacklist завершена, нарушений не найдено")
    return False

async def add_to_blacklist(phrase: str, admin_id: int = None) -> bool:
    """Добавить фразу в черный список"""
    async with get_async_session() as session:
        existing = await BlacklistRepository.get_by_phrase(session, phrase)
        if existing:
            return False
        
        from app.infrastructure.db.models import BlacklistItem
        item = BlacklistItem(phrase=phrase, added_by=admin_id)
        await BlacklistRepository.add(session, item)
        
        from app.infrastructure.db.repositories import LogRepository
        from app.infrastructure.db.models import Log
        await LogRepository.add(session, Log(
            event_type="blacklist_added",
            user_id=admin_id,
            message=f"Добавлено в blacklist: {phrase}"
        ))
        return True

async def remove_from_blacklist(phrase: str, admin_id: int = None) -> bool:
    """Удалить фразу из черного списка"""
    async with get_async_session() as session:
        await BlacklistRepository.delete_by_phrase(session, phrase)
        
        from app.infrastructure.db.repositories import LogRepository
        from app.infrastructure.db.models import Log
        await LogRepository.add(session, Log(
            event_type="blacklist_removed",
            user_id=admin_id,
            message=f"Удалено из blacklist: {phrase}"
        ))
        return True

async def get_all_blacklist() -> List:
    """Получить весь черный список"""
    async with get_async_session() as session:
        return await BlacklistRepository.get_all(session)
