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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 限制上传大小为 16MB (可选)

# --- Core Formatting Logic (增加 keep_precision 参数) ---
def format_chat_log(json_data, keep_precision=False): # 添加新参数，默认False=删除
    """
    将聊天消息字典列表格式化为所需的文本格式。

    Args:
        json_data: 字典列表，每个字典代表一条聊天消息。
        keep_precision (bool): 是否保留时间戳的毫秒和时区指示符(Z)。默认为 False。

    Returns:
        包含格式化聊天记录的字符串，如果输入无效则返回 None。
    """
    if not isinstance(json_data, list):
        print("错误：输入数据不是列表。")
        return None

    formatted_lines = []
    for message in json_data:
        try:
            timestamp_str = message.get("timestamp")
            sender = message.get("sender", "未知发送者")
            content = message.get("content", "")

            if not timestamp_str:
                print(f"警告：因缺少时间戳而跳过消息：{message.get('id', '未知ID')}")
                continue

            # 格式化时间戳
            try:
                # 确保能处理带 Z 和不带 Z 的 ISO 格式
                if timestamp_str.endswith('Z'):
                    # fromisoformat 在 Python 3.11+ 可直接处理 Z，低版本需替换
                     try:
                         dt_object = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                     except AttributeError: # 兼容旧版 Python datetime 不支持 fromisoformat
                          # 备用解析方案，可能不完美
                          dt_object = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                else:
                    # 尝试直接解析可能不带时区的 ISO 格式
                     dt_object = datetime.fromisoformat(timestamp_str)
                     # 如果需要，可以假定它是本地时间或 UTC
                     # dt_object = dt_object.replace(tzinfo=timezone.utc) # 假设无Z即UTC

                # *** 根据 keep_precision 决定输出格式 ***
                if keep_precision:
                    # 保留毫秒和 Z (确保转换为 UTC 再格式化以正确显示 Z)
                    # 如果原对象非 UTC，先转为 UTC
                    dt_object_utc = dt_object.astimezone(timezone.utc)
                    # 格式化为 YYYY-MM-DDTHH:MM:SS.sssZ
                    # strftime 的 %f 输出微秒，需截断
                    formatted_time = dt_object_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                else:
                    # 删除毫秒和 Z，只保留到秒
                    formatted_time = dt_object.strftime('%Y-%m-%dT%H:%M:%S')

            except ValueError as e:
                print(f"警告：无法解析时间戳 '{timestamp_str}' ({e})。将使用原始值。")
                formatted_time = timestamp_str # 回退到原始字符串

            # 清理内容 (与之前相同)
            cleaned_content = re.sub(r'\[图片\]\s*路径:.*', '[图片]', str(content), flags=re.IGNORECASE)
            cleaned_content = re.sub(r'\[视频\]\s*路径:.*', '[视频]', cleaned_content, flags=re.IGNORECASE)

            formatted_lines.append(f"{formatted_time}\n{sender}：{cleaned_content}")

        except Exception as e:
            print(f"处理消息时出错: {message.get('id', '未知ID')}. 错误: {e}")
            formatted_lines.append(f"[错误：无法处理消息 {message.get('id', '')}]")

    return "\n\n".join(formatted_lines)

