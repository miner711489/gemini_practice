import os
from opencc import OpenCC
##需要安裝套件，指令：pip install opencc

## 簡體轉繁體
## 這個程式會將指定資料夾下的所有 .txt 檔案的內容從簡體中文轉換為繁體中文。
def convert_file(file_path, output_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    cc = OpenCC("s2t")  # s2t: Simplified Chinese to Traditional Chinese
    converted_content = cc.convert(content)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(converted_content)


def process_directory(directory_path):
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            output_file_path = os.path.join(
                directory_path, filename.replace(".txt", "_繁體.txt")
            )
            convert_file(file_path, output_file_path)
            
            print(f"Converted {filename} to {output_file_path}")


if __name__ == "__main__":
    directory_path = input("請輸入資料夾路徑: ")
    process_directory(directory_path)
