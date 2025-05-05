# -*- coding: utf-8 -*-
import json
import re
import io
from datetime import datetime, timezone
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import traceback # 用于更详细的错误追踪

# --- Flask App Initialization ---
app = Flask(__name__)
# *** 增加文件上传大小限制 (例如设置为 64MB) ***
# 64 * 1024 * 1024 字节 = 64 MB
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

# --- Core Formatting Logic (与 V5.2 相同) ---
def format_chat_log(json_data, show_timestamp=True):
    """
    将聊天消息字典列表格式化为所需的文本格式。
    Args:
        json_data: 字典列表，每个字典代表一条聊天消息。
        show_timestamp (bool): 是否在输出中包含时间戳行。默认为 True。
    Returns:
        包含格式化聊天记录的字符串，如果输入无效则返回 None。
    """
    if not isinstance(json_data, list):
        print("错误：输入数据不是列表。")
        return None

    formatted_lines = []
    for message in json_data:
        try:
            sender = message.get("sender", "未知发送者")
            content = message.get("content", "")
            timestamp_str = message.get("timestamp")

            line_parts = []

            if show_timestamp:
                formatted_time = ""
                if timestamp_str:
                    try:
                        temp_ts = timestamp_str.replace('Z', '+00:00')
                        dt_object = datetime.fromisoformat(temp_ts)
                        dt_object_naive = dt_object.replace(tzinfo=None)
                        formatted_time = dt_object_naive.strftime('%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        print(f"警告：解析时间戳 '{timestamp_str}' 失败，尝试截断。")
                        if len(timestamp_str) >= 19 and timestamp_str[4] == '-' and timestamp_str[10] == 'T' and timestamp_str[16] == ':':
                             formatted_time = timestamp_str[:19]
                        else:
                             formatted_time = f"[无法解析时间: {timestamp_str}]"
                    line_parts.append(formatted_time)
                else:
                    line_parts.append("[时间戳缺失]")

            # 清理内容时也考虑替换无法编码的字符（更早处理可能更好，但最后encode处处理是保底）
            cleaned_content = re.sub(r'\[图片\]\s*路径:.*', '[图片]', str(content), flags=re.IGNORECASE)
            cleaned_content = re.sub(r'\[视频\]\s*路径:.*', '[视频]', cleaned_content, flags=re.IGNORECASE)
            sender_content_line = f"{sender}：{cleaned_content}"
            line_parts.append(sender_content_line)

            formatted_lines.append("\n".join(line_parts))

        except Exception as e:
            msg_id = message.get('id', '未知ID')
            print(f"处理消息 {msg_id} 时发生意外错误: {e}")
            traceback.print_exc()
            formatted_lines.append(f"[错误：处理消息 {msg_id} 失败]")

    return "\n\n".join(formatted_lines)

# --- Frontend HTML, CSS, JS (与 V5.2 相同) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON 聊天记录格式化工具 V5.3 - 大文件与编码修复</title>
    <style>
        :root {
            --primary-color: #007bff; --primary-hover: #0056b3; --glow-color: rgba(0, 123, 255, 0.45);
            --background-color: #e7f5ff; --text-color: #333; --border-color: #aecde0; --drop-bg: #f0f8ff;
            --drop-border-hover: #007bff; --success-color: #28a745; --error-color: #dc3545;
            --shadow-color: rgba(0, 80, 150, 0.1); --shadow-hover-color: rgba(0, 80, 150, 0.2);
            --switch-bg: #ccc; --switch-bg-active: var(--primary-color); --switch-knob: white;
            --switch-glow: rgba(0, 123, 255, 0.7);
        }
        body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background-color: var(--background-color); color: var(--text-color); margin: 0; padding: 20px; box-sizing: border-box; }
        .container { background-color: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 25px rgba(0, 80, 150, 0.08); text-align: center; max-width: 600px; width: 100%; }
        h1 { color: var(--primary-color); margin-bottom: 30px; font-weight: 600; }
        #drop-zone { border: 3px dashed var(--border-color); border-radius: 8px; padding: 60px 30px; margin-bottom: 20px; cursor: pointer; transition: border-color 0.3s ease, background-color 0.3s ease, box-shadow 0.3s ease; background-color: var(--drop-bg); box-shadow: 0 5px 15px var(--shadow-color); position: relative; overflow: hidden; }
        #drop-zone.drag-over { border-color: var(--drop-border-hover); background-color: #d6ebff; box-shadow: 0 8px 20px var(--shadow-hover-color); }
        #drop-zone p { margin: 0; font-size: 1.1em; color: #4a6a80; pointer-events: none; }
        #file-input { display: none; }
        #file-name { font-size: 0.9em; color: #557; margin-top: 15px; min-height: 1.2em; word-break: break-all; }
        .setting-container { display: flex; align-items: center; justify-content: center; margin-bottom: 30px; gap: 10px; }
        .toggle-switch { position: relative; display: inline-block; width: 50px; height: 26px; cursor: pointer; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: var(--switch-bg); border-radius: 26px; transition: background-color 0.3s ease, box-shadow 0.3s ease; }
        .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background-color: var(--switch-knob); border-radius: 50%; transition: transform 0.3s ease; }
        .toggle-switch:hover .slider { box-shadow: 0 0 8px var(--switch-glow); }
        input:checked + .slider { background-color: var(--switch-bg-active); }
        input:checked + .slider:before { transform: translateX(24px); }
        .setting-label { font-size: 0.95em; color: #555; }
        #format-button { background-color: var(--primary-color); color: white; border: none; padding: 15px 35px; font-size: 1.2em; font-weight: 500; border-radius: 50px; cursor: pointer; transition: background-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease; box-shadow: 0 4px 10px rgba(0, 123, 255, 0.25); }
        #format-button:hover { background-color: var(--primary-hover); box-shadow: 0 0 22px var(--glow-color); transform: translateY(-2px); }
        @keyframes jelly-press { 0% { transform: scale(1, 1) translateY(0); } 30% { transform: scale(1.05, 0.9) translateY(0); } 50% { transform: scale(0.9, 1.1) translateY(-3px); } 70% { transform: scale(1.02, 0.98) translateY(0); } 100% { transform: scale(1, 1) translateY(0); } }
        #format-button:active { animation: jelly-press 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); background-color: #004ca3; box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3); transform: translateY(0); }
        #format-button:disabled { background-color: #b8cde0; cursor: not-allowed; box-shadow: none; transform: none; color: #f0f8ff; }
        #status { margin-top: 25px; font-size: 1em; font-weight: 500; min-height: 1.5em; }
        .status-success { color: var(--success-color); } .status-error { color: var(--error-color); } .status-processing { color: #555; }
    </style>
</head>
<body>
    <div class="container">
        <h1>JSON 聊天记录格式化</h1>
        <input type="file" id="file-input" accept=".json" aria-hidden="true">
        <div id="drop-zone" role="button" tabindex="0" aria-label="拖放或点击选择JSON文件">
            <p>将 JSON 文件拖拽到这里</p>
            <p>或 <span style="color: var(--primary-color); font-weight: bold;">点击选择文件</span></p>
            <p id="file-name"></p>
        </div>
        <div class="setting-container">
            <span class="setting-label">显示时间戳</span>
            <label class="toggle-switch">
                <input type="checkbox" id="timestamp-toggle" checked>
                <span class="slider"></span>
            </label>
        </div>
        <button id="format-button" disabled>请先选择文件</button>
        <div id="status"></div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const dropZone = document.getElementById('drop-zone'); const fileInput = document.getElementById('file-input');
            const formatButton = document.getElementById('format-button'); const statusDiv = document.getElementById('status');
            const fileNameDisplay = document.getElementById('file-name'); const timestampToggle = document.getElementById('timestamp-toggle');
            if (!dropZone || !fileInput || !formatButton || !statusDiv || !fileNameDisplay || !timestampToggle) { console.error('错误：页面元素未找到！'); statusDiv.textContent = '页面初始化错误！'; statusDiv.className = 'status-error'; return; }
            let selectedFile = null;
            function isValidJsonFile(file) { if (!file) return false; const fileName = file.name || ''; const fileType = file.type || ''; return fileType === 'application/json' || fileName.toLowerCase().endsWith('.json'); }
            function updateButtonState() { formatButton.disabled = !selectedFile; formatButton.textContent = selectedFile ? '格式化并下载 TXT' : '请先选择文件'; }
            function handleFileSelect(file) { if (isValidJsonFile(file)) { selectedFile = file; fileNameDisplay.textContent = `已选: ${file.name}`; showStatus(''); } else { selectedFile = null; fileNameDisplay.textContent = ''; if (file) { showStatus('请选择有效的 JSON 文件 (.json)', 'error'); } fileInput.value = ''; } updateButtonState(); }
            dropZone.addEventListener('click', () => { fileInput.click(); }); dropZone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { fileInput.click(); } }); fileInput.addEventListener('change', (event) => { if (event.target.files && event.target.files.length > 0) { handleFileSelect(event.target.files[0]); } }); dropZone.addEventListener('dragenter', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drag-over'); }); dropZone.addEventListener('dragover', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drag-over'); e.dataTransfer.dropEffect = 'copy'; }); dropZone.addEventListener('dragleave', (e) => { e.preventDefault(); e.stopPropagation(); if (!dropZone.contains(e.relatedTarget)) { dropZone.classList.remove('drag-over'); } }); dropZone.addEventListener('drop', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('drag-over'); const files = e.dataTransfer.files; if (files && files.length > 0) { handleFileSelect(files[0]); try { fileInput.files = files; } catch (ex) { console.warn("无法设置 input.files", ex); } } else { handleFileSelect(null); } });
            formatButton.addEventListener('click', async () => {
                if (!selectedFile) { showStatus('错误：没有选中的文件！', 'error'); formatButton.style.animation = 'shake 0.5s ease-in-out'; setTimeout(() => formatButton.style.animation = '', 500); return; }
                formatButton.disabled = true; showStatus('正在处理...', 'processing');
                const formData = new FormData(); formData.append('jsonFile', selectedFile, selectedFile.name);
                const showTimestamp = timestampToggle.checked; formData.append('showTimestamp', showTimestamp); console.log(`显示时间戳开关状态: ${showTimestamp}`);
                try {
                    const response = await fetch('/format', { method: 'POST', body: formData });
                    if (response.ok) { const blob = await response.blob(); const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.style.display = 'none'; a.href = url; const disposition = response.headers.get('Content-Disposition'); let filename = `${selectedFile.name.replace(/\.[^/.]+$/, "")}_formatted.txt`; if (disposition) { const m1 = disposition.match(/filename\*?=(?:UTF-8'')?([^;]+)/i); if (m1 && m1[1]) { try { filename = decodeURIComponent(m1[1].replace(/['"]/g, '')); } catch (e) {} } else { const m2 = disposition.match(/filename="([^"]+)"/i); if (m2 && m2[1]) filename = m2[1]; } } a.download = filename; document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url); a.remove(); showStatus('格式化完成！已开始下载。', 'success'); } else { let errorMsg = `处理失败 (HTTP ${response.status})`; try { const errorData = await response.json(); errorMsg += `: ${errorData.error || '未知错误'}`; } catch (e) { try { const errorText = await response.text(); errorMsg += `: ${errorText.substring(0, 100) || '(无信息)'}`; } catch (e2) {} } showStatus(errorMsg, 'error'); console.error('服务器错误:', errorMsg); }
                } catch (error) { showStatus(`客户端错误: ${error.message}`, 'error'); console.error('Fetch错误:', error); } finally { updateButtonState(); }
            });
            function showStatus(message, type = 'info') { statusDiv.textContent = message; statusDiv.className = ''; if (type === 'success') statusDiv.classList.add('status-success'); else if (type === 'error') statusDiv.classList.add('status-error'); else if (type === 'processing') statusDiv.classList.add('status-processing'); }
            const styleSheet = document.createElement("style"); styleSheet.textContent = `@keyframes shake { 10%, 90% { transform: translateX(-1px); } 20%, 80% { transform: translateX(2px); } 30%, 50%, 70% { transform: translateX(-3px); } 40%, 60% { transform: translateX(3px); }}`; document.head.appendChild(styleSheet);
            updateButtonState(); showStatus('请拖放或点击选择 JSON 文件'); console.log('页面脚本初始化完成。');
        });
    </script>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/format', methods=['POST'])
def format_file():
    print("\n收到 /format 请求")
    # 文件检查
    if 'jsonFile' not in request.files: return jsonify({"error": "缺少文件部分"}), 400
    file = request.files['jsonFile']
    if not file or file.filename == '': return jsonify({"error": "没有选择文件"}), 400
    original_filename = secure_filename(file.filename)
    if not (original_filename.lower().endswith('.json') or file.content_type == 'application/json'): return jsonify({"error": "不允许的文件类型"}), 400
    print(f"处理文件: '{original_filename}' ({file.content_type})")

    # 获取开关状态
    show_timestamp_str = request.form.get('showTimestamp', 'true')
    show_timestamp = show_timestamp_str.lower() == 'true'
    print(f"显示时间戳选项: {show_timestamp}")

    try:
        # 读取文件 (大小限制由 app.config['MAX_CONTENT_LENGTH'] 控制)
        print("开始读取文件内容...")
        # 检查文件大小是否真的超限 (虽然Flask会先拦截，但这里可以加日志)
        # file.seek(0, os.SEEK_END)
        # file_length = file.tell()
        # file.seek(0)
        # print(f"文件实际大小: {file_length} 字节")
        # if file_length > app.config['MAX_CONTENT_LENGTH']:
        #     return jsonify({"error": f"文件过大，超过服务器限制 ({app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024} MB)"}), 413 # Payload Too Large

        file_content = file.stream.read().decode('utf-8') # 假设输入文件是UTF-8
        print("文件内容读取完毕。")

        if not file_content.strip(): return jsonify({"error": "JSON 文件内容为空"}), 400

        # 解析 JSON
        print("开始解析 JSON...")
        data = json.loads(file_content)
        print("JSON 解析成功。")

        # 格式化
        print(f"开始格式化 (显示时间戳: {show_timestamp})...")
        formatted_text = format_chat_log(data, show_timestamp=show_timestamp)
        if formatted_text is None: return jsonify({"error": "输入数据格式无效"}), 400
        print("格式化完成。")

        # 创建内存文件并发送响应
        mem_file = io.BytesIO()
        # *** 修改点：添加 errors='replace' 处理编码错误 ***
        try:
            mem_file.write(formatted_text.encode('utf-8', errors='replace'))
            print("文本已成功编码为 UTF-8 (使用 'replace' 处理错误)")
        except Exception as encode_err:
             # 这个理论上不应该再发生 UnicodeEncodeError 了，但保留以防万一
             print(f"!!! 编码时发生意料之外的错误: {encode_err}")
             traceback.print_exc()
             return jsonify({"error": "在准备下载文件时发生内部编码错误"}), 500

        mem_file.seek(0)

        # 准备下载
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        download_name = f"{base_name}_formatted.txt"
        print(f"准备发送文件: '{download_name}'")

        response = send_file(
            mem_file,
            mimetype='text/plain; charset=utf-8',
            as_attachment=True,
            download_name=download_name
        )
        # 设置 Content-Disposition
        try:
            from urllib.parse import quote
            response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\"; filename*=UTF-8''{quote(download_name)}"
        except Exception: response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\""

        print("文件发送成功。")
        return response

    # 错误处理
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return jsonify({"error": f"无效的 JSON 文件: {e}"}), 400
    except UnicodeDecodeError:
        # 这个错误发生在 file.stream.read().decode('utf-8')
        print("文件编码错误，需要 UTF-8")
        return jsonify({"error": "文件编码错误，请确保上传的文件本身是 UTF-8 编码"}), 400
    except Exception as e:
        # 捕获其他所有错误，包括可能的 MAX_CONTENT_LENGTH 错误（虽然通常Flask会先拦截）
        print(f"处理文件时发生意外错误: {e}")
        # 检查是否是文件过大导致的 Werkzeug 错误
        if isinstance(e, werkzeug.exceptions.RequestEntityTooLarge):
             mb_limit = app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024
             print(f"错误原因：文件大小超过配置限制 ({mb_limit:.1f} MB)")
             return jsonify({"error": f"上传的文件过大，请确保小于 {mb_limit:.1f} MB"}), 413
        else:
            traceback.print_exc()
            return jsonify({"error": "处理文件时发生内部服务器错误"}), 500


# --- Main Execution ---
if __name__ == '__main__':
    # 导入 Werkzeug 异常，以便在 except 块中检查
    import werkzeug.exceptions

    print("---------------------------------------------")
    print("启动 Flask 服务器 (V5.3 - 大文件与编码修复)...")
    print(f"最大上传限制: {app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024:.1f} MB")
    print("访问 http://127.0.0.1:5000 或 http://[你的局域网IP]:5000")
    print("按 Ctrl+C 停止服务器")
    print("---------------------------------------------")
    app.run(debug=True, host='0.0.0.0', port=5000)