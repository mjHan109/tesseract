import os
import json
import requests
import multiprocessing
from itertools import cycle

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
    
import os
import requests
import multiprocessing
from itertools import cycle

def extract_text_from_image(file_content, tika_server_url):
    """
    Tika 서버에 이미지 파일을 업로드하여 텍스트 정보를 추출하는 함수

    Args:
        file_content (bytes): 분석할 이미지 파일의 바이너리 콘텐츠
        tika_server_url (str): Tika 서버의 URL

    Returns:
        str: 추출된 텍스트 정보
    """
    headers = {
        'Accept': 'text/plain; charset=UTF-8'  # 다중 언어 인코딩 설정
    }
    try:
        response = requests.put(tika_server_url, headers=headers, data=file_content)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외를 발생시킵니다.
        response.encoding = 'utf-8'  # 응답의 인코딩 설정
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to analyze file with Tika server at {tika_server_url}: {str(e)}")

def process_file(file_path, tika_server_url):
    """
    단일 파일을 처리하는 함수

    Args:
        file_path (str): 분석할 파일의 경로
        tika_server_url (str): Tika 서버의 URL

    Returns:
        None
    """
    print(f"Processing file: {file_path} on server: {tika_server_url}")
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()
            result = extract_text_from_image(file_content, tika_server_url)
            print(f"Extracted text from {file_path}:\n{result}\n")
    except Exception as e:
        print(f"Error processing {file_path} on server {tika_server_url}: {e}")

def process_folder(folder_path, tika_server_urls):
    """
    주어진 폴더 내의 모든 파일을 멀티프로세싱을 사용하여 처리하는 함수

    Args:
        folder_path (str): 분석할 파일이 있는 폴더 경로
        tika_server_urls (list): 사용 가능한 Tika 서버의 URL 목록

    Returns:
        None
    """
    file_paths = [os.path.join(root, file_name) 
                  for root, _, files in os.walk(folder_path) 
                  for file_name in files]
    
    server_cycle = cycle(tika_server_urls)

    with multiprocessing.Pool(processes=len(tika_server_urls)) as pool:
        pool.starmap(process_file, [(file_path, next(server_cycle)) for file_path in file_paths])

if __name__ == "__main__":

    tika_server_urls = []

    try:
        json_data = config_reading('config.json')
        
        if json_data != None:
            # tika path info
            datainfopath = json_data['datainfopath']
            target_path = datainfopath['target_path']

            tika_app = json_data['tika_app']
            tika_server_ip = tika_app['tika_server_ip']
            tika_server_port = tika_app['tika_server_port']
            tika_server_count = tika_app['tika_server_count']
            
            for i in range(tika_server_count):
                port = tika_server_port + i
                java_command = f"http://{tika_server_ip}:{port}/tika"
                tika_server_urls.append(java_command)

        process_folder(target_path, tika_server_urls)
    except Exception as e:
        print(f"Error processing folder {target_path}: {e}")