# --- Frontend HTML, CSS, JS ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON 聊天记录格式化工具 V5 - 时间精度开关</title>
    <style>
        :root {
            --primary-color: #007bff;
            --primary-hover: #0056b3;
            --glow-color: rgba(0, 123, 255, 0.45);
            --background-color: #e7f5ff;
            --text-color: #333;
            --border-color: #aecde0;
            --drop-bg: #f0f8ff;
            --drop-border-hover: #007bff;
            --success-color: #28a745;
            --error-color: #dc3545;
            --shadow-color: rgba(0, 80, 150, 0.1);
            --shadow-hover-color: rgba(0, 80, 150, 0.2);
            --switch-bg: #ccc;
            --switch-bg-active: var(--primary-color);
            --switch-knob: white;
            --switch-glow: rgba(0, 123, 255, 0.7); /* 开关辉光 */
        }
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: var(--background-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .container {
            background-color: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0, 80, 150, 0.08);
            text-align: center;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: var(--primary-color);
            margin-bottom: 30px;
            font-weight: 600;
        }
        #drop-zone {
            border: 3px dashed var(--border-color);
            border-radius: 8px;
            padding: 60px 30px;
            margin-bottom: 20px; /* 调整间距给开关留位 */
            cursor: pointer;
            transition: border-color 0.3s ease, background-color 0.3s ease, box-shadow 0.3s ease;
            background-color: var(--drop-bg);
            box-shadow: 0 5px 15px var(--shadow-color);
            position: relative;
            overflow: hidden;
        }
        #drop-zone.drag-over {
            border-color: var(--drop-border-hover);
            background-color: #d6ebff;
            box-shadow: 0 8px 20px var(--shadow-hover-color);
        }
        #drop-zone p {
            margin: 0;
            font-size: 1.1em;
            color: #4a6a80;
            pointer-events: none;
        }
         #file-input { display: none; }
        #file-name {
            font-size: 0.9em;
            color: #557;
            margin-top: 15px;
            min-height: 1.2em;
            word-break: break-all;
        }

        /* --- 开关样式 --- */
        .setting-container {
            display: flex;
            align-items: center;
            justify-content: center; /* 居中开关 */
            margin-bottom: 30px; /* 开关和按钮之间的距离 */
            gap: 10px; /* 文字和开关的间距 */
        }
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 50px; /* 开关宽度 */
            height: 26px; /* 开关高度 */
            cursor: pointer;
        }
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .slider {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--switch-bg);
            border-radius: 26px; /* 圆角 */
            transition: background-color 0.3s ease, box-shadow 0.3s ease; /* 添加阴影过渡 */
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 20px; /* 滑块高度 */
            width: 20px; /* 滑块宽度 */
            left: 3px; /* 滑块初始位置 */
            bottom: 3px;
            background-color: var(--switch-knob);
            border-radius: 50%; /* 圆形滑块 */
            transition: transform 0.3s ease;
        }
        /* 鼠标悬停在整个开关上时发光 */
        .toggle-switch:hover .slider {
             box-shadow: 0 0 8px var(--switch-glow);
        }
        input:checked + .slider {
            background-color: var(--switch-bg-active);
        }
        /* 选中状态下滑块的位置 */
        input:checked + .slider:before {
            transform: translateX(24px); /* 滑动距离 = 开关宽度 - 滑块宽度 - 2*左边距 */
        }
        .setting-label {
            font-size: 0.95em;
            color: #555;
        }

        /* --- 按钮样式 (与之前类似) --- */
        #format-button {
            background-color: var(--primary-color);
            color: white; border: none; padding: 15px 35px; font-size: 1.2em;
            font-weight: 500; border-radius: 50px; cursor: pointer;
            transition: background-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease;
            box-shadow: 0 4px 10px rgba(0, 123, 255, 0.25);
        }
        #format-button:hover {
            background-color: var(--primary-hover);
            box-shadow: 0 0 22px var(--glow-color);
            transform: translateY(-2px);
        }
        @keyframes jelly-press { /* 果冻动画 */
            0% { transform: scale(1, 1) translateY(0); } 30% { transform: scale(1.05, 0.9) translateY(0); }
            50% { transform: scale(0.9, 1.1) translateY(-3px); } 70% { transform: scale(1.02, 0.98) translateY(0); }
            100% { transform: scale(1, 1) translateY(0); }
        }
        #format-button:active {
            animation: jelly-press 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
            background-color: #004ca3; box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);
            transform: translateY(0);
        }
        #format-button:disabled {
            background-color: #b8cde0; cursor: not-allowed; box-shadow: none;
            transform: none; color: #f0f8ff;
        }
        #status { margin-top: 25px; font-size: 1em; font-weight: 500; min-height: 1.5em; }
        .status-success { color: var(--success-color); } .status-error { color: var(--error-color); }
        .status-processing { color: #555; }
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

        <!-- *** 新增：时间精度设置 *** -->
        <div class="setting-container">
            <span class="setting-label">保留可能是错误的时间</span>
            <label class="toggle-switch">
                <input type="checkbox" id="precision-toggle">
                <span class="slider"></span>
            </label>
        </div>
        <!-- *** 结束新增部分 *** -->

        <button id="format-button" disabled>请先选择文件</button>
        <div id="status"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            console.log('DOM fully loaded and parsed');

            const dropZone = document.getElementById('drop-zone');
            const fileInput = document.getElementById('file-input');
            const formatButton = document.getElementById('format-button');
            const statusDiv = document.getElementById('status');
            const fileNameDisplay = document.getElementById('file-name');
            // *** 获取新增的开关元素 ***
            const precisionToggle = document.getElementById('precision-toggle');

            if (!dropZone || !fileInput || !formatButton || !statusDiv || !fileNameDisplay || !precisionToggle) {
                console.error('错误：一个或多个必要的页面元素未找到！');
                statusDiv.textContent = '页面初始化错误，请刷新重试！';
                statusDiv.className = 'status-error';
                return;
            }
            console.log('所有关键元素已找到。');

            let selectedFile = null;

            function isValidJsonFile(file) { /* ... (与之前相同) ... */
                if (!file) return false;
                const fileName = file.name || '';
                const fileType = file.type || '';
                const isValid = fileType === 'application/json' || fileName.toLowerCase().endsWith('.json');
                return isValid;
            }
            function updateButtonState() { /* ... (与之前相同) ... */
                if (selectedFile) {
                    formatButton.disabled = false;
                    formatButton.textContent = '格式化并下载 TXT';
                } else {
                    formatButton.disabled = true;
                    formatButton.textContent = '请先选择文件';
                }
            }
            function handleFileSelect(file) { /* ... (与之前相同) ... */
                if (isValidJsonFile(file)) {
                    selectedFile = file;
                    fileNameDisplay.textContent = `已选: ${file.name}`;
                    showStatus('');
                    console.log('文件已选择:', file.name);
                } else {
                    selectedFile = null;
                    fileNameDisplay.textContent = '';
                    if (file) { showStatus('请选择有效的 JSON 文件 (.json)', 'error'); }
                    fileInput.value = '';
                    console.log('选择了无效的文件或没有选择文件');
                }
                updateButtonState();
            }

            // 事件监听器 (click, keydown, change, drag/drop) ... (与之前相同) ...
            dropZone.addEventListener('click', () => { fileInput.click(); });
            dropZone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { fileInput.click(); } });
            fileInput.addEventListener('change', (event) => { if (event.target.files && event.target.files.length > 0) { handleFileSelect(event.target.files[0]); } });
            dropZone.addEventListener('dragenter', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drag-over'); });
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drag-over'); e.dataTransfer.dropEffect = 'copy'; });
            dropZone.addEventListener('dragleave', (e) => { e.preventDefault(); e.stopPropagation(); if (!dropZone.contains(e.relatedTarget)) { dropZone.classList.remove('drag-over'); } });
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files && files.length > 0) {
                    handleFileSelect(files[0]);
                    try { fileInput.files = files; } catch (ex) { console.warn("无法设置 input.files", ex); }
                } else { handleFileSelect(null); }
            });

            // --- 格式化按钮点击处理 (修改) ---
            formatButton.addEventListener('click', async () => {
                if (!selectedFile) {
                    showStatus('错误：没有选中的文件！', 'error');
                    formatButton.style.animation = 'shake 0.5s ease-in-out';
                    setTimeout(() => formatButton.style.animation = '', 500);
                    return;
                }

                console.log('开始格式化文件:', selectedFile.name);
                formatButton.disabled = true;
                showStatus('正在处理...', 'processing');

                const formData = new FormData();
                formData.append('jsonFile', selectedFile, selectedFile.name);
                // *** 将开关状态添加到 FormData ***
                const keepPrecision = precisionToggle.checked;
                formData.append('keepPrecision', keepPrecision); // 发送 'true' 或 'false' 字符串
                console.log(`时间精度保留开关状态: ${keepPrecision}`);

                try {
                    const response = await fetch('/format', {
                        method: 'POST',
                        body: formData
                    });

                    console.log(`服务器响应状态: ${response.status}`);

                    if (response.ok) { // ... (下载逻辑与之前相同) ...
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none'; a.href = url;

                        const disposition = response.headers.get('Content-Disposition');
                        let filename = `${selectedFile.name.replace(/\.[^/.]+$/, "")}_formatted.txt`;
                        if (disposition) { /* ... (解析文件名逻辑) ... */
                             const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?([^;]+)/i);
                             if (filenameMatch && filenameMatch[1]) { try { filename = decodeURIComponent(filenameMatch[1].replace(/['"]/g, '')); } catch (e) { console.warn("解码文件名失败", e); }}
                             else { const simpleMatch = disposition.match(/filename="([^"]+)"/i); if (simpleMatch && simpleMatch[1]) filename = simpleMatch[1]; }
                        }

                        a.download = filename; document.body.appendChild(a); a.click();
                        window.URL.revokeObjectURL(url); a.remove();
                        showStatus('格式化完成！已开始下载。', 'success');
                        console.log(`下载已触发: ${filename}`);
                    } else { // ... (错误处理与之前相同) ...
                        let errorMsg = `处理失败 (HTTP ${response.status})`;
                        try {
                            const errorData = await response.json(); errorMsg += `: ${errorData.error || '未知服务器错误'}`;
                        } catch (e) { try { const errorText = await response.text(); errorMsg += `: ${errorText.substring(0, 100) || '(无信息)'}`; } catch (e2) { errorMsg += " (无法读取错误详情)"; }}
                        showStatus(errorMsg, 'error'); console.error('服务器错误:', errorMsg);
                    }
                } catch (error) { // ... (Fetch 错误处理与之前相同) ...
                    showStatus(`发生客户端错误: ${error.message}`, 'error');
                    console.error('Fetch 或客户端处理出错:', error);
                } finally { // ... (恢复按钮状态与之前相同) ...
                    updateButtonState();
                    console.log('格式化流程结束');
                }
            });

            function showStatus(message, type = 'info') { /* ... (与之前相同) ... */
                statusDiv.textContent = message; statusDiv.className = '';
                if (type === 'success') statusDiv.classList.add('status-success');
                else if (type === 'error') statusDiv.classList.add('status-error');
                else if (type === 'processing') statusDiv.classList.add('status-processing');
            }
            const styleSheet = document.createElement("style");
            styleSheet.textContent = `@keyframes shake { 10%, 90% { transform: translateX(-1px); } 20%, 80% { transform: translateX(2px); } 30%, 50%, 70% { transform: translateX(-3px); } 40%, 60% { transform: translateX(3px); }}`;
            document.head.appendChild(styleSheet);
            updateButtonState();
            showStatus('请拖放或点击选择一个 JSON 文件');
            console.log('页面脚本初始化完成。');
        });
    </script>
</body>
</html>
"""

# --- Flask Routes (修改 /format 路由) ---
@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/format', methods=['POST'])
def format_file():
    print("\n收到 /format 请求")
    if 'jsonFile' not in request.files:
        print("错误：请求中缺少 'jsonFile' 部分")
        return jsonify({"error": "请求中缺少文件部分"}), 400

    file = request.files['jsonFile']
    print(f"获取到文件: filename='{file.filename}', content_type='{file.content_type}'")

    if not file or file.filename == '':
        print("错误：未选择文件或文件名为空")
        return jsonify({"error": "没有选择文件"}), 400

    original_filename = secure_filename(file.filename)
    print(f"安全处理后的文件名: '{original_filename}'")

    if not (original_filename.lower().endswith('.json') or file.content_type == 'application/json'):
         print(f"错误：不允许的文件类型。文件名: {original_filename}, 类型: {file.content_type}")
         return jsonify({"error": "不允许的文件类型，请上传 .json 文件"}), 400

    # *** 获取时间精度开关状态 ***
    keep_precision_str = request.form.get('keepPrecision', 'false') # 从表单获取值，默认 'false'
    keep_precision = keep_precision_str.lower() == 'true' # 转换为布尔值
    print(f"接收到的时间精度保留选项: {keep_precision} (来自请求值: '{keep_precision_str}')")

    try:
        print("开始读取文件内容...")
        file_content = file.stream.read().decode('utf-8')
        print(f"文件内容读取完毕，长度: {len(file_content)} 字节")

        if not file_content.strip():
             print("错误：文件内容为空")
             return jsonify({"error": "JSON 文件内容不能为空"}), 400

        print("开始解析 JSON...")
        data = json.loads(file_content)
        print("JSON 解析成功。")

        print(f"开始格式化聊天记录 (保留精度: {keep_precision})...")
        # *** 将 keep_precision 传递给格式化函数 ***
        formatted_text = format_chat_log(data, keep_precision=keep_precision)

        if formatted_text is None:
             print("错误：format_chat_log 返回 None")
             return jsonify({"error": "输入数据格式无效 (应为 JSON 对象列表)"}), 400
        print(f"聊天记录格式化完成，输出长度: {len(formatted_text)}")

        # ... (创建内存文件和发送响应的逻辑与之前相同) ...
        mem_file = io.BytesIO()
        mem_file.write(formatted_text.encode('utf-8'))
        mem_file.seek(0)
        print("内存文件已准备好。")

        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        download_name = f"{base_name}_formatted.txt"
        print(f"准备发送文件，下载名: '{download_name}'")

        response = send_file(
            mem_file,
            mimetype='text/plain; charset=utf-8',
            as_attachment=True,
            download_name=download_name
        )
        try: # 设置 Content-Disposition (与之前相同)
            from urllib.parse import quote
            encoded_download_name = quote(download_name)
            response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\"; filename*=UTF-8''{encoded_download_name}"
        except Exception as e:
             print(f"警告：设置 Content-Disposition 出错: {e}")
             response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\""

        print("文件发送成功。")
        return response

    # ... (错误处理 except 块与之前相同) ...
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return jsonify({"error": f"无效的 JSON 文件: {e}"}), 400
    except UnicodeDecodeError:
        print("文件编码错误，需要 UTF-8")
        return jsonify({"error": "文件编码错误，请确保文件为 UTF-8 编码"}), 400
    except Exception as e:
        print(f"处理文件时发生意外错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "处理文件时发生内部服务器错误，请查看服务器日志"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    print("---------------------------------------------")
    print("启动 Flask 服务器 (V5 - 时间精度开关)...")
    print("访问 http://127.0.0.1:5000 或 http://[你的局域网IP]:5000")
    print("按 Ctrl+C 停止服务器")
    print("---------------------------------------------")
    app.run(debug=True, host='0.0.0.0', port=5000)