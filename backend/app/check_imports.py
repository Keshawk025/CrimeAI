try:
    import fitz
    print("fitz: OK")
except ImportError:
    print("fitz: Missing")

try:
    import docx
    print("docx: OK")
except ImportError:
    print("docx: Missing")

try:
    import langdetect
    print("langdetect: OK")
except ImportError:
    print("langdetect: Missing")
