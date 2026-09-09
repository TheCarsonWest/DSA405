import pdfplumber

table_lines = []
with pdfplumber.open("./data/pdf/digital_ptr/20032174.pdf") as pdf:
    for page in pdf.pages:
        table = page.extract_tables()
        table_lines.extend(table)

# join all text in one line and remove newlines
for i in range(len(table_lines)):
    table_lines[i] = " ".join([str(cell) for cell in table_lines[i]]).replace("\n", " ")
    
print(table_lines)