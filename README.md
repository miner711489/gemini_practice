# gemini_practice

# 建立虛擬環境
```python -m venv ven ```

# 執行下載套件
```pip install google-generativeai```
```pip install google-api-core```

# 建立虛擬環境與安裝套件

1. 建立虛擬環境（建議用 venv）：
   ```bash
   python -m venv venv
   ```

2. 啟動虛擬環境：

   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. 安裝依賴套件：
   ```bash
   pip install -r requirements.txt
   ```

# 這是筆記 
只包含專案實際用到套件的 requirements.txt，推薦幾種方法：

方法一：pipreqs（最推薦）
pipreqs 是專門做這件事的工具。
它會根據你專案的程式碼自動分析 import，產生最小需求檔。

安裝 pipreqs
bash
pi install pipreqs
使用 pipreqs 產生 requirements.txt
bash
pipreqs ./ --force
./ 代表當前目錄（你可以換成你的專案資料夾路徑）。
--force 會覆蓋原本的 requirements.txt。
產生的 requirements.txt 就只會列出你專案程式碼有 import 到的套件！

# 未來預想：
1.使用flask做出畫面
2.使用json檔，來區分個小說的各路線，要有維護json檔功能


```pip install Flask```