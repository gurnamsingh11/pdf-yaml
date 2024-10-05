# source myenv/bin/activate

import os
import base64
import requests
from pdf2image import convert_from_path
from io import BytesIO
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import json
from typing import Annotated
import shutil

app = FastAPI()

def pdf_to_text(pdf_file):
    """
    Convert each page of a PDF directly into text without saving images, and return the final text content.
    """
    pdf_name = 'input'
    api_key = "ee65aca022a74803b2e2d1ff4c373b05"  
    endpoint = "https://firstsource.openai.azure.com/openai/deployments/gpt-4o-v05-13/chat/completions?api-version=2024-02-15-preview"

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    print(f"Converting {pdf_name} PDF pages to images...")
    pages = convert_from_path(pdf_file)  # Use pdf_file.file to access the file-like object

    full_json = []

    for i, page in enumerate(pages):
        print(f"Processing page {i + 1} of {pdf_name}...")
        img_byte_arr = BytesIO()
        page.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        encoded_image = base64.b64encode(img_byte_arr.read()).decode('ascii')

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": """
                                    You are an OCR model designed to extract structured information from document images and convert it into a JSON format.
                                    Analyze the image provided and extract the relevant text data. 
                                    Make sure to exclude any text found in headers, footers, and page numbers. 
                                    Focus on the primary content sections and fields and other specific fields in the main body.
                                    
                                    Here are additional instructions to follow:
                                    - Exclude text in the top-left and bottom of the document such as the company logo, headers, footers.
                                    - Maintain a clear and structured JSON format.
                                    - If a value is not present, set its value to null.
                                    """
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "\n"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": """Convert the given image to JSON.
                            Example:
                            ```json
                            {
                            }```

                            Strictly follow the given response pattern.
                            """
                        }
                    ]
                }
            ],
            "temperature": 0,
            "max_tokens": 800
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()  # Raise an exception if the request failed
            ai_response = response.json()['choices'][0]['message']['content']
            combined_yaml = ai_response + "\n"
            json_content = combined_yaml.replace("```json\n","").replace("```\n","")
            full_json.append(json_content)
        except requests.RequestException as e:
            print(f"Failed to process page {i + 1}. Error: {e}")
            continue

    return full_json

def process_pdf(upload_file: UploadFile):
    combined_json = {}
    # Create a temporary file to save the uploaded PDF
    temp_pdf_path = f"temp_{upload_file.filename}"
    
    # Save the uploaded file to a temporary location
    with open(temp_pdf_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    # Use the temporary file path for processing
    json_content = pdf_to_text(temp_pdf_path)

    # Create the JSON filename
    json_filename = temp_pdf_path.replace('.pdf', '.json')

    for json_str in json_content:
        json_object = json.loads(json_str)
        combined_json.update(json_object)

    # Write the combined JSON object to a file
    with open(json_filename, 'w') as json_file:
        json.dump(combined_json, json_file, indent=4)

    # Clean up the temporary PDF file
    os.remove(temp_pdf_path)

    return json_filename

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        return {"error": "File must be a PDF."}

    json_filename = process_pdf(file)

    return FileResponse(json_filename, media_type='application/json', filename=os.path.basename(json_filename))

@app.get("/")
async def main():
    content = """
<body>
<form action="/uploadpdf/" enctype="multipart/form-data" method="post">
<input name="pdf_file" type="file" accept=".pdf" required>
<input type="submit">
</form>
</body>
    """
    return content

@app.on_event("shutdown")
def shutdown_event():
    # Cleanup any generated JSON files after serving
    for filename in os.listdir('.'):
        if filename.endswith('.json'):
            os.remove(filename)
