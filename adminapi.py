import requests
import xml.etree.ElementTree as ET
import json
import re
from typing import Optional, Tuple, List, Dict, Set
import streamlit as st

class NumberPredictor:
    """번호 예측 엔진"""
    
    @staticmethod
    def parse_number(number_str: str) -> Dict:
        """번호 파싱"""
        # 제1-5조의2 패턴
        if match := re.match(r'제(\d+)-(\d+)([장절관조])의(\d+)', number_str):
            return {
                "type": match.group(3),
                "main": int(match.group(1)),
                "dash": int(match.group(2)),
                "sub": int(match.group(4))
            }
        # 제1-5조 패턴
        elif match := re.match(r'제(\d+)-(\d+)([장절관조])', number_str):
            return {
                "type": match.group(3),
                "main": int(match.group(1)),
                "dash": int(match.group(2)),
                "sub": None
            }
        # 제3조의2 패턴
        elif match := re.match(r'제(\d+)([장절관조])의(\d+)', number_str):
            return {
                "type": match.group(2),
                "main": int(match.group(1)),
                "dash": None,
                "sub": int(match.group(3))
            }
        # 제3조 패턴
        elif match := re.match(r'제(\d+)([장절관조])', number_str):
            return {
                "type": match.group(2),
                "main": int(match.group(1)),
                "dash": None,
                "sub": None
            }
        return None
    
    @staticmethod
    def predict_next_numbers(current_number: str) -> List[str]:
        """다음 가능한 번호들 예측"""
        parsed = NumberPredictor.parse_number(current_number)
        if not parsed:
            return []
        
        next_numbers = []
        t = parsed["type"]
        main = parsed["main"]
        dash = parsed["dash"]
        sub = parsed["sub"]
        
        if dash and sub:  # 제1-5조의2
            next_numbers.extend([
                f"제{main}-{dash}{t}의{sub + 1}",
                f"제{main}-{dash + 1}{t}",
                f"제{main + 1}-1{t}"
            ])
        elif dash:  # 제1-5조
            next_numbers.extend([
                f"제{main}-{dash}{t}의2",
                f"제{main}-{dash + 1}{t}",
                f"제{main + 1}-1{t}"
            ])
        elif sub:  # 제3조의2
            next_numbers.extend([
                f"제{main}{t}의{sub + 1}",
                f"제{main + 1}{t}"
            ])
        else:  # 제3조
            next_numbers.extend([
                f"제{main}{t}의2",
                f"제{main + 1}{t}"
            ])
        
        return next_numbers

