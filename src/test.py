import logging
import os
from typing import Dict
from dotenv import load_dotenv
from paper_crawler import PaperCrawler
from paper_analyzer import PaperAnalyzer
from paper_ranker import PaperRanker
from blog_poster import BlogPoster
import json

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ai_news_blog.log'),
            logging.StreamHandler()
        ]
    )

def load_config() -> Dict:
    load_dotenv()
    return {
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY'),
        'NAVER_ID': os.getenv('NAVER_ID'),
        'NAVER_USERNAME': os.getenv('NAVER_USERNAME'),
        'NAVER_PASSWORD': os.getenv('NAVER_PASSWORD'),
        'NAVER_PW': os.getenv('NAVER_PW')
    }

def main():
    """메인 함수"""
    try:
        # 설정 로드
        config = load_config()
        
        # 논문 크롤러 초기화
        crawler = PaperCrawler(config)
        
        # 최근 논문 1개만 크롤링
        papers = crawler.get_daily_papers()
        if not papers:
            print("✗ 크롤링할 논문이 없습니다.")
            return
            
        # 블로그 포스터 초기화
        poster = BlogPoster(config)
        
        # 논문 포스팅
        for paper in papers[:1]:  # 첫 번째 논문만 처리
            try:
                result = poster.post_paper(paper)
                if result:
                    print(f"✓ 논문 포스팅 성공: {paper['title']}")
                else:
                    print(f"✗ 논문 포스팅 실패: {paper['title']}")
            except Exception as e:
                print(f"✗ 논문 포스팅 중 오류 발생: {str(e)}")
                continue
                
    except Exception as e:
        print(f"✗ 프로그램 실행 중 오류 발생: {str(e)}")
    finally:
        # 리소스 정리
        if 'poster' in locals():
            poster.close()

if __name__ == "__main__":
    main() 