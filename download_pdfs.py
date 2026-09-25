import requests
import logging

logging.basicConfig(
    filename='./data/download_pdfs.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Example link : https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20033337.pdf

csv = open('./data/clerk_directories/all_digital_ptr.csv', 'r')

# Downloads pdf fom the link provided
def download_pdf(link):
    response = requests.get(link)
    if response.status_code == 200: # If the request was successful
        filename = link.split("/")[-1]
        with open(f"./data/pdf/digital_ptr/{filename}", "wb") as f:
            f.write(response.content)
        message = f"Downloaded: {filename}"
        print(message)
        logger.info(message)
    else:
        message = f"Failed to download: {link} - Status code: {response.status_code}"
        print(message)
        logger.error(message)
        
# Create a list of all document IDs from the csv file. Ignore the header line, 
for line in csv:
    document_id = line.strip().split(",")[-1]
    year = line.strip().split(",")[-3]
    pdf_link = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{document_id}.pdf"
    download_pdf(pdf_link)