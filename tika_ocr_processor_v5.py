import os
import time
import json
import uuid
import datetime
import asyncio
import aiohttp
from tika import parser
from concurrent.futures import ThreadPoolExecutor
import itertools
import requests
import log_info
import logging
import threading
import concurrent.futures
import main_utility as main_ut
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # type: ignore


files_index_exception_count = 0
files_index_exception_count_lock = threading.Lock()

def config_reading(json_file_name):
    current_directory = os.getcwd()
    config_file = os.path.join(current_directory, json_file_name)
    if os.path.isfile(config_file):
        with open(config_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        log_info.status_info_print(f"{current_directory} - {json_file_name} 파일을 찾을 수 없습니다.")
        return None

def increment_files_index_exception_count():
    global files_index_exception_count
    with files_index_exception_count_lock:
        files_index_exception_count += 1

def create_session_with_retries():
    session = requests.Session()
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def check_tika_server(server_url):
    session = create_session_with_retries()
    try:
        response = session.get(server_url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        log_info.status_info_print(f"Failed to connect to Tika server at {server_url}: {e}")
        return False

def extract_text_from_image(file_path, server_url):
    headers = {
        "X-Tika-OCRLanguage": "kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara"
    }

    response = parser.from_file(file_path, headers=headers)

    if response is not None: 
        try:
            body_info = response.get('content', None)
            metainfo = response.get('metadata', None)
            return metainfo, body_info
        except Exception as e:
            log_info.status_info_print(f"{file_path}, Error with : {str(e)}")
            return None, None

def save_as_json(file_path, json_data, metainfo, body_info):
    try:
        root_path = json_data['root_path']
        json_path = json_data['elasticsearch']['normal_el_file_target_path']
        json_file_name = uuid.uuid4()
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        now = datetime.datetime.now()
        json_path = os.path.join(root_path, json_path)
        splitdrive_file_path = os.path.dirname(file_path)
        new_uuid = uuid.uuid4()
        utc_now = datetime.datetime.utcnow()
        timestamp = utc_now.timestamp()
        uuid_str = str(new_uuid) + '_' + str(timestamp)

    except Exception as e:
        message = f"{file_path}, meta 정보 생성 중 오류 발생 : {str(e)}"
        log_info.status_info_print(message)

    if not os.path.exists(json_path):
        os.makedirs(json_path, exist_ok=True)

    metadata_info, _ = main_ut.read_file_from_path(file_path, None, False)

    document_info = {
        "file": {},
        "tags": []
    }

    try:
        document_info["file"]["path"] = file_path
        document_info["file"]["extension"] = file_extension[1:]
        document_info["file"]["size"] = metadata_info["size"]
        document_info["file"]["mtime"] = metadata_info["mtime"]
        document_info["file"]["ctime"] = metadata_info["created"]
        document_info["file"]["meta_info"] = metadata_info
        document_info["root_path"] = root_path
        document_info["directory"] = splitdrive_file_path
        document_info["title"] = file_name
        document_info["uuid"] = uuid_str
        document_info["json_write_time"] = now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        if body_info is not None:
            document_info["content"] = body_info
            document_info["summary"] = body_info[:300]
            document_info["tags"].append("normal")
        if metainfo is not None:
            document_info["file"]["type"] = metainfo["Content-Type"]
            document_info["file"]["mime_type"] = metainfo["Content-Type"]
        else:
            document_info["file"]["type"] = metadata_info["mime_type"]
            document_info["file"]["mime_type"] = metadata_info["mime_type"]

        if body_info is None:
            document_info["tags"].append("exception")
        document_info["tags"].append("file")

    except Exception as e:
        document_info["tags"].append("exception")
        log_info.status_info_print(f"{file_path}, document_info 생성 중 오류 발생 : {str(e)}")

    try:
        result_file = os.path.join(json_path, f"{json_file_name}.json")
        with open(result_file, 'w', encoding='utf-8') as json_file:
            json.dump(document_info, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        message = f"{file_path}, JSON 생성 중 오류 발생 : {str(e)}"
        log_info.status_info_print(message)

def process_image(file_path, json_data, server_url):
    max_retries = 2
    try_count = 0

    while try_count < max_retries:
        try_count += 1

        try:
            if check_tika_server(server_url):
                start_time = time.time()
                metadata, body_info = extract_text_from_image(file_path, server_url)
                print(f"{file_path}, {body_info}")
                save_as_json(file_path, json_data, metadata, body_info)
                break
        except TimeoutError as e:
            if try_count >= max_retries:
                end_time = time.time()
                info_message = f"{file_path}, Timeout Error, (Time : {(end_time - start_time)}): {str(e)}"
        time.sleep(5)

def main():
    try:
        json_data = config_reading('config.json')
        if json_data is not None:
            datafilter = json_data['datafilter']
            image_extensions = datafilter['image_extensions']
            tika_app = json_data['tika_app']
            tika_server_ip = tika_app['tika_server_ip']
            tika_server_port = tika_app['tika_server_port']
            tika_ocr_server_count = tika_app['tika_ocr_server_count']
            max_tika_ocr_thread = tika_app['max_tika_ocr_thread']
            root_path = json_data['root_path']
            source_path = json_data['datainfopath']['source_path']
            source_path = os.path.join(root_path, source_path)

            server_urls = [f"http://{tika_server_ip}:{tika_server_port + i}/tika" for i in range(tika_ocr_server_count)]
            server_cycle = itertools.cycle(server_urls)

            try:
                with ThreadPoolExecutor(max_workers=max_tika_ocr_thread) as executor:
                    futures = []
                    for root, _, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if any(file_path.lower().endswith(ext) for ext in image_extensions):
                                server_url = next(server_cycle)
                                futures.append(executor.submit(process_image, file_path, json_data, server_url))
                            time.sleep(0.5)
                    concurrent.futures.wait(futures)
                    executor.shutdown(wait=True)
            except Exception as e:
                log_info.status_info_print(f"{file_path}, ThreadPool 오류 발생 : {str(e)}")

    except Exception as e:
        message = f"config.json 을 읽는 도중 오류 발생 : {str(e)}"
        log_info.status_info_print(message)

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    total_time = end_time - start_time
    log_info.status_info_print(f"total_time : {total_time:.2f}")
