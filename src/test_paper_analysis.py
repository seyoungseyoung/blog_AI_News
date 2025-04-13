import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any
import yaml
from paper_analyzer import PaperAnalyzer

def setup_logging():
    """로깅 설정"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f'paper_analysis_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def load_test_paper() -> Dict[str, Any]:
    """테스트용 논문 데이터 로드"""
    return {
        "paper_id": "test_paper_001",
        "title": "Test Paper Title",
        "abstract": "This is a test abstract for testing the paper analysis functionality. It contains some technical terms and concepts that should be properly analyzed and translated.",
        "authors": ["Test Author 1", "Test Author 2"],
        "url": "https://example.com/test_paper"
    }

def main():
    logger = setup_logging()
    logger.info("Starting paper analysis test...")
    
    try:
        # 테스트 논문 로드
        test_paper = load_test_paper()
        logger.info(f"Loaded test paper: {test_paper['title']}")
        
        # PaperAnalyzer 초기화
        analyzer = PaperAnalyzer()
        
        # 논문 분석
        logger.info("Analyzing paper...")
        result = analyzer.analyze_paper(test_paper)
        
        # 결과 출력
        logger.info("Analysis Results:")
        logger.info(f"Classification: {result['classification']}")
        logger.info(f"Tags: {', '.join(result['tags'])}")
        logger.info(f"Summary: {result['summary']}")
        logger.info(f"Translation: {result['translation']}")
        
        logger.info("Paper analysis test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during paper analysis test: {str(e)}")
        raise

if __name__ == "__main__":
    main() 