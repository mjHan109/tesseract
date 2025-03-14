import subprocess
import os
import json
import uuid
import requests

def config_reading(json_file_name):
    current_directory = os.getcwd()
    config_file = os.path.join(current_directory, json_file_name)
         
    if os.path.isfile(config_file):
        with open(config_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
            return json_data
    else:
        print(f"{current_directory} - {json_file_name} 파일을 찾을 수 없습니다.")
        return None

def extract_text_from_image(image_path):

    current_directory = os.getcwd()
    tika_server_path = os.path.join(current_directory, "tika-server-1.7.jar")
    tika_config_path = os.path.join(current_directory, "tika-config.xml")

    command = [
        "java",
        "-jar",
        tika_server_path,
        "--config=" + tika_config_path,
        image_path
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error during Tika processing: {e}")
        return None

def save_as_json(json_data, text_data):
    root_path = json_data['root_path']
    json_path = json_data['elasticsearch']['normal_el_file_target_path']
    file_name = uuid.uuid4()

    json_path = os.path.join(root_path, json_path)

    if not os.path.exists(json_path):
        os.makedirs(json_path, exist_ok=True)

    data = {
        "text": text_data
    }

    result_file = os.path.join(json_path, f"{file_name}.json")
    with open(result_file, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    try:
        json_data = config_reading('config.json')
        
        if json_data is not None:
            datafilter = json_data['datafilter']
            image_extensions = datafilter['image_extensions']
            tika_app = json_data['tika_app']
            root_path = json_data['root_path']
            source_path = json_data['datainfopath']['source_path']

            source_path = os.path.join(root_path, source_path)

            for root, _, files in os.walk(source_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        image_path = os.path.join(root, file)
                        try:
                            text_data = extract_text_from_image(image_path)
                            print(f"{file} 처리 완료, 추출된 텍스트: {text_data}")
                            save_as_json(json_data, text_data)
                        except Exception as e:
                            print(f"{file} 처리 중 오류 발생: {str(e)}")
    except Exception as e:
        info_message = f"Exception : {str(e)}"
        print(f"main(): {info_message}")
