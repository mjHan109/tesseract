# tesseract-ocr 및 language-pack(한국어, 영어, 일어, 중국어(간체,번체), 스페인, 프랑스, 아랍) 설치
# sudo apt-get install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim tesseract-ocr-chi-tra tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-ara

# tika-server start
# java -jar tika-server.jar --host 0.0.0.0 --port 9998 --enableImageOcr --ocrLanguage kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara


# 폴더 생성
# sudo mkdir -p /usr/local/share/tessdata

# language pack download
# wget https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
# wget https://github.com/tesseract-ocr/tessdata/raw/main/jpn.traineddata
# wget https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata
# wget https://github.com/tesseract-ocr/tessdata/raw/main/chi_tra.traineddata
# wget https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata
# wget https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata
# wget https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata
# wget https://github.com/tesseract-ocr/tessdata/raw/main/ara.traineddata

# 환경변수 설정
# export TESSDATA_PREFIX=/usr/local/share/


#1. 온라인 시스템에서 패키지 다운로드
#1.1 필요한 패키지 목록 작성
#mkdir -p ~/tesseract-offline
#cd ~/tesseract-offline
#apt-get download tesseract-ocr
#apt-get download tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim tesseract-ocr-chi-tra tesseract-ocr-kor

#1.2 종속성 패키지 다운로드
#apt-get download $(apt-rdepends tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim tesseract-ocr-chi-tra tesseract-ocr-kor | grep -v "^ " | grep -v "^\./")


#sudo apt-get install apt-rdepends


import subprocess
import os
import signal
import time
import socket
import json


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0
    
def start_tika_server(port_number, java_command):
    current_directory = os.getcwd()
    tika_server_path = os.path.join(current_directory, "tika-server.jar")
    if not is_port_in_use(port_number):

        # tika_command = f'nohup java -Xms512m -Xmx1024m -jar "{tika_server_path}" --port={port_number} --host 0.0.0.0 --enableImageOcr > /dev/null 2>&1 &'
      
        tika_command = f'{java_command} "{tika_server_path}" --port={port_number} --host 0.0.0.0 --enableImageOcr --ocrLanguage kor+eng+jpn+chi_sim+chi_tra+spa+fra+ara > /dev/null 2>&1 &'
        try:
            subprocess.run(tika_command, shell=True)
            print(f"start tika server : {tika_command}")
        except Exception as e:
            info_message = f"Exception : {str(e)}"
            print(f"start_tika_server(): {info_message}")     
        time.sleep(2)  # 5초간 대기

def kill_process_by_name(processor_name):
    
    print( f"\ncall kill tika-server : {processor_name}")  
    try:
        command = f"pkill -f '{processor_name}'"
        
        subprocess.run(command, shell=True)
        print(f"Killing process {command}")
        
    except Exception as e:
        info_message = f"kill_process_by_name:Exception 0-1: {processor_name} {str(e)}"
        print(f"kill_process_by_name(): {info_message}") 

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
    
if __name__ == "__main__":
    processes = []
    try:
        kill_process_by_name("tika-server")    
        time.sleep(1)

        json_data = config_reading('config.json')
        
        if json_data != None:
            # tika path info
            tika_app = json_data['tika_app']
            tika_app_jar_path = tika_app['tika_jar_path']
            tika_app_jar_name = tika_app['tika_jar_name']
            tika_server_ip = tika_app['tika_server_ip']
            tika_server_port = tika_app['tika_server_port']
            tika_server_count = tika_app['tika_server_count']
            max_tika_thread_num = tika_app['max_tika_thread_num']

            tika_xms = tika_app['tika_xms']
            tika_xmx = tika_app['tika_xmx']
            
            for i in range(tika_server_count):
                port = tika_server_port + i
                java_command = f"nohup java -Xms{tika_xms}m -Xmx{tika_xmx}m -jar"
                start_tika_server(tika_server_port + i, java_command)

    except Exception as e:
        info_message = f"Exception : {str(e)}"
        print(f"start_tika_server(): {info_message}")  
