import logging
from blog_poster import BlogPoster
from paper_analyzer import PaperAnalyzer
from paper_ranker import PaperRanker
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_test_paper() -> dict:
    """테스트용 논문 데이터를 로드합니다."""
    return {
        "paper_id": "test_paper_001",
        "title": "Test Paper: A Novel Approach to AI Research",
        "abstract": """This paper presents a novel approach to artificial intelligence research. 
        We propose a new framework that combines deep learning with reinforcement learning to achieve 
        state-of-the-art performance in various tasks. Our method demonstrates significant improvements 
        in both accuracy and efficiency compared to existing approaches.""",
        "authors": ["Test Author 1", "Test Author 2"],
        "url": "https://arxiv.org/abs/test.001"
    }

def main():
    try:
        # 테스트용 논문 데이터 로드
        test_paper = load_test_paper()
        logger.info("Loaded test paper data")

        # 논문 분석
        analyzer = PaperAnalyzer()
        logger.info("Starting paper analysis...")
        analyzed_paper = analyzer.analyze_paper(test_paper)
        logger.info("Paper analysis completed")

        # 블로그 포스팅
        poster = BlogPoster()
        logger.info("Starting blog post generation...")
        blog_post = poster.post_paper(analyzed_paper)
        logger.info("Blog post generation completed")

        # 결과 출력
        print("\n=== Generated Blog Post ===")
        print(f"Title: {blog_post['title']}")
        print(f"Classification: {blog_post['classification']}")
        print(f"Tags: {', '.join(blog_post['tags'])}")
        print("\nContent:")
        print(blog_post['content'])

    except Exception as e:
        logger.error(f"Error in test process: {str(e)}")
        raise

if __name__ == "__main__":
    main() 