class SimpleArticleParser:
    """1단계: 단순 조문 파싱"""
    
    def __init__(self):
        self.predictor = NumberPredictor()
    
    def preprocess_text(self, text: str) -> str:
        """텍스트 전처리: <> 안의 문자열 삭제 (<삭 제>는 제외)"""
        # <삭 제>를 제외한 다른 <> 패턴 삭제
        cleaned_text = re.sub(r'<(?!삭\s*제>)[^>]*>', '', text)
        return cleaned_text
    
    def is_article_reference(self, text: str, match_start: int) -> bool:
        """조문 패턴이 다른 조문의 인용인지 판별"""
        # 조문 괄호 끝 위치 찾기 (제X조(제목) 다음 위치)
        match_end = text.find(')', match_start)
        if match_end == -1:
            return False
        
        # 조문 패턴 이후 25자를 확인
        after_text = text[match_end+1:match_end+26]
        
        # 1. 나열 단어 패턴 (조문 패턴 이후에 오는 경우)
        list_patterns = [r'^\s*및\s*', r'^\s*,\s*', r'^\s*또는\s*', r'^\s*내지\s*', r'^\s*부터\s*']
        for pattern in list_patterns:
            if re.search(pattern, after_text):
                return True
        
        # 2. 조사나 연결어 패턴 (조문 번호 바로 뒤에 오는 경우)
        connective_patterns = [
            r'^\s*의\s*규정', r'^\s*에\s*따라', r'^\s*에\s*따른', 
            r'^\s*의\s*규정에', r'^\s*단서의', r'^\s*에서', 
            r'^\s*을\s*', r'^\s*를\s*'
        ]
        for pattern in connective_patterns:
            if re.search(pattern, after_text):
                return True
        
        # 3. 세부항목 인용 패턴
        if re.search(r'^\s*제\s*\d+\s*[항호]', after_text):
            return True
        
        return False
    
    def is_sentence_title(self, title: str) -> bool:
        """괄호 안 제목이 문장 형식인지 판별"""
        if not title:
            return False
        
        # 동사형 종결어미로 끝나는 경우
        sentence_endings = [
            '한다', '하여야', '해야', '된다', '받는다', '따른다',
            '의한다', '정한다', '본다', '처리한다', '관리한다'
        ]
        
        for ending in sentence_endings:
            if title.endswith(ending):
                return True
        
        return False
    
    def parse_articles_only(self, text: str) -> List[Dict]:
        """조문만 단순 파싱"""
        text = self.preprocess_text(text)
        
        # 조문 패턴: 제목이 괄호 안에
        pattern = r'(제\s*\d+(?:-\d+)?\s*조(?:의\d+)?)\s*\(([^)]+)\)'
        
        articles = []
        all_matches = list(re.finditer(pattern, text))
        valid_matches = []
        
        print(f"1단계 - 조문 패턴 {len(all_matches)}개 발견, 필터링 중...")
        
        # 유효한 조문 매치만 필터링
        for match in all_matches:
            title = match.group(2).strip()
            
            # 1. 인용 패턴 체크
            if self.is_article_reference(text, match.start()):
                continue
            
            # 2. 문장형 제목 체크
            if self.is_sentence_title(title):
                continue
            
            valid_matches.append(match)
        
        print(f"1단계 - 유효한 조문 {len(valid_matches)}개 추출")
        
        for i, match in enumerate(valid_matches):
            start_pos = match.start()
            end_pos = valid_matches[i + 1].start() if i + 1 < len(valid_matches) else len(text)
            
            number_str = re.sub(r'\s+', '', match.group(1))
            title = match.group(2).strip()
            content = text[start_pos:end_pos].strip()
            
            # 제목 부분 제거하여 내용만 추출
            content = re.sub(f'{re.escape(number_str)}\\s*\\([^)]+\\)', '', content, count=1).strip()
            
            articles.append({
                "조번호": number_str,
                "제목": title,
                "내용": content
            })
        
        return articles

