import gradio as gr
import os
import base64
import requests
from pdf2image import convert_from_path
from io import BytesIO

def pdf_to_yaml(pdf_file):
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

    combined_yaml = ""

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
                            "text": "You are an AI assistant that converts given image to YAML file."
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
                            "text": "Convert the given image to YAML file without adding any other data by yourself."
                        }
                    ]
                }
            ],
            "temperature": 0,
            "top_p": 0.95,
            "max_tokens": 800
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()  # Raise an exception if the request failed
            ai_response = response.json()['choices'][0]['message']['content']
            combined_yaml += ai_response + "\n"
        except requests.RequestException as e:
            print(f"Failed to process page {i + 1}. Error: {e}")
            continue

    final_yaml = combined_yaml.replace('```yaml\n', '').replace('```', '')

    print(f"YAML conversion completed successfully.")
    return final_yaml

def process_pdf(pdf_file):
    yaml_content = pdf_to_yaml(pdf_file)
    
    yaml_filename = pdf_file.name.replace('.pdf', '.yaml')
    
    with open(yaml_filename, "w") as f:
        f.write(yaml_content)

    return yaml_filename


with gr.Blocks() as interface:
    gr.Markdown("# PDF to YAML Converter")

    pdf_input = gr.File(label="Upload PDF File", file_types=[".pdf"])

    yaml_output = gr.File(label="Download YAML File")

    convert_button = gr.Button("Convert PDF to YAML")

    convert_button.click(process_pdf, inputs=[pdf_input], outputs=[yaml_output])

interface.launch(share=True)
