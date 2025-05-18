import os
from flask import Flask, render_template_string, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import io # 用于在内存中处理文件
import json
import re

app = Flask(__name__)
app.secret_key = "another_very_secret_and_random_string_for_flash" # 生产环境应使用更安全的密钥
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 设置最大上传文件大小为16MB

# --- HTML模板字符串 ---
INDEX_HTML_STRING = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>聊天记录JSON清理工具 🧹✨</title>
    <style>
        :root {
            --primary-color: #007bff; /* 主题蓝 */
            --primary-hover-color: #0056b3;
            --secondary-color: #6c757d; /* 次要灰色 */
            --background-color: #f8f9fa; /* 更浅的背景灰 */
            --card-background-color: #ffffff;
            --text-color: #343a40;
            --border-color: #dee2e6;
            --success-bg: #d1e7dd;
            --success-text: #0f5132;
            --success-border: #badbcc;
            --error-bg: #f8d7da;
            --error-text: #842029;
            --error-border: #f5c2c7;
            --warning-bg: #fff3cd;
            --warning-text: #664d03;
            --warning-border: #ffecb5;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        body {
            font-family: var(--font-family); margin: 0; padding: 20px; background-color: var(--background-color);
            color: var(--text-color); display: flex; flex-direction: column; align-items: center;
            min-height: 100vh; box-sizing: border-box;
        }
        .container {
            background-color: var(--card-background-color); padding: 30px 40px; border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1); width: 100%; max-width: 650px;
            text-align: center; border: 1px solid var(--border-color);
        }
        h1 { color: var(--primary-color); margin-bottom: 15px; font-size: 2em; font-weight: 600; }
        h1 .emoji { font-size: 0.8em; vertical-align: middle; }
        p.description { margin-bottom: 25px; line-height: 1.7; color: #555; font-size: 1.1em; }
        .upload-area {
            border: 2px dashed var(--primary-color); border-radius: 8px; padding: 40px 20px;
            margin-bottom: 20px; cursor: pointer; transition: background-color 0.3s ease, border-color 0.3s ease;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            min-height: 150px;
        }
        .upload-area.highlight { background-color: #e9f5ff; border-color: var(--primary-hover-color); }
        .upload-area p { margin: 5px 0 0 0; color: var(--primary-color); font-weight: 500; font-size: 1.1em; }
        .upload-area .upload-icon { font-size: 2.5em; color: var(--primary-color); margin-bottom: 10px; }
        input[type="file"] { display: none; }
        .btn-submit {
            background-color: var(--primary-color); color: white; padding: 12px 25px; border: none;
            border-radius: 6px; cursor: pointer; font-size: 1.1em; font-weight: 500;
            transition: background-color 0.3s ease, transform 0.1s ease; display: block; width: 100%;
            margin-top: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .btn-submit:hover { background-color: var(--primary-hover-color); transform: translateY(-2px); }
        .btn-submit:active { transform: translateY(0); }
        .flash-messages { list-style-type: none; padding: 0; margin-top: 20px; margin-bottom: 20px; width: 100%; }
        .flash-messages li { padding: 12px 15px; margin-bottom: 10px; border-radius: 6px; font-size: 0.95em; text-align: left; border: 1px solid transparent; }
        .flash-messages .error { background-color: var(--error-bg); color: var(--error-text); border-color: var(--error-border); }
        .flash-messages .success { background-color: var(--success-bg); color: var(--success-text); border-color: var(--success-border); }
        .flash-messages .warning { background-color: var(--warning-bg); color: var(--warning-text); border-color: var(--warning-border); }
        #filename-display { margin-top: 10px; font-style: italic; color: var(--secondary-color); font-size: 0.9em; min-height: 1.2em; }
        .footer { margin-top: auto; padding: 25px 0; font-size: 0.95em; color: #777; text-align: center; }
        .footer a { color: var(--primary-color); text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>聊天记录JSON清理工具 <span class="emoji">🧹✨</span></h1>
        <p class="description">请将包含JSON聊天记录的 <code>.txt</code> 文件拖拽到下方区域，或点击选择文件。系统将自动提取对话内容，去除Markdown格式，并提供清理后的纯文本文件供您下载。</p>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <ul class="flash-messages">
            {% for category, message in messages %}
              <li class="{{ category }}">{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <form method="POST" enctype="multipart/form-data" action="/" id="upload-form">
            <label for="file-upload" class="upload-area" id="drop-area">
                <div class="upload-icon">📤</div>
                <p>将文件拖拽到此处，或点击选择</p>
                <p id="filename-display"></p>
            </label>
            <input type="file" name="file" id="file-upload" accept=".txt">
            <button type="submit" class="btn-submit">上传并处理</button>
        </form>
    </div>
    <div class="footer">
        <p>&copy; 专为青山与纸船喵 <span style="color: #e91e63;">❤️</span> 打造的小工具 (Gemini出品)</p>
        <p>遇到问题？可以尝试 <a href="mailto:ai.feedback.gemini@example.com?subject=ChatCleanerFeedback">联系开发者</a> (好吧，其实是联系训练我的团队)</p>
    </div>
    <script>
        const dropArea = document.getElementById('drop-area');
        const fileInput = document.getElementById('file-upload');
        const filenameDisplay = document.getElementById('filename-display');
        const uploadForm = document.getElementById('upload-form');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.body.addEventListener(eventName, preventDefaults, false);
            if (dropArea) dropArea.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

        if (dropArea) {
            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
            });
            ['dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
            });
            dropArea.addEventListener('drop', handleDrop, false);
        }

        if (fileInput) {
            fileInput.addEventListener('change', function(e) { handleFiles(e.target.files); });
        }

        function handleDrop(e) { let dt = e.dataTransfer; let files = dt.files; handleFiles(files); }
        
        function handleFiles(files) {
            if (files.length > 0) {
                const file = files[0];
                if (file.name.endsWith('.txt')) {
                    if (fileInput) fileInput.files = files;
                    if (filenameDisplay) filenameDisplay.textContent = `已选择: ${file.name}`;
                } else {
                    if (filenameDisplay) filenameDisplay.textContent = '错误: 仅支持 .txt 文件';
                    alert('只允许上传.txt文件！');
                    if (fileInput) fileInput.value = ''; 
                }
            } else {
                 if (filenameDisplay) filenameDisplay.textContent = '';
            }
        }

        if (uploadForm && fileInput) {
            uploadForm.addEventListener('submit', function(e) {
                if (fileInput.files.length === 0) {
                    e.preventDefault(); 
                    alert('请先选择一个文件再提交！');
                    if (filenameDisplay) filenameDisplay.textContent = '错误: 未选择文件';
                }
            });
        }
    </script>
</body>
</html>
"""

# --- Markdown 清理和核心处理逻辑 (与之前相同) ---
def clean_markdown_to_plain_text(text):
    if not isinstance(text, str):
        return ""
    text = text.replace('\\n', ' ')
    text = text.replace('\n', ' ')
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = text.replace('`', '')
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'^[ \t]*#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'^[ \t]*>\s?', '', text, flags=re.MULTILINE)
    text = text.replace('> ', ' ').replace('>', ' ')
    text = re.sub(r'^[ \t]*([*-+])\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = text.replace('- ', ' ')
    text = re.sub(r'^[ \t]*([-*_]){3,}[ \t]*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def process_chat_data_core(json_data_string):
    try:
        data = json.loads(json_data_string)
    except json.JSONDecodeError:
        raise ValueError("上传的文件不是有效的JSON格式。")

    processed_lines = []
    def extract_and_clean(chunks_list):
        if not isinstance(chunks_list, list):
            return
        for chunk in chunks_list:
            if not isinstance(chunk, dict):
                continue
            role = chunk.get("role")
            text_content = chunk.get("text")
            formatted_role = ""
            if role == "user":
                formatted_role = "(user)"
            elif role == "model":
                formatted_role = "(model)"

            if formatted_role:
                if text_content:
                    cleaned_text = clean_markdown_to_plain_text(text_content)
                    if cleaned_text:
                        processed_lines.append(f"{formatted_role}\n{cleaned_text}\n")

    chunked_prompt = data.get("chunkedPrompt", {})
    if isinstance(chunked_prompt, dict):
        extract_and_clean(chunked_prompt.get("chunks", []))
    extract_and_clean(data.get("pendingInputs", []))
    return processed_lines
# --- 核心处理逻辑结束 ---

ALLOWED_EXTENSIONS = {'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('没有文件被上传', 'error')
            return redirect(url_for('index')) # 使用 url_for 重定向
        file = request.files['file']
        if file.filename == '':
            flash('未选择任何文件', 'error')
            return redirect(url_for('index'))
        if file and allowed_file(file.filename):
            try:
                json_string = file.stream.read().decode("utf-8")
                processed_data_lines = process_chat_data_core(json_string)

                if not processed_data_lines:
                    flash('处理后的内容为空，请检查JSON结构或内容是否符合预期。', 'warning')
                    return redirect(url_for('index'))

                output_text_content = "\n".join(processed_data_lines)

                str_io = io.BytesIO()
                str_io.write(output_text_content.encode('utf-8'))
                str_io.seek(0)

                original_filename = secure_filename(file.filename)
                download_filename = f"cleaned_{os.path.splitext(original_filename)[0]}.txt"

                return send_file(
                    str_io,
                    mimetype='text/plain',
                    as_attachment=True,
                    download_name=download_filename
                )

            except ValueError as e:
                flash(str(e), 'error')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'处理文件时发生未知错误: {str(e)}', 'error')
                return redirect(url_for('index'))
        else:
            flash('只允许上传 .txt 格式的文件', 'error')
            return redirect(url_for('index'))

    # 渲染嵌入的HTML字符串
    return render_template_string(INDEX_HTML_STRING)

if __name__ == '__main__':
    # 现在不需要自动创建 templates 文件夹或 index.html 文件了
    app.run(debug=True, host='0.0.0.0', port=5000)