class HierarchyExtractor:
    """2단계: 계층구조 추출기"""
    
    def __init__(self):
        self.predictor = NumberPredictor()
    
    def preprocess_text(self, text: str) -> str:
        """텍스트 전처리: <> 안의 문자열 삭제 (<삭 제>는 제외)"""
        # <삭 제>를 제외한 다른 <> 패턴 삭제
        cleaned_text = re.sub(r'<(?!삭\s*제>)[^>]*>', '', text)
        return cleaned_text
    
    def find_all_hierarchy_numbers(self, text: str, hierarchy_type: str) -> List[int]:
        """텍스트에서 특정 계층의 모든 번호를 추출하여 정렬된 리스트 반환"""
        patterns = [
            f'제\\s*(\\d+)(?:-\\d+)?\\s*{hierarchy_type}(?:의\\d+)?',  # 기본: 제1장
            f'(?<=[^제])제\\s*(\\d+)(?:-\\d+)?\\s*{hierarchy_type}(?:의\\d+)?',  # 앞에 다른 텍스트: ...제1장
            f'\\b(\\d+)\\s*{hierarchy_type}(?:의\\d+)?',  # 숫자만: 1장
        ]
        
        all_numbers = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    num = int(match) if isinstance(match, str) else int(match[0])
                    if 1 <= num <= 999:  # 합리적인 범위만
                        all_numbers.add(num)
                except (ValueError, IndexError):
                    continue
        
        sorted_numbers = sorted(list(all_numbers))
        print(f"2단계 - {hierarchy_type} 발견된 번호들: {sorted_numbers}")
        return sorted_numbers
    
    def is_hierarchy_reference(self, text: str, match_start: int, hierarchy_type: str) -> bool:
        """계층 패턴이 다른 계층의 인용인지 판별"""
        # 매치 끝 위치 찾기 (제X장/절/관 다음 위치)
        match_text = text[match_start:]
        hierarchy_pattern = f'제\\s*\\d+\\s*{hierarchy_type}'
        match_obj = re.match(hierarchy_pattern, match_text)
        if not match_obj:
            return False
        
        match_end = match_start + match_obj.end()
        
        # 계층 패턴 이후 25자를 확인
        after_text = text[match_end:match_end+25]
        
        # 1. 나열 단어 패턴 (계층 패턴 이후에 오는 경우)
        list_patterns = [r'^\s*및\s*', r'^\s*,\s*', r'^\s*또는\s*', r'^\s*내지\s*', r'^\s*부터\s*']
        for pattern in list_patterns:
            if re.search(pattern, after_text):
                return True
        
        # 2. 조사나 연결어 패턴
        connective_patterns = [
            r'^\s*의\s*규정', r'^\s*에\s*따라', r'^\s*에\s*따른', 
            r'^\s*의\s*규정에', r'^\s*단서의', r'^\s*에서', 
            r'^\s*을\s*', r'^\s*를\s*'
        ]
        for pattern in connective_patterns:
            if re.search(pattern, after_text):
                return True
        
        # 3. 하위 세부항목 인용 패턴 (계층구조에 맞게)
        if hierarchy_type == '장':
            subsection_patterns = [
                r'^\s*제\s*\d+\s*절',  # 제XX절
                r'^\s*제\s*\d+\s*관',  # 제XX관
                r'^\s*제\s*\d+(?:-\d+)?\s*조(?:의\d+)?'  # 제XX조
            ]
        elif hierarchy_type == '절':
            subsection_patterns = [
                r'^\s*제\s*\d+\s*관',  # 제XX관
                r'^\s*제\s*\d+(?:-\d+)?\s*조(?:의\d+)?'  # 제XX조
            ]
        elif hierarchy_type == '관':
            subsection_patterns = [
                r'^\s*제\s*\d+(?:-\d+)?\s*조(?:의\d+)?'  # 제XX조
            ]
        else:
            subsection_patterns = []
        
        for pattern in subsection_patterns:
            if re.search(pattern, after_text):
                return True
        
        return False
    
    def is_sentence_title(self, title: str) -> bool:
        """제목이 문장 형식인지 판별"""
        if not title:
            return False
        
        # 동사형 종결어미로 끝나는 경우
        sentence_endings = [
            '한다', '하여야', '해야', '된다', '받는다', '따른다',
            '의한다', '정한다', '본다', '처리한다', '관리한다'
        ]
        
        for ending in sentence_endings:
            if title.endswith(ending):
                return True
        
        return False
    
    def find_hierarchy_boundaries(self, text: str, hierarchy_type: str) -> List[Tuple[int, str, str]]:
        """특정 계층의 경계점들 찾기 - 향상된 필터링 적용"""
        text = self.preprocess_text(text)
        
        # 패턴: 번호 다음부터 다른 계층구조 전까지가 제목 (30자 제한)
        pattern = f'(제\\s*\\d+(?:-\\d+)?\\s*{hierarchy_type}(?:의\\d+)?)\\s*(.{{1,30}}?)(?=제\\d|$)'
        
        all_matches = list(re.finditer(pattern, text))
        valid_matches = []
        
        print(f"2단계 - {hierarchy_type} 패턴 {len(all_matches)}개 발견, 필터링 중...")
        
        # 유효한 매치만 필터링
        for match in all_matches:
            number_str = re.sub(r'\s+', '', match.group(1))
            raw_title = match.group(2).strip()
            
            # 제목 정제: 공백 정리하고 불필요한 문자 제거
            title = re.sub(r'\s+', ' ', raw_title)  # 연속 공백을 하나로
            title = re.sub(r'[^\w\s가-힣]', '', title).strip()  # 특수문자 제거
            
            # 1. 인용 패턴 체크
            if self.is_hierarchy_reference(text, match.start(), hierarchy_type):
                continue
            
            # 2. 문장형 제목 체크
            if self.is_sentence_title(title):
                continue
            
            valid_matches.append((match.start(), number_str, title))
        
        print(f"2단계 - 유효한 {hierarchy_type} 패턴 {len(valid_matches)}개 추출")
        
        # 실제 존재하는 번호 기반으로 필터링
        return self._filter_by_existing_numbers(valid_matches, hierarchy_type, text)
    
    def _filter_by_existing_numbers(self, matches: List[Tuple[int, str, str]], hierarchy_type: str, text: str) -> List[Tuple[int, str, str]]:
        """실제 존재하는 번호들을 기준으로 유효한 경계만 필터링"""
        if not matches:
            return []
        
        # 1. 실제 존재하는 번호들 추출
        existing_numbers = self.find_all_hierarchy_numbers(text, hierarchy_type)
        
        # 2. 매칭된 결과에서 실제 존재하는 번호들만 필터링
        valid_boundaries = []
        
        for pos, number_str, title in matches:
            # 번호 추출 (제3장 → 3)
            parsed = self.predictor.parse_number(number_str)
            if parsed and parsed['main'] in existing_numbers:
                valid_boundaries.append((pos, number_str, title))
        
        # 3. 번호 순서대로 정렬
        valid_boundaries.sort(key=lambda x: self.predictor.parse_number(x[1])['main'])
        
        print(f"2단계 - {hierarchy_type} 전체 매칭: {len(matches)}개, 유효 경계: {len(valid_boundaries)}개")
        if len(existing_numbers) != len(valid_boundaries):
            missing = set(existing_numbers) - {self.predictor.parse_number(x[1])['main'] for x in valid_boundaries}
            if missing:
                print(f"2단계 - {hierarchy_type} 누락된 번호: {sorted(missing)}")
        
        return valid_boundaries
    
    def extract_hierarchy_structure(self, text: str) -> Dict:
        """전체 텍스트에서 계층 구조 추출"""
        print("2단계 - 계층구조 추출 시작")
        
        hierarchy_structure = {
            '장': [],
            '절': [],
            '관': [],
            '조': []
        }
        
        # 장/절/관 추출
        for hierarchy_type in ['장', '절', '관']:
            boundaries = self.find_hierarchy_boundaries(text, hierarchy_type)
            for pos, number_str, title in boundaries:
                parsed = self.predictor.parse_number(number_str)
                if parsed:
                    hierarchy_structure[hierarchy_type].append({
                        'number': number_str,
                        'title': title,
                        'main_num': parsed['main'],
                        'position': pos
                    })
        
        return hierarchy_structure

