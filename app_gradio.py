import gradio as gr
import os
import base64
import requests
from pdf2image import convert_from_path
from io import BytesIO
import json
import yaml
import re


def pdf_to_text(pdf_file):
    """
    Convert each page of a PDF directly into YAML without saving images, and return the final YAML string.
    """
    pdf_name = os.path.basename(pdf_file.name).replace('.pdf', '')
    poppler_path = r'poppler-24.07.0\Library\bin'
    api_key = "ee65aca022a74803b2e2d1ff4c373b05"
    endpoint = "https://firstsource.openai.azure.com/openai/deployments/gpt-4o-v05-13/chat/completions?api-version=2024-02-15-preview"

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    print(f"Converting {pdf_name} PDF pages to images...")
    pages = convert_from_path(pdf_file.name, poppler_path=poppler_path)

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

    # final_yaml = combined_yaml.replace('```yaml\n', '').replace('```', '')

    print(f"YAML conversion completed successfully.")
    # return merge_json_objects(combined_yaml)
    return full_json

def process_pdf(pdf_file):
    combined_json = {}
    # text_content = pdf_to_text(pdf_file)
    json_content = pdf_to_text(pdf_file)

    json_filename = pdf_file.name.replace('.pdf', '.json')

    for json_str in json_content:
        json_object = json.loads(json_str)
        combined_json.update(json_object)


    # Write the combined JSON object to a file
    with open(json_filename, 'w') as json_file:
        json.dump(combined_json, json_file, indent=4)

    return json_filename

with gr.Blocks() as interface:
    gr.Markdown("# PDF 2 JSON Converter")

    pdf_input = gr.File(label="Upload PDF File", file_types=[".pdf"])

    json_output = gr.File(label="Download JSON File")

    convert_button = gr.Button("Convert PDF to JSON")

    convert_button.click(process_pdf, inputs=[pdf_input], outputs=[json_output])

interface.launch(debug=True)
