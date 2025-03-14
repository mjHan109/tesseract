import requests
from tika import parser

def extract_text_from_image(image_path, server_url):
    headers = {
        "X-Tika-OCRLanguage": "kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara"
    }
    with open(image_path, 'rb') as file:
        files = {'file': file}
        try:
            response = requests.put(server_url, headers=headers, files=files, timeout=120)
            if response.status_code == 200:
                body_info = response.text
                metainfo = response.headers
                print(f"body_info : {body_info}")
                return metainfo, body_info
            else:
                print(f"Error: {response.status_code} for file: {image_path}")
                return None, None
        except requests.exceptions.RequestException as e:
            print(f"RequestException: {e} for file: {image_path}")
            return None, None

# Example usage
image_path = "/data/100G/test_files/test_1.png"
server_url = "http://221.151.83.139:9991/tika"
metadata, content = extract_text_from_image(image_path, server_url)
print(metadata, content)
