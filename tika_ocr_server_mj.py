import subprocess
import os
import signal
import time
import socket
import json
import uuid
import mimetypes
import requests
import base64
import datetime
from tika import parser

def config_reading(json_file_name):
    current_directory = os.getcwd()
    # JSON 파일 경로 생성
    config_file = os.path.join(current_directory, json_file_name)
         
    if os.path.isfile(config_file):
        with open(config_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

            return json_data
    else:
        print( f"{current_directory} - {json_file_name} 파일을 찾을 수 없습니다.")
        return None

def wait_for_port(port, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(1)
    return False

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0
    
def start_tika_server(port_number, java_command):
    current_directory = os.getcwd()
    tika_config_path = os.path.join(current_directory, "tika-config.xml")
    # tika_server_path = os.path.join(current_directory, "tika-server-1.26.jar")
    tika_server_path = os.path.join(current_directory, "tika-server.jar")
    log_file_path = os.path.join(current_directory, f"tika_server_{port_number}.log")
    if not is_port_in_use(port_number):
        # tika_command = f'{java_command} "{tika_server_path}" --port={port_number} --host 0.0.0.0 --enableImageOcr --ocrLanguage kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara > {log_file_path} 2>&1 &'
        tika_command = f'{java_command} "{tika_server_path}" --port={port_number} --host 0.0.0.0 --config "{tika_config_path}" > /dev/null 2>&1 &'
        # tika_command = f'{java_command} "{tika_server_path}" --port={port_number} --host 0.0.0.0 --config "{tika_config_path}" > {log_file_path} 2>&1 &'
        try:
            # print(f"Starting Tika server with command: {tika_command}")
            subprocess.run(tika_command, shell=True)
        except Exception as e:
            info_message = f"Exception : {str(e)}"
            print(f"start_tika_server(): {info_message}")
        time.sleep(2)

def kill_process_by_name(processor_name):
    
    print( f"\ncall kill tika-server : {processor_name}")  
    try:
        command = f"pkill -f '{processor_name}'"
        
        subprocess.run(command, shell=True)
        print(f"Killing process {command}")
        
    except Exception as e:
        info_message = f"kill_process_by_name:Exception 0-1: {processor_name} {str(e)}"
        print(f"kill_process_by_name(): {info_message}") 

def extract_text_from_image(image_path, server_url):
    current_directory = os.getcwd()
    # tika_config_path = os.path.join(current_directory, "tika-config.xml")

    # headers = {
    #     # 'Content-Type': mime_type,
    #     # 'X-Tika-OCRLanguage': 'kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara',
    #     # 'Accept': 'text/plain',
    #     'Content-Disposition' : f'attachment; filename={image_path}'
    # }

    headers = {
    "X-Tika-OCRLanguage": "kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara"
    }

    # parsed = parser.from_file(image_path, headers=headers)

    response = parser.from_file(image_path, headers=headers)

    if response is not None: 
        status = response.get('status', None)

        if status == 200:
                try:
                    body_info = response.get('content', None)
                    # print(f"file : {image_path}, content : {body_info}")
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

        # print(f"file : {image_path}, body_info : {body_info}")
    except Exception as e:
        print(f"{file_path}, document_info 생성 중 오류 발생 : {str(e)}")

    try:
        # 결과를 JSON 파일로 저장
        result_file = os.path.join(json_path, f"{json_file_name}.json")
        with open(result_file, 'w', encoding='utf-8') as json_file:
            json.dump(document_info, json_file, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"{file_path}, JSON 생성 중 오류 발생 : {str(e)}")
    
if __name__ == "__main__":
    processes = []
    try:
        kill_process_by_name("tika-server")    
        time.sleep(1)

        json_data = config_reading('config.json')
        
        if json_data != None:
            # tika path info
            datafilter = json_data['datafilter']
            image_extensions = datafilter['image_extensions']
            tika_app = json_data['tika_app']
            tika_app_jar_path = tika_app['tika_jar_path']
            tika_app_jar_name = tika_app['tika_jar_name']
            tika_server_ip = tika_app['tika_server_ip']
            tika_server_port = tika_app['tika_server_port']
            tika_server_count = tika_app['tika_server_count']
            max_tika_thread_num = tika_app['max_tika_thread_num']
            root_path = json_data['root_path']
            source_path = json_data['datainfopath']['source_path']

            tika_xms = tika_app['tika_xms']
            tika_xmx = tika_app['tika_xmx']
            
            for i in range(tika_server_count):
                port = tika_server_port + i
                java_command = f"nohup java -Xms{tika_xms}m -Xmx{tika_xmx}m -jar"
                start_tika_server(tika_server_port + i, java_command)
                time.sleep(5)

                if not wait_for_port(tika_server_port):
                    raise RuntimeError(f"Tika 서버가 {tika_server_port} 포트에서 시작되지 않았습니다.")

                source_path = os.path.join(root_path, source_path)

                server_url = f"http://localhost:{tika_server_port}/tika"

                for root, _, files in os.walk(source_path):
                    for file in files:
                        # if any(file.lower().endswith(ext) for ext in image_extensions):
                        image_path = os.path.join(root, file)
                        try:
                            metadata, body_info = extract_text_from_image(image_path, server_url)
                            # print(f"{file} 처리 완료, 추출된 텍스트: {text_data}")

                            save_as_json(image_path, json_data,metadata, body_info)

                        except Exception as e:
                            print(f"{file} 처리 중 오류 발생: {str(e)}")
            

    except Exception as e:
        info_message = f"Exception : {str(e)}"
        print(f"start_tika_server(): {info_message}")  
