import os
import time
import socket
import json
import uuid
import datetime
import itertools
from tika import parser
from concurrent.futures import ThreadPoolExecutor

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

def extract_text_from_image(image_path, server_url):
    headers = {
        "X-Tika-OCRLanguage": "kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara"
    }

    response = parser.from_file(image_path, server_url, headers=headers)
    if response is not None: 
        status = response.get('status', None)
        if status == 200:
            try:
                body_info = response.get('content', None)
                print(f"file : {image_path}, content : {body_info}")
                metainfo = response.get('metadata', None)
                return metainfo, body_info
            except Exception as e:
                print(f"Error with : {str(e)}")
                return None, None

def save_as_json(file_path, json_data, metainfo, body_info):
    try:
        root_path = json_data['root_path']
        json_path = json_data['elasticsearch']['normal_el_file_target_path']
        json_file_name = uuid.uuid4()
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        file_extension = file_extension.lower() 
        now = datetime.datetime.now()
        json_path = os.path.join(root_path, json_path)
        splitdrive_file_path = os.path.dirname(file_path)
        new_uuid = uuid.uuid4()
        utc_now = datetime.datetime.utcnow()
        timestamp = utc_now.timestamp()
        uuid_str = str(new_uuid) + '_' + str(timestamp)
    
    except Exception as e:
        print(f"{file_path}, meta 정보 생성 중 오류 발생 : {str(e)}")

    if not os.path.exists(json_path):
        os.makedirs(json_path, exist_ok=True)

    try:
        document_info = {}
        document_info["file"] = {}
        document_info["file"]["path"] = file_path
        document_info["file"]["extension"] = file_extension[1:]
        document_info["file"]["size"] = ""
        document_info["file"]["type"] = metainfo["Content-Type"]
        document_info["file"]["mime_type"] = metainfo["Content-Type"]
        document_info["file"]["mtime"] = ""
        document_info["file"]["ctime"] = ""
        document_info["file"]["meta_info"] = metainfo
        document_info["root_path"] = root_path
        document_info["directory"] = splitdrive_file_path
        document_info["title"] = file_name
        document_info["uuid"] = uuid_str
        document_info["json_write_time"] = now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        document_info["content"] = body_info
        document_info["summary"] = body_info[:300]
        document_info["tags"] = []
        document_info["tags"].append("file")
        document_info["tags"].append("normal")

    except Exception as e:
        print(f"document_info 생성 중 오류 발생 : {str(e)}")

    try:
        result_file = os.path.join(json_path, f"{json_file_name}.json")
        with open(result_file, 'w', encoding='utf-8') as json_file:
            json.dump(document_info, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"JSON 생성 중 오류 발생 : {str(e)}")

def process_image(image_path, json_data, server_urls):
    try:
        server_url = next(server_urls)
        metadata, body_info = extract_text_from_image(image_path, server_url)
        save_as_json(image_path, json_data, metadata, body_info)
    except Exception as e:
        print(f"{image_path} 처리 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    try:
        json_data = config_reading('config.json')
        
        if json_data is not None:
            datafilter = json_data['datafilter']
            image_extensions = datafilter['image_extensions']
            tika_app = json_data['tika_app']
            tika_server_ip = tika_app["tika_server_ip"]
            tika_server_port = tika_app['tika_server_port']
            tika_server_count = tika_app['tika_server_count']
            max_tika_thread_num = tika_app['max_tika_thread_num']
            root_path = json_data['root_path']
            source_path = json_data['datainfopath']['source_path']
            source_path = os.path.join(root_path, source_path)

            server_urls = itertools.cycle([f"http://{tika_server_ip}:{tika_server_port + i}/tika" for i in range(tika_server_count)])

            with ThreadPoolExecutor(max_workers=max_tika_thread_num) as executor:
                for root, _, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if any(file_path.lower().endswith(ext) for ext in image_extensions):
                            executor.submit(process_image, file_path, json_data, server_urls)

    except Exception as e:
        info_message = f"Exception : {str(e)}"
        print(f"Exception in main(): {info_message}")