class ArticleHierarchyMatcher:
    """3단계: 조문과 계층구조 매칭"""
    
    def __init__(self):
        self.predictor = NumberPredictor()
    
    def is_article_reference(self, text: str, match_start: int) -> bool:
        """조문 패턴이 다른 조문의 인용인지 판별"""
        # 조문 괄호 끝 위치 찾기 (제X조(제목) 다음 위치)
        match_end = text.find(')', match_start)
        if match_end == -1:
            return False
        
        # 조문 패턴 이후 25자를 확인
        after_text = text[match_end+1:match_end+26]
        
        # 1. 나열 단어 패턴 (조문 패턴 이후에 오는 경우)
        list_patterns = [r'^\s*및\s*', r'^\s*,\s*', r'^\s*또는\s*', r'^\s*내지\s*', r'^\s*부터\s*']
        for pattern in list_patterns:
            if re.search(pattern, after_text):
                return True
        
        # 2. 조사나 연결어 패턴 (조문 번호 바로 뒤에 오는 경우)
        connective_patterns = [
            r'^\s*의\s*규정', r'^\s*에\s*따라', r'^\s*에\s*따른', 
            r'^\s*의\s*규정에', r'^\s*단서의', r'^\s*에서', 
            r'^\s*을\s*', r'^\s*를\s*'
        ]
        for pattern in connective_patterns:
            if re.search(pattern, after_text):
                return True
        
        # 3. 세부항목 인용 패턴
        if re.search(r'^\s*제\s*\d+\s*[항호]', after_text):
            return True
        
        return False
    
    def find_article_position_in_text(self, text: str, article_number: str) -> Optional[int]:
        """텍스트에서 특정 조문의 위치를 찾기 - 첫 번째 실제 조문 위치"""
        # 조문 패턴으로 모든 매치 찾기
        pattern = f'{re.escape(article_number)}\\s*\\([^)]+\\)'
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            return None
        
        # 여러 매치가 있는 경우, 인용이 아닌 실제 조문 찾기
        for match in matches:
            match_start = match.start()
            
            # 기존 is_article_reference 메소드를 활용하여 인용 패턴 체크
            if not self.is_article_reference(text, match_start):
                return match_start
        
        # 모든 매치가 인용으로 판단되면 첫 번째 매치 반환
        return matches[0].start()
    
    def find_belonging_hierarchy(self, article_position: int, hierarchy_structure: Dict) -> List[str]:
        """조문이 속하는 계층구조 찾기 - 계층구조를 고려한 올바른 매칭"""
        belonging_titles = []
        
        # 1단계: 조문이 속하는 장 찾기
        current_chapter = None
        for chapter in hierarchy_structure['장']:
            if chapter['position'] <= article_position:
                current_chapter = chapter
            else:
                break
        
        if current_chapter:
            belonging_titles.append(current_chapter['title'])
            chapter_num = current_chapter['main_num']
            
            # 2단계: 해당 장 내에서 절 찾기
            current_section = None
            for section in hierarchy_structure['절']:
                # 절이 현재 장에 속하는지 확인 (절의 위치가 현재 장 이후이고 조문 이전인지)
                if (section['position'] > current_chapter['position'] and 
                    section['position'] <= article_position):
                    
                    # 다음 장이 있다면, 절이 다음 장 이전에 있는지 확인
                    next_chapter = self._find_next_chapter(chapter_num, hierarchy_structure['장'])
                    if next_chapter is None or section['position'] < next_chapter['position']:
                        current_section = section
                    else:
                        break
                elif section['position'] > article_position:
                    break
            
            if current_section:
                belonging_titles.append(current_section['title'])
                
                # 3단계: 해당 절 내에서 관 찾기
                current_subsection = None
                for subsection in hierarchy_structure['관']:
                    # 관이 현재 절에 속하는지 확인
                    if (subsection['position'] > current_section['position'] and 
                        subsection['position'] <= article_position):
                        
                        # 다음 절이 있다면, 관이 다음 절 이전에 있는지 확인
                        next_section = self._find_next_section(current_section, hierarchy_structure['절'])
                        if next_section is None or subsection['position'] < next_section['position']:
                            current_subsection = subsection
                        else:
                            break
                    elif subsection['position'] > article_position:
                        break
                
                if current_subsection:
                    belonging_titles.append(current_subsection['title'])
            else:
                # 절이 없는 장에서 관 찾기
                current_subsection = None
                for subsection in hierarchy_structure['관']:
                    if (subsection['position'] > current_chapter['position'] and 
                        subsection['position'] <= article_position):
                        
                        # 다음 장이 있다면, 관이 다음 장 이전에 있는지 확인
                        next_chapter = self._find_next_chapter(chapter_num, hierarchy_structure['장'])
                        if next_chapter is None or subsection['position'] < next_chapter['position']:
                            current_subsection = subsection
                        else:
                            break
                    elif subsection['position'] > article_position:
                        break
                
                if current_subsection:
                    belonging_titles.append(current_subsection['title'])
        
        return belonging_titles
    
    def _find_next_chapter(self, current_chapter_num: int, chapters: List[Dict]) -> Optional[Dict]:
        """다음 장 찾기"""
        for chapter in chapters:
            if chapter['main_num'] > current_chapter_num:
                return chapter
        return None
    
    def _find_next_section(self, current_section: Dict, sections: List[Dict]) -> Optional[Dict]:
        """다음 절 찾기"""
        current_found = False
        for section in sections:
            if current_found:
                return section
            if section['number'] == current_section['number']:
                current_found = True
        return None
    
    def add_hierarchy_to_articles(self, articles: List[Dict], text: str, hierarchy_structure: Dict) -> List[Dict]:
        """조문 목록에 계층구조 정보 추가"""
        print("3단계 - 조문에 계층구조 매칭 시작")
        
        enhanced_articles = []
        
        for article in articles:
            article_number = article['조번호']
            original_title = article['제목']
            
            # 조문의 텍스트 내 위치 찾기
            article_position = self.find_article_position_in_text(text, article_number)
            
            if article_position is not None:
                # 소속 계층구조 찾기
                belonging_hierarchy = self.find_belonging_hierarchy(article_position, hierarchy_structure)
                
                # 제목에 계층구조 추가
                if belonging_hierarchy:
                    enhanced_title = ", ".join(belonging_hierarchy + [original_title])
                else:
                    enhanced_title = original_title
            else:
                enhanced_title = original_title
            
            enhanced_articles.append({
                "조번호": article['조번호'],
                "제목": enhanced_title,
                "내용": article['내용']
            })
        
        print(f"3단계 - {len(enhanced_articles)}개 조문에 계층구조 매칭 완료")
        return enhanced_articles

