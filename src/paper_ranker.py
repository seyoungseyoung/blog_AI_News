import logging
from typing import List, Dict, Any
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL

class PaperRanker:
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.logger = logging.getLogger(__name__)

    def _call_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
            raise

    def _extract_keywords(self, paper: Dict[str, Any]) -> List[str]:
        """
        논문에서 핵심 키워드를 추출합니다.
        """
        prompt = f"""다음 논문에서 핵심 키워드를 추출해주세요:

제목: {paper['title']}
초록: {paper['abstract']}

키워드 추출 규칙:
1. 기술적 용어와 개념을 우선적으로 추출
2. 연구 방법론이나 접근 방식 관련 용어 포함
3. 주요 성능 지표나 평가 방법 포함
4. 연구 분야의 특수 용어 포함
5. 최소 5개, 최대 10개의 키워드 추출

응답 형식:
키워드: [키워드1], [키워드2], [키워드3], ...
"""
        try:
            response = self._call_api(prompt)
            keywords_str = response.split("키워드:")[1].strip()
            keywords = [kw.strip() for kw in keywords_str.split(",")]
            return keywords
        except Exception as e:
            self.logger.error(f"Error extracting keywords from paper {paper['title']}: {str(e)}")
            return []

    def _evaluate_paper(self, paper: Dict[str, Any]) -> float:
        """
        논문의 중요도와 관련성을 평가하여 점수를 매깁니다.
        """
        prompt = f"""다음 논문의 중요도와 관련성을 평가해주세요:

제목: {paper['title']}
초록: {paper['abstract']}
분류: {paper['classification']}
태그: {', '.join(paper['tags'])}

평가 기준:
1. 연구의 혁신성과 독창성 (0-30점)
2. 기술적 영향력과 실용성 (0-30점)
3. 연구 분야의 중요성 (0-20점)
4. 결과의 명확성과 검증 가능성 (0-20점)

각 기준에 대한 점수를 0-100 사이의 정수로 평가해주세요.
응답 형식:
총점: [점수]
"""
        try:
            response = self._call_api(prompt)
            score = float(response.split("총점:")[1].strip())
            return score
        except Exception as e:
            self.logger.error(f"Error evaluating paper {paper['title']}: {str(e)}")
            return 0.0

    def rank_papers(self, papers: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """
        논문들을 평가하여 상위 n개를 선별합니다.
        """
        self.logger.info(f"Ranking {len(papers)} papers...")
        
        # 각 논문에 대한 점수 계산 및 키워드 추출
        scored_papers = []
        for paper in papers:
            try:
                score = self._evaluate_paper(paper)
                keywords = self._extract_keywords(paper)
                scored_papers.append({
                    **paper,
                    "score": score,
                    "keywords": keywords
                })
            except Exception as e:
                self.logger.error(f"Failed to evaluate paper {paper['title']}: {str(e)}")
                continue
        
        # 점수 기준으로 정렬
        ranked_papers = sorted(scored_papers, key=lambda x: x["score"], reverse=True)
        
        # 상위 n개 선택
        top_papers = ranked_papers[:top_n]
        
        self.logger.info(f"Selected top {len(top_papers)} papers")
        return top_papers 