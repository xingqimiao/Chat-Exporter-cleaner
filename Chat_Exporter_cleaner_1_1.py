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

# --- Core Formatting Logic (修改版 - 控制显示/隐藏时间) ---
def format_chat_log(json_data, show_timestamp=True): # 新参数控制是否显示时间，默认显示
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
            timestamp_str = message.get("timestamp") # 读取时间戳用于格式化(如果需要显示)

            line_parts = [] # 用列表存储当前消息的各个部分

            # --- 处理时间戳 (如果需要显示) ---
            if show_timestamp:
                formatted_time = "" # 初始化为空字符串
                if timestamp_str:
                    try:
                        # 尝试解析 ISO 格式时间戳，处理 'Z'
                        temp_ts = timestamp_str.replace('Z', '+00:00')
                        dt_object = datetime.fromisoformat(temp_ts)
                        # 强制移除时区，格式化为 YYYY-MM-DDTHH:MM:SS
                        dt_object_naive = dt_object.replace(tzinfo=None)
                        formatted_time = dt_object_naive.strftime('%Y-%m-%dT%H:%M:%S')
                        print(f"  格式化时间戳 (显示): {formatted_time}")
                    except ValueError:
                        print(f"警告：解析时间戳 '{timestamp_str}' 失败，尝试截断。")
                        # 解析失败，尝试截断
                        if len(timestamp_str) >= 19 and timestamp_str[4] == '-' and timestamp_str[10] == 'T' and timestamp_str[16] == ':':
                             formatted_time = timestamp_str[:19]
                             print(f"  截断时间戳 (显示): {formatted_time}")
                        else:
                             # 截断也失败或格式不对，使用原始字符串或特定标记
                             formatted_time = f"[无法解析时间: {timestamp_str}]"
                             print(f"  无法处理时间戳 (显示): {timestamp_str}")
                    line_parts.append(formatted_time) # 添加时间部分
                else:
                    # 时间戳字段不存在，但也要求显示时间
                    line_parts.append("[时间戳缺失]")
                    print("警告：消息缺少时间戳字段，但要求显示时间。")


            # --- 清理和添加发送者与内容 ---
            cleaned_content = re.sub(r'\[图片\]\s*路径:.*', '[图片]', str(content), flags=re.IGNORECASE)
            cleaned_content = re.sub(r'\[视频\]\s*路径:.*', '[视频]', cleaned_content, flags=re.IGNORECASE)
            sender_content_line = f"{sender}：{cleaned_content}"
            line_parts.append(sender_content_line) # 添加发送者和内容部分

            # --- 组合当前消息的输出 ---
            formatted_lines.append("\n".join(line_parts)) # 使用换行符连接时间(如果存在)和内容

        except Exception as e:
            # 捕获处理单个消息时的其他意外错误
            msg_id = message.get('id', '未知ID')
            print(f"处理消息 {msg_id} 时发生意外错误: {e}")
            traceback.print_exc()
            formatted_lines.append(f"[错误：处理消息 {msg_id} 失败]")

    # 使用两个换行符连接所有消息块
    return "\n\n".join(formatted_lines)