class SmartParser:
    """통합 파서 - 장별 분할 및 통합 파싱"""
    
    def __init__(self):
        self.article_parser = SimpleArticleParser()
        self.hierarchy_extractor = HierarchyExtractor()
    
    def parse(self, text: str) -> List[Dict]:
        """장별 분할 통합 파싱"""
        print("통합 파싱 시작 (장별 분할 방식)")
        print("=" * 50)
        
        # 전처리된 텍스트 사용 (모든 단계에서 동일한 텍스트 기준)
        processed_text = self.hierarchy_extractor.preprocess_text(text)
        
        # 1단계: 단순 조문 파싱 (전체)
        all_articles = self.article_parser.parse_articles_only(text)
        print(f"1단계 완료: {len(all_articles)}개 조문 파싱")
        
        # 2단계: 장 경계 찾기 및 장별 텍스트 분할
        chapter_boundaries = self.hierarchy_extractor.find_hierarchy_boundaries(text, '장')
        print(f"2단계 완료: {len(chapter_boundaries)}개 장 발견")
        
        if not chapter_boundaries:
            # 장이 없으면 기본 파싱
            return all_articles
        
        # 3단계: 장별로 조문 매칭 및 계층구조 적용
        enhanced_articles = []
        
        for i, (chapter_pos, chapter_number, chapter_title) in enumerate(chapter_boundaries):
            # 장의 텍스트 영역 결정 (전처리된 텍스트 사용)
            if i + 1 < len(chapter_boundaries):
                next_chapter_pos = chapter_boundaries[i + 1][0]
                chapter_text = processed_text[chapter_pos:next_chapter_pos]
            else:
                chapter_text = processed_text[chapter_pos:]
            
            print(f"3단계 - {chapter_number} 처리 중...")
            
            # 이 장에 속하는 조문들 찾기 (전처리된 텍스트 사용)
            chapter_articles = self._find_articles_in_chapter(all_articles, processed_text, chapter_pos, 
                                                            next_chapter_pos if i + 1 < len(chapter_boundaries) else len(processed_text))
            
            # 장 내부의 절/관 구조 추출
            chapter_hierarchy = self._extract_chapter_hierarchy(chapter_text, chapter_pos)
            
            # 조문에 계층구조 적용
            enhanced_chapter_articles = self._apply_hierarchy_to_articles(
                chapter_articles, chapter_text, chapter_pos, chapter_title, chapter_hierarchy)
            
            enhanced_articles.extend(enhanced_chapter_articles)
            print(f"3단계 - {chapter_number}: {len(enhanced_chapter_articles)}개 조문 처리")
        
        print(f"통합 파싱 완료: {len(enhanced_articles)}개 조문")
        print("=" * 50)
        
        return enhanced_articles
    
    def _find_articles_in_chapter(self, all_articles: List[Dict], full_text: str, 
                                 chapter_start: int, chapter_end: int) -> List[Dict]:
        """특정 장에 속하는 조문들 찾기"""
        chapter_articles = []
        
        for article in all_articles:
            # 조문의 첫 번째 실제 출현 위치 찾기 (인용이 아닌)
            article_position = self._find_first_real_article_position(full_text, article)
            
            if article_position is not None and chapter_start <= article_position < chapter_end:
                chapter_articles.append(article)
        
        return chapter_articles
    
    def _find_first_real_article_position(self, text: str, article: Dict) -> Optional[int]:
        """조문의 첫 번째 실제 출현 위치 찾기 (인용이 아닌)"""
        article_number = article["조번호"]
        article_title = article["제목"]
        
        # 조문 패턴으로 모든 매치 찾기
        pattern = f'{re.escape(article_number)}\\s*\\({re.escape(article_title)}\\)'
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            # 제목이 다를 수 있으므로 번호만으로 찾기
            pattern = f'{re.escape(article_number)}\\s*\\([^)]+\\)'
            matches = list(re.finditer(pattern, text))
        
        if not matches:
            return None
        
        # 여러 매치가 있는 경우, 가장 앞에 있는 실제 조문 찾기
        for match in matches:
            match_start = match.start()
            
            # 앞의 100자를 확인해서 인용 패턴인지 체크
            before_text = text[max(0, match_start-100):match_start]
            
            # 인용 패턴들
            reference_indicators = [
                '준용', '따라', '규정', '의하여', '및', '또는', '내지', 
                '참조', '같은', '동일', '해당'
            ]
            
            is_reference = False
            for indicator in reference_indicators:
                if indicator in before_text:
                    is_reference = True
                    break
            
            # 실제 조문의 시작 패턴 확인 (조문은 보통 줄의 시작이나 특정 패턴 후에 나타남)
            before_line = before_text.split('\n')[-1] if '\n' in before_text else before_text
            
            # 조문이 줄의 시작이거나 특정 패턴 후에 나타나는 경우
            if (not is_reference and 
                (len(before_line.strip()) == 0 or  # 줄의 시작
                 before_line.strip().endswith('.') or  # 문장 끝 후
                 before_line.strip().endswith('>') or  # 태그 끝 후
                 re.search(r'\d+\.\s*$', before_line))):  # 번호 목록 후
                return match_start
        
        # 모든 매치가 인용으로 판단되면 첫 번째 매치 반환
        return matches[0].start()
    
    def _extract_chapter_hierarchy(self, chapter_text: str, chapter_start_pos: int) -> Dict:
        """장 내부의 절/관 계층구조 추출"""
        hierarchy = {'절': [], '관': []}
        
        # 절 추출
        section_boundaries = self.hierarchy_extractor.find_hierarchy_boundaries(chapter_text, '절')
        for pos, number, title in section_boundaries:
            hierarchy['절'].append({
                'number': number,
                'title': title,
                'position': chapter_start_pos + pos,
                'relative_position': pos
            })
        
        # 관 추출
        subsection_boundaries = self.hierarchy_extractor.find_hierarchy_boundaries(chapter_text, '관')
        for pos, number, title in subsection_boundaries:
            hierarchy['관'].append({
                'number': number,
                'title': title,
                'position': chapter_start_pos + pos,
                'relative_position': pos
            })
        
        return hierarchy
    
    def _apply_hierarchy_to_articles(self, articles: List[Dict], chapter_text: str, 
                                   chapter_start_pos: int, chapter_title: str, 
                                   chapter_hierarchy: Dict) -> List[Dict]:
        """장 내 조문들에 계층구조 적용"""
        enhanced_articles = []
        
        for article in articles:
            # 조문의 장 내 상대 위치 찾기
            article_pattern = f'{re.escape(article["조번호"])}\\s*\\({re.escape(article["제목"])}\\)'
            match = re.search(article_pattern, chapter_text)
            
            if not match:
                # Fallback: 조번호만으로 매칭 시도 (인용 필터링 포함)
                fallback_pattern = f'{re.escape(article["조번호"])}\\s*\\([^)]+\\)'
                fallback_matches = list(re.finditer(fallback_pattern, chapter_text))
                
                # 인용이 아닌 실제 조문 찾기
                for fallback_match in fallback_matches:
                    # 조문 뒤 25자를 확인하여 인용 패턴 체크
                    match_end = chapter_text.find(')', fallback_match.start())
                    if match_end != -1:
                        after_text = chapter_text[match_end+1:match_end+26]
                        
                        # 인용 패턴 체크
                        is_reference = False
                        reference_patterns = [
                            r'^\s*및\s*', r'^\s*,\s*', r'^\s*또는\s*', r'^\s*내지\s*',
                            r'^\s*의\s*규정', r'^\s*에\s*따라', r'^\s*에\s*따른', 
                            r'^\s*을\s*', r'^\s*를\s*'
                        ]
                        for pattern in reference_patterns:
                            if re.search(pattern, after_text):
                                is_reference = True
                                break
                        
                        if not is_reference:
                            match = fallback_match
                            break
            
            if not match:
                # 최종 fallback: 기본 장 제목만 추가
                enhanced_title = f"{chapter_title}, {article['제목']}"
            else:
                article_relative_pos = match.start()
                
                # 소속 절 찾기
                belonging_section = None
                for section in chapter_hierarchy['절']:
                    if section['relative_position'] <= article_relative_pos:
                        belonging_section = section
                    else:
                        break
                
                # 소속 관 찾기 (절이 있는 경우 절 범위 내에서, 없는 경우 장 범위 내에서)
                belonging_subsection = None
                search_start = belonging_section['relative_position'] if belonging_section else 0
                
                for subsection in chapter_hierarchy['관']:
                    if (subsection['relative_position'] >= search_start and 
                        subsection['relative_position'] <= article_relative_pos):
                        
                        # 다음 절이 있다면 그 절 이전에 있는지 확인
                        if belonging_section:
                            next_section = self._find_next_section(belonging_section, chapter_hierarchy['절'])
                            if next_section and subsection['relative_position'] >= next_section['relative_position']:
                                continue
                        
                        belonging_subsection = subsection
                
                # 제목 구성
                title_parts = [chapter_title]
                if belonging_section:
                    title_parts.append(belonging_section['title'])
                if belonging_subsection:
                    title_parts.append(belonging_subsection['title'])
                title_parts.append(article['제목'])
                
                enhanced_title = ", ".join(title_parts)
            
            enhanced_articles.append({
                "조번호": article['조번호'],
                "제목": enhanced_title,
                "내용": article['내용']
            })
        
        return enhanced_articles
    
    def _find_next_section(self, current_section: Dict, sections: List[Dict]) -> Optional[Dict]:
        """다음 절 찾기"""
        current_found = False
        for section in sections:
            if current_found:
                return section
            if section['number'] == current_section['number']:
                current_found = True
        return None

