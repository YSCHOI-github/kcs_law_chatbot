import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, List, Optional

try:
    from pdfminer.high_level import extract_text
except ModuleNotFoundError:  # pragma: no cover
    extract_text = None

from lawapi import (
    _combine_structure_titles_standalone,
    _extract_structure_title_standalone,
)


_CHAPTER_PATTERN = re.compile(r"^제\s*[\d가-힣]+\s*장")
_SECTION_PATTERN = re.compile(r"^제\s*[\d가-힣]+\s*절")
_SUBSECTION_PATTERN = re.compile(r"^제\s*[\d가-힣]+\s*관")
_ARTICLE_PATTERN = re.compile(r"제\s*(?P<number>[\d]+(?:-[\d]+)?(?:의[\d]+)*)\s*조(?:의(?P<sub>[\d]+))?\s*\((?P<title>[^)]+)\)(?P<rest>.*)")
_ANNEX_PATTERN = re.compile(r"^\s*[【\[]?\s*부\s*칙\s*[】\]]?")


@dataclass
class _ArticleBuffer:
    number: str
    title: str
    content_lines: List[str] = field(default_factory=list)

    def extend_with(self, text: str) -> None:
        self.content_lines.append(text)

    def to_dict(self) -> dict:
        content = "\n".join(self.content_lines).strip()
        return {
            "조번호": self.number,
            "제목": self.title,
            "내용": content,
        }


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.replace("\u3000", " ").split())


def _load_pdf_text(path: Path) -> str:
    if extract_text is None:
        raise RuntimeError("pdfminer.six 모듈을 찾을 수 없습니다. PDF 처리를 위해 설치가 필요합니다.")
    return extract_text(str(path))


def _load_txt_text(path: Path) -> str:
    encodings = ("utf-8", "cp949")
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _normalize_article_number(raw_number: str) -> str:
    normalized = raw_number.replace(" ", "").lstrip("0")
    return normalized or "0"


def _is_sentence_title(title: str) -> bool:
    """
    괄호 안 제목이 문장 형식인지 판별 (adminapi.py 로직 참고)

    문장형 제목은 실제 조문이 아닌 참조문일 가능성이 높음
    예시: "관세를 부과한다", "징수처리한다"
    """
    sentence_endings = [
        '한다', '하여야', '해야', '된다', '받는다', '따른다',
        '의한다', '정한다', '본다', '처리한다', '관리한다',
        '이다', '것이다', '않는다', '같다', '다르다'
    ]

    title = title.strip()
    for ending in sentence_endings:
        if title.endswith(ending):
            return True
    return False


def _is_article_reference(article_match, full_line: str) -> bool:
    """
    조문 참조 문장인지 판별 (adminapi.py의 is_article_reference 로직 참고)

    예시 참조 패턴:
    - "제14조(관세 등의 부과)에 따라 수입물품에 부과되는..."
    - "제37조(특허) 및 제38조의 규정"
    - "제51조부터 제67조까지"
    """
    rest = article_match.group("rest").strip()

    # 1. 나열어 패턴 (정규표현식)
    list_patterns = [
        r'^\s*및\s*',
        r'^\s*,\s*',
        r'^\s*또는\s*',
        r'^\s*내지\s*',
        r'^\s*부터\s*',
        r'^\s*까지\s*',
        r'^\s*ㆍ\s*',
        r'^\s*~\s*',
    ]
    for pattern in list_patterns:
        if re.search(pattern, rest):
            return True

    # 2. 조사나 연결어 패턴
    connective_patterns = [
        r'^\s*의\s*규정',
        r'^\s*에\s*따라',
        r'^\s*에\s*의하여',
        r'^\s*을\s*준용',
        r'^\s*를\s*준용',
        r'^\s*에\s*의한',
        r'^\s*에\s*규정',
        r'^\s*의\s*개정',
        r'^\s*에\s*해당',
        r'^\s*에\s*따른',
        r'^\s*을\s*적용',
        r'^\s*를\s*적용',
        r'^\s*의\s*적용',
        r'^\s*에서\s*정한',
        r'^\s*의\s+',
        r'^\s*을\s+',
        r'^\s*를\s+',
        r'^\s*에\s+',
        r'^\s*에서\s+',
    ]
    for pattern in connective_patterns:
        if re.search(pattern, rest):
            return True

    # 3. 세부항목 인용 패턴 (제X항, 제X호)
    if re.search(r'^\s*제\s*\d+\s*[항호]', rest):
        return True

    return False