# --- Frontend HTML, CSS, JS ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON 聊天记录格式化工具 V5.2 - 显示/隐藏时间戳</title>
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
        /* 开关样式 */
        .setting-container { display: flex; align-items: center; justify-content: center; margin-bottom: 30px; gap: 10px; }
        .toggle-switch { position: relative; display: inline-block; width: 50px; height: 26px; cursor: pointer; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: var(--switch-bg); border-radius: 26px; transition: background-color 0.3s ease, box-shadow 0.3s ease; }
        .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background-color: var(--switch-knob); border-radius: 50%; transition: transform 0.3s ease; }
        .toggle-switch:hover .slider { box-shadow: 0 0 8px var(--switch-glow); }
        input:checked + .slider { background-color: var(--switch-bg-active); }
        input:checked + .slider:before { transform: translateX(24px); }
        .setting-label { font-size: 0.95em; color: #555; }
        /* 按钮样式 */
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

        <!-- 时间戳显示开关 (默认开启) -->
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
            console.log('DOM fully loaded and parsed');

            // 获取必要的 DOM 元素
            const dropZone = document.getElementById('drop-zone');
            const fileInput = document.getElementById('file-input');
            const formatButton = document.getElementById('format-button');
            const statusDiv = document.getElementById('status');
            const fileNameDisplay = document.getElementById('file-name');
            // 获取新的时间戳开关元素
            const timestampToggle = document.getElementById('timestamp-toggle');

            // 检查元素是否存在
            if (!dropZone || !fileInput || !formatButton || !statusDiv || !fileNameDisplay || !timestampToggle) {
                console.error('错误：一个或多个必要的页面元素未找到！请检查 HTML ID。');
                statusDiv.textContent = '页面初始化错误，请刷新重试！';
                statusDiv.className = 'status-error';
                return; // 阻止后续代码执行
            }
            console.log('所有关键元素已找到。');

            let selectedFile = null; // 跟踪选择的文件

            // 验证文件是否为 JSON
            function isValidJsonFile(file) {
                if (!file) return false;
                const fileName = file.name || '';
                const fileType = file.type || '';
                return fileType === 'application/json' || fileName.toLowerCase().endsWith('.json');
            }

            // 更新格式化按钮的状态
            function updateButtonState() {
                formatButton.disabled = !selectedFile;
                formatButton.textContent = selectedFile ? '格式化并下载 TXT' : '请先选择文件';
            }

            // 处理文件选择（通过点击或拖放）
            function handleFileSelect(file) {
                if (isValidJsonFile(file)) {
                    selectedFile = file;
                    fileNameDisplay.textContent = `已选: ${file.name}`;
                    showStatus(''); // 清除状态
                    console.log('文件已选择:', file.name);
                } else {
                    selectedFile = null;
                    fileNameDisplay.textContent = '';
                    if (file) { // 只有在确实选择了无效文件时才提示
                         showStatus('请选择有效的 JSON 文件 (.json)', 'error');
                    }
                    fileInput.value = ''; // 清空 file input 的值
                    console.log('选择了无效的文件或没有选择文件');
                }
                updateButtonState(); // 更新按钮状态
            }

            // --- 事件监听器 ---
            // 点击拖拽区触发文件选择
            dropZone.addEventListener('click', () => { fileInput.click(); });
            // 键盘激活拖拽区
            dropZone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { fileInput.click(); } });
            // 文件输入框内容改变
            fileInput.addEventListener('change', (event) => { if (event.target.files && event.target.files.length > 0) { handleFileSelect(event.target.files[0]); } });
            // 拖放事件
            dropZone.addEventListener('dragenter', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drag-over'); });
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drag-over'); e.dataTransfer.dropEffect = 'copy'; });
            dropZone.addEventListener('dragleave', (e) => { e.preventDefault(); e.stopPropagation(); if (!dropZone.contains(e.relatedTarget)) { dropZone.classList.remove('drag-over'); } });
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files && files.length > 0) {
                    handleFileSelect(files[0]);
                    try { fileInput.files = files; } catch (ex) { console.warn("无法设置 input.files", ex); } // 尝试设置，失败也无妨
                } else { handleFileSelect(null); } // 没有文件则清除选择
            });

            // 格式化按钮点击事件
            formatButton.addEventListener('click', async () => {
                if (!selectedFile) {
                    showStatus('错误：没有选中的文件！', 'error');
                    // 给按钮加抖动提示
                    formatButton.style.animation = 'shake 0.5s ease-in-out';
                    setTimeout(() => formatButton.style.animation = '', 500);
                    return;
                }

                console.log('开始格式化文件:', selectedFile.name);
                formatButton.disabled = true; // 禁用按钮
                showStatus('正在处理...', 'processing'); // 显示处理状态

                const formData = new FormData();
                formData.append('jsonFile', selectedFile, selectedFile.name);

                // 获取 "显示时间戳" 开关状态并添加到 FormData
                const showTimestamp = timestampToggle.checked;
                formData.append('showTimestamp', showTimestamp); // 发送 'true' 或 'false'
                console.log(`显示时间戳开关状态: ${showTimestamp}`);

                try {
                    // 发送 POST 请求到后端 /format
                    const response = await fetch('/format', {
                        method: 'POST',
                        body: formData
                    });

                    console.log(`服务器响应状态: ${response.status}`);

                    if (response.ok) {
                        // 处理成功响应：触发下载
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;

                        // 解析或生成下载文件名
                        const disposition = response.headers.get('Content-Disposition');
                        let filename = `${selectedFile.name.replace(/\.[^/.]+$/, "")}_formatted.txt`; // 默认名
                        if (disposition) {
                             // 尝试从 Content-Disposition 解析更准确的文件名
                             const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?([^;]+)/i);
                             if (filenameMatch && filenameMatch[1]) {
                                try { filename = decodeURIComponent(filenameMatch[1].replace(/['"]/g, '')); } catch (e) { console.warn("解码 header 文件名失败", e); }
                             } else {
                                const simpleFilenameMatch = disposition.match(/filename="([^"]+)"/i);
                                if (simpleFilenameMatch && simpleFilenameMatch[1]) { filename = simpleFilenameMatch[1]; }
                             }
                        }

                        a.download = filename;
                        document.body.appendChild(a);
                        a.click(); // 模拟点击触发下载

                        // 清理
                        window.URL.revokeObjectURL(url);
                        a.remove();
                        showStatus('格式化完成！已开始下载。', 'success'); // 显示成功状态
                        console.log(`下载已触发: ${filename}`);

                    } else {
                        // 处理服务器错误响应
                        let errorMsg = `处理失败 (HTTP ${response.status})`;
                        try { // 尝试解析 JSON 错误体
                            const errorData = await response.json();
                            errorMsg += `: ${errorData.error || '未知服务器错误'}`;
                        } catch (e) { // 如果不是 JSON，尝试读取文本
                            try {
                                const errorText = await response.text();
                                errorMsg += `: ${errorText.substring(0, 100) || '(无详细信息)'}`; // 限制错误文本长度
                            } catch (e2) { errorMsg += " (无法读取错误详情)"; }
                        }
                        showStatus(errorMsg, 'error'); // 显示错误状态
                        console.error('服务器错误:', errorMsg);
                    }
                } catch (error) {
                    // 处理网络错误或其他客户端错误
                    showStatus(`发生客户端错误: ${error.message}`, 'error');
                    console.error('Fetch 或客户端处理出错:', error);
                } finally {
                    // 无论成功失败，最后都恢复按钮状态
                    updateButtonState();
                    console.log('格式化流程结束');
                }
            });

            // 显示状态消息的辅助函数
            function showStatus(message, type = 'info') {
                statusDiv.textContent = message;
                statusDiv.className = ''; // 清除旧类
                if (type === 'success') statusDiv.classList.add('status-success');
                else if (type === 'error') statusDiv.classList.add('status-error');
                else if (type === 'processing') statusDiv.classList.add('status-processing');
            }

            // 添加简单的抖动动画 CSS (用于错误提示)
            const styleSheet = document.createElement("style");
            styleSheet.textContent = `@keyframes shake { 10%, 90% { transform: translateX(-1px); } 20%, 80% { transform: translateX(2px); } 30%, 50%, 70% { transform: translateX(-3px); } 40%, 60% { transform: translateX(3px); }}`;
            document.head.appendChild(styleSheet);

            // 初始化页面状态
            updateButtonState(); // 设置初始按钮状态
            showStatus('请拖放或点击选择一个 JSON 文件'); // 显示初始提示
            console.log('页面脚本初始化完成。');

        }); // 结束 DOMContentLoaded
    </script>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def index():
    """提供主 HTML 页面。"""
    return HTML_TEMPLATE

