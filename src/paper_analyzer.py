import json
import requests
from typing import Dict, Any, List
import time
import logging
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, ANALYSIS_PROMPTS
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class PaperAnalyzer:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        
        # 세션 설정
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # 최대 3번 재시도
            backoff_factor=1,  # 재시도 간격 (1, 2, 4초)
            status_forcelist=[500, 502, 503, 504]  # 재시도할 HTTP 상태 코드
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _call_api(self, prompt: str, max_retries: int = 3) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"API 호출 시도 {attempt + 1}/{max_retries}")
                response = self.session.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=30  # 30초 타임아웃
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"API 호출 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 지수 백오프
                    self.logger.info(f"{wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"API 호출 최대 재시도 횟수 초과: {str(e)}")
                    raise
            except Exception as e:
                self.logger.error(f"예상치 못한 API 호출 오류: {str(e)}")
                raise

    def _parse_classification(self, response: str) -> Dict[str, Any]:
        lines = response.split("\n")
        classification = ""
        tags = []
        
        for line in lines:
            if line.startswith("분류:"):
                classification = line.split(":", 1)[1].strip()
            elif line.startswith("태그:"):
                tags_str = line.split(":", 1)[1].strip()
                tags = [tag.strip("[]") for tag in tags_str.split(",")]
        
        if len(tags) < 3:
            tags.extend(["AI", "Research", "Technology"])
        
        return {
            "classification": classification,
            "tags": tags
        }

    def _clean_response(self, response: str) -> str:
        lines = response.split("\n")
        cleaned_lines = []
        
        for line in lines:
            if line.startswith("###"):
                cleaned_lines.append(f"<h3>{line[4:]}</h3>")
            elif "**" in line:
                cleaned_lines.append(line.replace("**", "<strong>", 1).replace("**", "</strong>", 1))
            else:
                cleaned_lines.append(f"<p>{line}</p>")
        
        return "\n".join(cleaned_lines)

    def _translate_abstract(self, abstract: str) -> str:
        prompt = f"다음 영어 초록을 한국어로 번역해주세요. 전문 용어는 원문(영어)을 병기해주세요:\n\n{abstract}"
        return self._call_api(prompt)

    def _analyze_paper_content(self, title: str, abstract: str) -> Dict[str, Any]:
        # 분류 및 태그 생성
        classification_prompt = ANALYSIS_PROMPTS["classification"].format(
            title=title,
            abstract=abstract
        )
        classification_response = self._call_api(classification_prompt)
        classification_result = self._parse_classification(classification_response)
        
        # 요약 생성
        summary_prompt = ANALYSIS_PROMPTS["summary"].format(
            title=title,
            abstract=abstract
        )
        summary_response = self._call_api(summary_prompt)
        cleaned_summary = self._clean_response(summary_response)
        
        # 초록 번역
        translation = self._translate_abstract(abstract)
        
        return {
            "classification": classification_result["classification"],
            "tags": classification_result["tags"],
            "summary": cleaned_summary,
            "translation": translation
        }

    def analyze_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """논문을 분석하고 결과를 반환합니다."""
        self.logger.info(f"Analyzing paper: {paper['title']}")
        
        try:
            analysis_result = self._analyze_paper_content(paper["title"], paper["abstract"])
            
            return {
                "paper_id": paper["paper_id"],
                "title": paper["title"],
                "classification": analysis_result["classification"],
                "tags": analysis_result["tags"],
                "summary": analysis_result["summary"],
                "translation": analysis_result["translation"],
                "original_abstract": paper["abstract"]
            }
        except Exception as e:
            self.logger.error(f"Error analyzing paper {paper['paper_id']}: {str(e)}")
            raise

    def analyze_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for paper in papers:
            try:
                result = self.analyze_paper(paper)
                results.append(result)
                time.sleep(1)  # API 호출 간 딜레이
            except Exception as e:
                self.logger.error(f"Failed to analyze paper {paper['paper_id']}: {str(e)}")
                continue
        return results 