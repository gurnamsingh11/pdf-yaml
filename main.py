import os
import base64
import requests
from pdf2image import convert_from_path

def pdf_to_images(pdf_path, output_dir, poppler_path=None):
    """
    Convert each page of a PDF into an image and save them in the specified directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pages = convert_from_path(pdf_path, poppler_path=poppler_path)

    image_paths = []
    for i, page in enumerate(pages):
        output_file = os.path.join(output_dir, f"page_{i + 1}.png")
        page.save(output_file, 'PNG')
        image_paths.append(output_file)
        print(f"Saved {output_file}")

    return image_paths

def convert_images_to_yaml(image_paths, api_key, endpoint):
    """
    Convert a list of images to a combined YAML string using a specified API endpoint.
    """
    combined_yaml = ""
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    for image_path in image_paths:
        print(f"Processing {image_path}...")
        encoded_image = base64.b64encode(open(image_path, 'rb').read()).decode('ascii')
        
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
                            "image_url": 
                            {
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
            print(f"Failed to process {image_path}. Error: {e}")
            continue

    final_yaml = combined_yaml.replace('```yaml\n', '').replace('```', '')
    return final_yaml

def pdf_to_yaml(pdf_path, poppler_path, api_key, endpoint):
    """
    Complete workflow to convert a PDF to a YAML file.
    """
    pdf_name = os.path.basename(pdf_path).replace('.pdf', '')
    base_dir = os.path.dirname(pdf_path)
    
    image_output_dir = os.path.join(base_dir, f"pdf-images/{pdf_name}")
    yaml_output_dir = os.path.join(base_dir, "yaml-files")

    if not os.path.exists(yaml_output_dir):
        os.makedirs(yaml_output_dir)

    image_paths = pdf_to_images(pdf_path, image_output_dir, poppler_path=poppler_path)
    
    yaml_string = convert_images_to_yaml(image_paths, api_key, endpoint)
    
    yaml_filename = os.path.join(yaml_output_dir, f"{pdf_name}.yaml")
    with open(yaml_filename, "w") as f:
        f.write(yaml_string)
    
    print(f"YAML file saved as {yaml_filename}")
    return yaml_filename

pdf_path = 'docs/L3-NetworX Pricer Functionality - All States Medicaid - Job Aid.pdf'
poppler_path = r'poppler-24.07.0\Library\bin'
api_key = "YOUR_API_KEY"  
endpoint = "YOUR_API_ENDPOINT"  

pdf_to_yaml(pdf_path, poppler_path, api_key, endpoint)
