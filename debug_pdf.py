import pdfplumber

with pdfplumber.open("uploads/infosys.pdf") as pdf:
    page = pdf.pages[346]  
    tables = page.extract_tables()
    
    print(f"Tables found: {len(tables)}\n")

    for t_idx, table in enumerate(tables):
        print(f"\n--- TABLE {t_idx} ---")
        for row in table[:10]:
            print(row)

