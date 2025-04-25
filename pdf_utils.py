import PyPDF2
import os

def extract_text_from_pdf(pdf_path):
    """
    PDF 파일에서 텍스트를 추출하는 함수
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
    return text

def load_all_pdfs():
    """
    모든 PDF 파일을 로드하고 텍스트를 추출하는 함수
    """
    pdf_files = [
        "관세법.pdf",
        "관세법 시행령.pdf",
        "관세법 시행규칙.pdf",
        "관세평가 운영에 관한 고시.pdf",
        "관세조사 운영에 관한 훈령.pdf"
    ]
    
    all_text = ""
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            text = extract_text_from_pdf(pdf_file)
            all_text += f"\n\n=== {pdf_file} ===\n\n{text}"
    
    return all_text 