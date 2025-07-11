import re
from phonemizer import backend
from typing import List


class Tokenizer:
    def __init__(self):
        self.VOCAB = self._get_vocab()
        self.phonemizers = {
            'en-us': backend.EspeakBackend(language='en-us', preserve_punctuation=True, with_stress=True),
            'en-gb': backend.EspeakBackend(language='en-gb', preserve_punctuation=True, with_stress=True),
        }

    @staticmethod
    def _get_vocab():
        """
        Generates a mapping of symbols to integer indices for tokenization.

        Returns:
            dict: A dictionary where keys are symbols and values are unique integer indices.
        """
        # Define the symbols
        _pad = "$"
        _punctuation = ';:,.!?¡¿—…"«»“” '
        _letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        _letters_ipa = (
            "ɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞↓↑→↗↘'̩'ᵻ"
        )
        symbols = [_pad] + list(_punctuation) + list(_letters) + list(_letters_ipa)

        # Create a dictionary mapping each symbol to its index
        return {symbol: index for index, symbol in enumerate(symbols)}

    @staticmethod
    def split_num(num: re.Match) -> str:
        """
        Processes numeric strings, formatting them as time, years, or other representations.

        Args:
            num (re.Match): A regex match object representing the numeric string.

        Returns:
            str: A formatted string based on the numeric input.
        """
        num = num.group()

        # Handle time (e.g., "12:30")
        if ':' in num:
            hours, minutes = map(int, num.split(':'))
            if minutes == 0:
                return f"{hours} o'clock"
            elif minutes < 10:
                return f'{hours} oh {minutes}'
            return f'{hours} {minutes}'

        # Handle years or general numeric cases
        year = int(num[:4])
        if year < 1100 or year % 1000 < 10:
            return num

        left, right = num[:2], int(num[2:4])
        suffix = 's' if num.endswith('s') else ''

        # Format years
        if 100 <= year % 1000 <= 999:
            if right == 0:
                return f'{left} hundred{suffix}'
            elif right < 10:
                return f'{left} oh {right}{suffix}'
        return f'{left} {right}{suffix}'

    @staticmethod
    def flip_money(match: re.Match) -> str:
        """
        Converts monetary values to a textual representation.

        Args:
            m (re.Match): A regex match object representing the monetary value.

        Returns:
            str: A formatted string describing the monetary value.
        """
        m = m.group()
        currency = 'dollar' if m[0] == '$' else 'pound'

        # Handle whole amounts (e.g., "$10", "£20")
        if '.' not in m:
            singular = '' if m[1:] == '1' else 's'
            return f'{m[1:]} {currency}{singular}'

        # Handle amounts with decimals (e.g., "$10.50", "£5.25")
        whole, cents = m[1:].split('.')
        singular = '' if whole == '1' else 's'
        cents = int(cents.ljust(2, '0'))  # Ensure 2 decimal places
        coins = f"cent{'' if cents == 1 else 's'}" if m[0] == '$' else ('penny' if cents == 1 else 'pence')
        return f'{whole} {currency}{singular} and {cents} {coins}'

    @staticmethod
    def point_num(match):
        whole, fractional = match.group().split('.')
        return ' point '.join([whole, ' '.join(fractional)])

    def normalize_text(self, text: str) -> str:
        """
        Normalizes input text by replacing special characters, punctuation, and applying custom transformations.

        Args:
            text (str): Input text to normalize.

        Returns:
            str: Normalized text.
        """
        # Replace specific characters with standardized versions
        replacements = {
            chr(8216): "'",  # Left single quotation mark
            chr(8217): "'",  # Right single quotation mark
            '«': chr(8220),  # Left double angle quotation mark to left double quotation mark
            '»': chr(8221),  # Right double angle quotation mark to right double quotation mark
            chr(8220): '"',  # Left double quotation mark
            chr(8221): '"',  # Right double quotation mark
            '(': '«',        # Replace parentheses with angle quotation marks
            ')': '»'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Replace punctuation and add spaces
        punctuation_replacements = {
            '、': ',',
            '。': '.',
            '！': '!',
            '，': ',',
            '：': ':',
            '；': ';',
            '？': '?',
        }
        for old, new in punctuation_replacements.items():
            text = text.replace(old, new + ' ')

        # Apply regex-based replacements
        text = re.sub(r'[^\S\n]', ' ', text)
        text = re.sub(r'  +', ' ', text)
        text = re.sub(r'(?<=\n) +(?=\n)', '', text)

        # Expand abbreviations and handle special cases
        abbreviation_patterns = [
            (r'\bD[Rr]\.(?= [A-Z])', 'Doctor'),
            (r'\b(?:Mr\.|MR\.(?= [A-Z]))', 'Mister'),
            (r'\b(?:Ms\.|MS\.(?= [A-Z]))', 'Miss'),
            (r'\b(?:Mrs\.|MRS\.(?= [A-Z]))', 'Mrs'),
            (r'\betc\.(?! [A-Z])', 'etc'),
            (r'(?i)\b(y)eah?\b', r"\1e'a"),
        ]
        for pattern, replacement in abbreviation_patterns:
            text = re.sub(pattern, replacement, text)

        # Handle numbers and monetary values
        text = re.sub(r'\d*\.\d+|\b\d{4}s?\b|(?<!:)\b(?:[1-9]|1[0-2]):[0-5]\d\b(?!:)', self.split_num, text)
        text = re.sub(r'(?<=\d),(?=\d)', '', text)  # Remove commas from numbers
        text = re.sub(
            r'(?i)[$£]\d+(?:\.\d+)?(?: hundred| thousand| (?:[bm]|tr)illion)*\b|[$£]\d+\.\d\d?\b',
            self.flip_money,
            text
        )
        text = re.sub(r'\d*\.\d+', self.point_num, text)
        text = re.sub(r'(?<=\d)-(?=\d)', ' to ', text)

        # Handle possessives and specific letter cases
        text = re.sub(r'(?<=\d)S', ' S', text)
        text = re.sub(r"(?<=[BCDFGHJ-NP-TV-Z])'?s\b", "'S", text)
        text = re.sub(r"(?<=X')S\b", 's', text)

        # Handle abbreviations with dots
        text = re.sub(r'(?:[A-Za-z]\.){2,} [a-z]', lambda m: m.group().replace('.', '-'), text)
        text = re.sub(r'(?i)(?<=[A-Z])\.(?=[A-Z])', '-', text)

        return text.strip()

    def tokenize(self, phonemes: str) -> List[int]:
        """
        Tokenizes a given string into a list of indices based on VOCAB.

        Args:
            text (str): Input string to tokenize.

        Returns:
            list: A list of integer indices corresponding to the characters in the input string.
        """
        return [self.VOCAB[x] for x in phonemes if x in self.VOCAB]

    def phonemize(self, text: str, lang: str = 'en-us', normalize: bool = True) -> str:
        """
        Converts text to phonemes using the specified language phonemizer and applies normalization.

        Args:
            text (str): Input text to be phonemized.
            lang (str): Language identifier ('en-us' or 'en-gb') for selecting the phonemizer.
            normalize (bool): Whether to normalize the text before phonemization.

        Returns:
            str: A processed string of phonemes.
        """
        # Normalize text if required
        if normalize:
            text = self.normalize_text(text)

        # Generate phonemes using the specified phonemizer
        if lang not in self.phonemizers:
            print(f"Language '{lang}' not supported. Defaulting to 'en-us'.")
            lang = 'en-us'

        phonemes = self.phonemizers[lang].phonemize([text])
        phonemes = phonemes[0] if phonemes else ''

        # Apply custom phoneme replacements
        replacements = {
            'kəkˈoːɹoʊ': 'kˈoʊkəɹoʊ',
            'kəkˈɔːɹəʊ': 'kˈəʊkəɹəʊ',
            'ʲ': 'j',
            'r': 'ɹ',
            'x': 'k',
            'ɬ': 'l',
        }
        for old, new in replacements.items():
            phonemes = phonemes.replace(old, new)

        # Apply regex-based replacements
        phonemes = re.sub(r'(?<=[a-zɹː])(?=hˈʌndɹɪd)', ' ', phonemes)
        phonemes = re.sub(r' z(?=[;:,.!?¡¿—…"«»“” ]|$)', 'z', phonemes)

        # Additional language-specific rules
        if lang == 'a':
            phonemes = re.sub(r'(?<=nˈaɪn)ti(?!ː)', 'di', phonemes)

        # Filter out characters not in VOCAB
        phonemes = ''.join(filter(lambda p: p in self.VOCAB, phonemes))

        return phonemes.strip()