def _finalize_article(article: Optional[_ArticleBuffer], results: List[dict]) -> None:
    if article is not None:
        results.append(article.to_dict())


def parse_text_to_articles(text: str) -> List[dict]:
    current_chapter = ""
    current_section = ""
    current_subsection = ""
    articles: List[dict] = []
    current_article: Optional[_ArticleBuffer] = None

    for raw_line in text.splitlines():
        stripped_line = raw_line.strip()
        if not stripped_line:
            if current_article:
                current_article.extend_with("")
            continue

        if _ANNEX_PATTERN.match(stripped_line):
            _finalize_article(current_article, articles)
            current_article = None
            break

        if _CHAPTER_PATTERN.match(stripped_line):
            current_chapter = _extract_structure_title_standalone(stripped_line)
            current_section = ""
            current_subsection = ""
            _finalize_article(current_article, articles)
            current_article = None
            continue

        if _SECTION_PATTERN.match(stripped_line):
            current_section = _extract_structure_title_standalone(stripped_line)
            current_subsection = ""
            _finalize_article(current_article, articles)
            current_article = None
            continue

        if _SUBSECTION_PATTERN.match(stripped_line):
            current_subsection = _extract_structure_title_standalone(stripped_line)
            _finalize_article(current_article, articles)
            current_article = None
            continue

        article_match = _ARTICLE_PATTERN.match(stripped_line)
        if article_match:
            rest_segment = article_match.group("rest").strip()
            prefix = rest_segment.split("(", 1)[0].strip()
            if prefix.startswith("제") and any(marker in prefix for marker in ("항", "호", "목")):
                if current_article:
                    current_article.extend_with(stripped_line)
                continue

            # 제목 추출 (패턴에서 캡처됨)
            title = article_match.group("title").strip()

            # 1. 문장형 제목 필터링 (괄호 안 검증)
            if _is_sentence_title(title):
                if current_article:
                    current_article.extend_with(stripped_line)
                continue

            # 2. 참조 문장 필터링 (괄호 뒤 검증)
            if _is_article_reference(article_match, stripped_line):
                if current_article:
                    current_article.extend_with(stripped_line)
                continue

            inline_content = rest_segment.strip()

            # 조문번호 생성 (number + sub 결합)
            number = _normalize_article_number(article_match.group("number"))
            sub = article_match.group("sub")
            if sub:
                number = f"{number}의{sub}"
            combined_title = _combine_structure_titles_standalone(
                current_chapter, current_section, current_subsection, title
            )
            parts = [part.strip() for part in combined_title.split(",") if part.strip()]
            unique_parts = []
            for part in parts:
                if part not in unique_parts:
                    unique_parts.append(part)
            combined_title = ", ".join(unique_parts)

            _finalize_article(current_article, articles)
            current_article = _ArticleBuffer(
                number=number,
                title=_normalize_whitespace(combined_title),
            )

            if inline_content:
                current_article.extend_with(inline_content.strip())
            continue

        if current_article:
            current_article.extend_with(stripped_line)

    _finalize_article(current_article, articles)
    return articles


def convert_text_to_json(text: str) -> List[dict]:
    return parse_text_to_articles(text)


def convert_path_to_json(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    if path.suffix.lower() == ".pdf":
        text = _load_pdf_text(path)
    elif path.suffix.lower() == ".txt":
        text = _load_txt_text(path)
    else:
        raise ValueError("지원하지 않는 파일 형식입니다. pdf와 txt만 허용됩니다.")

    return convert_text_to_json(text)


def convert_file_to_json(file: BinaryIO, filename: str) -> List[dict]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        if extract_text is None:
            raise RuntimeError("pdfminer.six 모듈을 찾을 수 없습니다. PDF 처리를 위해 설치가 필요합니다.")
        with io.BytesIO(file.read()) as buffer:
            text = extract_text(buffer)
    elif suffix == ".txt":
        data = file.read()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("cp949", errors="ignore")
    else:
        raise ValueError("지원하지 않는 파일 형식입니다. pdf와 txt만 허용됩니다.")

    return convert_text_to_json(text)