class AdminAPI:
    def __init__(self, oc: str):
        self.oc = oc
        self.base_url = "http://www.law.go.kr/DRF/"
        self.parser = SmartParser()
    
    def search_admin_rule_id(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """행정규칙명으로 검색해서 첫 번째 행정규칙의 ID를 반환"""
        url = f"{self.base_url}lawSearch.do"
        params = {
            "OC": self.oc,
            "target": "admrul",
            "type": "XML",
            "query": query,
            "search": 1,
            "display": 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            admrul = root.find("admrul")
            
            if admrul is None:
                return None, None
            
            return admrul.findtext("행정규칙일련번호"), admrul.findtext("행정규칙명")
        
        except Exception as e:
            st.error(f"행정규칙 검색 중 오류 발생: {str(e)}")
            return None, None
    
    def get_admin_rule_json(self, rule_id: str) -> Optional[Dict]:
        """행정규칙 ID로 행정규칙 데이터 조회"""
        url = f"{self.base_url}lawService.do"
        params = {
            "OC": self.oc,
            "target": "admrul",
            "type": "JSON",
            "ID": rule_id
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            st.error(f"행정규칙 데이터 조회 중 오류 발생: {str(e)}")
            return None
    
    def extract_text_from_rule_data(self, rule_data: Dict) -> str:
        """API 데이터에서 텍스트 추출"""
        admrul_service = rule_data.get("AdmRulService", {})
        content = admrul_service.get("조문내용", {})
        
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_content = item.get('조문내용', '') or str(item)
                else:
                    text_content = str(item)
                text_parts.append(text_content)
            text = "\n".join(text_parts)
        else:
            text = str(content)
        
        return text
    
    def clean_content(self, content: str) -> str:
        """내용에서 괄호 안 텍스트 제거 (<삭 제>는 제외)"""
        # <삭 제>를 제외한 다른 <> 패턴과 [] 패턴 삭제
        cleaned = re.sub(r"<(?!삭\s*제>).*?>|\[.*?\]", "", content)
        return cleaned.strip()
    
    def download_admin_rule_as_json(self, query: str) -> Optional[Dict]:
        """행정규칙을 검색하여 JSON 데이터로 반환 (3단계 파싱)"""
        # 1. 행정규칙 ID 검색
        rule_id, rule_name = self.search_admin_rule_id(query)
        if not rule_id:
            return None
        
        # 2. 행정규칙 데이터 조회
        rule_data = self.get_admin_rule_json(rule_id)
        if not rule_data:
            return None
        
        # 3. 텍스트 추출 및 3단계 파싱
        text = self.extract_text_from_rule_data(rule_data)
        if not text or len(text) < 50:
            return {
                "행정규칙ID": rule_id,
                "행정규칙명": rule_name,
                "조문": []
            }
        
        # 4. 3단계 스마트 파싱
        parsed_articles = self.parser.parse(text)
        
        # 5. 내용 정제
        cleaned_articles = []
        for article in parsed_articles:
            cleaned_content = self.clean_content(article.get("내용", ""))
            cleaned_articles.append({
                "조번호": article.get("조번호", ""),
                "제목": article.get("제목", ""),
                "내용": cleaned_content
            })
        
        return {
            "행정규칙ID": rule_id,
            "행정규칙명": rule_name,
            "조문": cleaned_articles
        }

def convert_admin_rule_data_to_chatbot_format(rule_data: Dict) -> List[Dict]:
    """행정규칙 데이터를 챗봇 형식으로 변환"""
    chatbot_data = []
    
    for article in rule_data.get("조문", []):
        title = article.get("제목")
        if title and str(title).strip():
            chatbot_data.append({
                "조번호": article.get("조번호", ""),
                "제목": title,
                "내용": article.get("내용", "")
            })
    
    return chatbot_data