@app.route('/format', methods=['POST'])
def format_file():
    """处理文件上传、格式化和下载。"""
    print("\n收到 /format 请求")
    # 检查文件是否存在
    if 'jsonFile' not in request.files:
        print("错误：请求中缺少 'jsonFile' 部分")
        return jsonify({"error": "请求中缺少文件部分"}), 400

    file = request.files['jsonFile']
    print(f"获取到文件: filename='{file.filename}', content_type='{file.content_type}'")

    # 检查文件名和是否选择了文件
    if not file or file.filename == '':
        print("错误：未选择文件或文件名为空")
        return jsonify({"error": "没有选择文件"}), 400

    # 安全处理文件名并检查类型
    original_filename = secure_filename(file.filename)
    print(f"安全处理后的文件名: '{original_filename}'")
    if not (original_filename.lower().endswith('.json') or file.content_type == 'application/json'):
         print(f"错误：不允许的文件类型。文件名: {original_filename}, 类型: {file.content_type}")
         return jsonify({"error": "不允许的文件类型，请上传 .json 文件"}), 400

    # 获取 "显示时间戳" 开关状态
    show_timestamp_str = request.form.get('showTimestamp', 'true') # 从表单获取，默认'true'
    show_timestamp = show_timestamp_str.lower() == 'true' # 转为布尔值
    print(f"接收到的显示时间戳选项: {show_timestamp} (来自请求值: '{show_timestamp_str}')")

    try:
        # 读取和解码文件内容
        print("开始读取文件内容...")
        file_content = file.stream.read().decode('utf-8')
        print(f"文件内容读取完毕，长度: {len(file_content)} 字节")

        # 检查文件内容是否为空
        if not file_content.strip():
             print("错误：文件内容为空")
             return jsonify({"error": "JSON 文件内容不能为空"}), 400

        # 解析 JSON 数据
        print("开始解析 JSON...")
        data = json.loads(file_content)
        print("JSON 解析成功。")

        # 调用核心格式化函数，传入显示时间戳的选项
        print(f"开始格式化聊天记录 (显示时间戳: {show_timestamp})...")
        formatted_text = format_chat_log(data, show_timestamp=show_timestamp)

        # 检查格式化结果
        if formatted_text is None:
             print("错误：format_chat_log 返回 None")
             return jsonify({"error": "输入数据格式无效 (应为 JSON 对象列表)"}), 400
        print(f"聊天记录格式化完成，输出长度: {len(formatted_text)}")

        # 创建内存文件用于响应
        mem_file = io.BytesIO()
        mem_file.write(formatted_text.encode('utf-8'))
        mem_file.seek(0)
        print("内存文件已准备好。")

        # 准备下载文件名
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        download_name = f"{base_name}_formatted.txt"
        print(f"准备发送文件，下载名: '{download_name}'")

        # 使用 send_file 发送文件响应
        response = send_file(
            mem_file,
            mimetype='text/plain; charset=utf-8',
            as_attachment=True,
            download_name=download_name # Flask 会处理基本的 Content-Disposition
        )
        # 尝试设置更兼容的 Content-Disposition 头，处理非 ASCII 文件名
        try:
            from urllib.parse import quote
            encoded_download_name = quote(download_name)
            response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\"; filename*=UTF-8''{encoded_download_name}"
            print("设置了 Content-Disposition header (RFC 6266 格式)")
        except Exception as e:
             print(f"警告：设置 Content-Disposition 出错: {e}")
             # 回退到简单格式，可能对某些浏览器或非ASCII文件名支持不好
             response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\""

        print("文件发送成功。")
        return response

    # 统一的错误处理块
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return jsonify({"error": f"无效的 JSON 文件: {e}"}), 400
    except UnicodeDecodeError:
        print("文件编码错误，需要 UTF-8")
        return jsonify({"error": "文件编码错误，请确保文件为 UTF-8 编码"}), 400
    except Exception as e:
        # 捕获所有其他未预料到的错误
        print(f"处理文件时发生意外错误: {e}")
        traceback.print_exc() # 打印完整错误堆栈到服务器控制台
        return jsonify({"error": "处理文件时发生内部服务器错误，请查看服务器日志"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    print("---------------------------------------------")
    print("启动 Flask 服务器 (V5.2 - 显示/隐藏时间戳)...")
    print("访问 http://127.0.0.1:5000 或 http://[你的局域网IP]:5000")
    print("按 Ctrl+C 停止服务器")
    print("---------------------------------------------")
    # debug=True 用于开发，自动重载代码。生产环境应设为 False 并使用生产级服务器如 Gunicorn/uWSGI
    app.run(debug=True, host='0.0.0.0', port=5000)