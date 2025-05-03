# -*- coding: utf-8 -*-
import json
import re
import io
from datetime import datetime
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import traceback # 用于更详细的错误追踪

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 限制上传大小为 16MB (可选)

# --- Core Formatting Logic (与之前版本相同) ---
def format_chat_log(json_data):
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

            try:
                dt_object = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                formatted_time = dt_object.strftime('%Y-%m-%dT%H:%M:%S')
            except ValueError:
                print(f"警告：无法解析时间戳 '{timestamp_str}'。将使用原始值。")
                formatted_time = timestamp_str

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
    <title>JSON 聊天记录格式化工具 V4 - 果冻效果</title>
    <style>
        :root {
            --primary-color: #007bff;
            --primary-hover: #0056b3;
            /* *** 修改辉光颜色和透明度，使其更柔和 *** */
            --glow-color: rgba(0, 123, 255, 0.45);
            /* *** 修改背景色为超浅蓝 *** */
            --background-color: #e7f5ff; /* 超浅蓝色 */
            --text-color: #333;
            --border-color: #aecde0; /* 边框颜色配合浅蓝背景 */
            --drop-bg: #f0f8ff; /* 拖拽区背景也用浅蓝 */
            --drop-border-hover: #007bff;
            --success-color: #28a745;
            --error-color: #dc3545;
            --shadow-color: rgba(0, 80, 150, 0.1); /* 阴影颜色配合浅蓝 */
            --shadow-hover-color: rgba(0, 80, 150, 0.2);
        }
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: var(--background-color); /* 应用浅蓝背景 */
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
            /* 可以加个背景渐变增加趣味性（可选） */
            /* background-image: linear-gradient(to top, #e7f5ff 0%, #ffffff 100%); */
        }
        .container {
            background-color: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0, 80, 150, 0.08); /* 调整阴影配合背景 */
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
            margin-bottom: 30px;
            cursor: pointer;
            transition: border-color 0.3s ease, background-color 0.3s ease, box-shadow 0.3s ease;
            background-color: var(--drop-bg);
            box-shadow: 0 5px 15px var(--shadow-color);
            position: relative;
            overflow: hidden;
        }
        #drop-zone.drag-over {
            border-color: var(--drop-border-hover);
            background-color: #d6ebff; /* 拖拽悬停时更深的浅蓝 */
            box-shadow: 0 8px 20px var(--shadow-hover-color);
        }
        #drop-zone p {
            margin: 0;
            font-size: 1.1em;
            color: #4a6a80; /* 文字颜色配合背景 */
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

        /* --- 按钮样式调整 --- */
        #format-button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 15px 35px;
            font-size: 1.2em;
            font-weight: 500;
            border-radius: 50px;
            cursor: pointer;
            transition: background-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease; /* 调整 transform 过渡时间 */
            box-shadow: 0 4px 10px rgba(0, 123, 255, 0.25); /* 默认阴影调整 */
            /* 为了果冻效果，transform-origin 可能需要调整，但默认 center 通常可以 */
            /* transform-origin: center; */
        }
        #format-button:hover {
            background-color: var(--primary-hover);
            /* *** 修改为柔光效果：无偏移，增大模糊半径 *** */
            box-shadow: 0 0 22px var(--glow-color); /* 调整模糊半径和辉光颜色变量 */
            transform: translateY(-2px); /* 轻微上浮增加反馈 */
        }
         /* *** 果冻感动画 *** */
        @keyframes jelly-press {
            0% { transform: scale(1, 1) translateY(0); }
            30% { transform: scale(1.05, 0.9) translateY(0); } /* 水平拉伸，垂直压缩 */
            50% { transform: scale(0.9, 1.1) translateY(-3px); } /* 垂直拉伸，水平压缩，轻微上移 */
            70% { transform: scale(1.02, 0.98) translateY(0); } /* 回弹 */
            100% { transform: scale(1, 1) translateY(0); }
        }

        #format-button:active {
            /* 触发果冻动画 */
            animation: jelly-press 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); /* 使用回弹效果的贝塞尔曲线 */
            /* :active 时可以稍微改变背景色或阴影 */
            background-color: #004ca3; /* 按下时颜色更深一点 */
            box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3); /* 按下时阴影变小 */
            /* 覆盖 hover 的 transform */
            transform: translateY(0);
        }

        #format-button:disabled {
            background-color: #b8cde0; /* 禁用颜色配合背景 */
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
            color: #f0f8ff;
        }
        #status {
            margin-top: 25px;
            font-size: 1em;
            font-weight: 500;
            min-height: 1.5em;
        }
        .status-success { color: var(--success-color); }
        .status-error { color: var(--error-color); }
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
        <button id="format-button" disabled>请先选择文件</button>
        <div id="status"></div>
    </div>

    <script>
        // JavaScript 部分与 V3 版本相同，无需修改
        document.addEventListener('DOMContentLoaded', () => {
            console.log('DOM fully loaded and parsed');

            const dropZone = document.getElementById('drop-zone');
            const fileInput = document.getElementById('file-input');
            const formatButton = document.getElementById('format-button');
            const statusDiv = document.getElementById('status');
            const fileNameDisplay = document.getElementById('file-name');

            if (!dropZone || !fileInput || !formatButton || !statusDiv || !fileNameDisplay) {
                console.error('错误：一个或多个必要的页面元素未找到！请检查 HTML 的 ID 是否正确。');
                statusDiv.textContent = '页面初始化错误，请刷新重试！';
                statusDiv.className = 'status-error';
                return;
            }
            console.log('所有关键元素已找到。');

            let selectedFile = null;

            function isValidJsonFile(file) {
                if (!file) return false;
                const fileName = file.name || '';
                const fileType = file.type || '';
                const isValid = fileType === 'application/json' || fileName.toLowerCase().endsWith('.json');
                // console.log(`文件验证: Name=${fileName}, Type=${fileType}, IsValid=${isValid}`);
                return isValid;
            }

            function updateButtonState() {
                if (selectedFile) {
                    formatButton.disabled = false;
                    formatButton.textContent = '格式化并下载 TXT';
                } else {
                    formatButton.disabled = true;
                    formatButton.textContent = '请先选择文件';
                }
            }

            function handleFileSelect(file) {
                if (isValidJsonFile(file)) {
                    selectedFile = file;
                    fileNameDisplay.textContent = `已选: ${file.name}`;
                    showStatus('');
                    console.log('文件已选择:', file.name);
                } else {
                    selectedFile = null;
                    fileNameDisplay.textContent = '';
                    // 只有在确实选择了无效文件时才提示，拖放取消时不提示
                    if (file) {
                         showStatus('请选择有效的 JSON 文件 (.json)', 'error');
                    }
                    fileInput.value = '';
                    console.log('选择了无效的文件或没有选择文件');
                }
                updateButtonState();
            }

            dropZone.addEventListener('click', () => {
                console.log('Drop zone clicked - triggering file input click');
                fileInput.click();
            });
            dropZone.addEventListener('keydown', (event) => {
                 if (event.key === 'Enter' || event.key === ' ') {
                    console.log('Drop zone activated via keyboard');
                    fileInput.click();
                 }
            });

            fileInput.addEventListener('change', (event) => {
                console.log('File input change event fired');
                if (event.target.files && event.target.files.length > 0) {
                    console.log('文件已通过 input 选择:', event.target.files[0].name);
                    handleFileSelect(event.target.files[0]);
                } else {
                    console.log('文件选择被取消或无文件');
                    // 用户取消选择时，保持当前状态不变
                }
            });

            dropZone.addEventListener('dragenter', (event) => {
                event.preventDefault();
                event.stopPropagation();
                dropZone.classList.add('drag-over');
            });

            dropZone.addEventListener('dragover', (event) => {
                event.preventDefault();
                event.stopPropagation();
                dropZone.classList.add('drag-over');
                event.dataTransfer.dropEffect = 'copy';
            });

            dropZone.addEventListener('dragleave', (event) => {
                event.preventDefault();
                event.stopPropagation();
                if (!dropZone.contains(event.relatedTarget)) {
                    dropZone.classList.remove('drag-over');
                }
            });

            dropZone.addEventListener('drop', (event) => {
                event.preventDefault();
                event.stopPropagation();
                dropZone.classList.remove('drag-over');
                console.log('Drop event fired');

                const files = event.dataTransfer.files;
                if (files && files.length > 0) {
                    console.log(`文件已拖放: ${files.length} 个, 处理第一个: ${files[0].name}`);
                    handleFileSelect(files[0]);
                    try {
                       fileInput.files = files;
                    } catch (e) {
                       console.warn("无法直接设置 input.files (某些浏览器不允许)", e);
                    }
                } else {
                     console.log('拖放事件中未找到文件。');
                     handleFileSelect(null);
                }
            });

            formatButton.addEventListener('click', async () => {
                if (!selectedFile) {
                    showStatus('错误：没有选中的文件！', 'error');
                    console.log('格式化按钮点击，但 selectedFile 为空');
                    // 可以给按钮加一个短暂的震动效果提示错误
                    formatButton.style.animation = 'shake 0.5s ease-in-out';
                    setTimeout(() => formatButton.style.animation = '', 500);
                    return;
                }

                console.log('开始格式化文件:', selectedFile.name);
                formatButton.disabled = true; // 动画期间也禁用
                showStatus('正在处理...', 'processing');

                const formData = new FormData();
                formData.append('jsonFile', selectedFile, selectedFile.name);

                try {
                    const response = await fetch('/format', {
                        method: 'POST',
                        body: formData
                    });

                    console.log(`服务器响应状态: ${response.status}`);

                    if (response.ok) {
                        const blob = await response.blob();
                        console.log(`获取到 Blob 大小: ${blob.size}, 类型: ${blob.type}`);
                        if (blob.size === 0 && response.headers.get('Content-Length') !== '0') {
                            console.warn("服务器返回 Blob 大小为 0，但 Content-Length 不是 0");
                            // 可能仍需尝试下载
                            // throw new Error("服务器返回了空文件内容");
                        }

                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;

                        const disposition = response.headers.get('Content-Disposition');
                        let filename = `${selectedFile.name.replace(/\.[^/.]+$/, "")}_formatted.txt`;
                        if (disposition) {
                             const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?([^;]+)/i);
                             if (filenameMatch && filenameMatch[1]) {
                                try {
                                    filename = decodeURIComponent(filenameMatch[1].replace(/['"]/g, ''));
                                } catch (e) { console.warn("解码 header 文件名失败", e); }
                             } else {
                                const simpleFilenameMatch = disposition.match(/filename="([^"]+)"/i);
                                if (simpleFilenameMatch && simpleFilenameMatch[1]) filename = simpleFilenameMatch[1];
                             }
                        }

                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        a.remove();
                        showStatus('格式化完成！已开始下载。', 'success');
                        console.log(`下载已触发: ${filename}`);

                    } else {
                        let errorMsg = `处理失败 (HTTP ${response.status})`;
                        try {
                            const errorData = await response.json();
                            errorMsg += `: ${errorData.error || '未知服务器错误'}`;
                        } catch (e) {
                            try {
                                const errorText = await response.text();
                                errorMsg += `: ${errorText.substring(0, 100) || '(无详细信息)'}`; // 限制长度
                            } catch (e2) { errorMsg += " (无法读取错误详情)"; }
                        }
                        showStatus(errorMsg, 'error');
                        console.error('服务器错误:', errorMsg);
                    }

                } catch (error) {
                    showStatus(`发生客户端错误: ${error.message}`, 'error');
                    console.error('Fetch 或客户端处理出错:', error);
                } finally {
                    // 等待动画结束后再完全恢复按钮状态可能更好，但简单起见先直接恢复
                    updateButtonState();
                    console.log('格式化流程结束');
                }
            });

            function showStatus(message, type = 'info') {
                statusDiv.textContent = message;
                statusDiv.className = '';
                if (type === 'success') statusDiv.classList.add('status-success');
                else if (type === 'error') statusDiv.classList.add('status-error');
                else if (type === 'processing') statusDiv.classList.add('status-processing');
                // console.log(`状态更新 (${type}): ${message}`); // 减少日志噪音
            }

            // 添加一个简单的抖动动画，用于错误提示
            const styleSheet = document.createElement("style");
            styleSheet.textContent = `
                @keyframes shake {
                  10%, 90% { transform: translateX(-1px); }
                  20%, 80% { transform: translateX(2px); }
                  30%, 50%, 70% { transform: translateX(-3px); }
                  40%, 60% { transform: translateX(3px); }
                }
            `;
            document.head.appendChild(styleSheet);

            updateButtonState();
            showStatus('请拖放或点击选择一个 JSON 文件');
            console.log('页面脚本初始化完成。');
        });
    </script>
</body>
</html>
"""

# --- Flask Routes (与 V3 版本相同) ---
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

        print("开始格式化聊天记录...")
        formatted_text = format_chat_log(data)

        if formatted_text is None:
             print("错误：format_chat_log 返回 None")
             return jsonify({"error": "输入数据格式无效 (应为 JSON 对象列表)"}), 400
        print(f"聊天记录格式化完成，输出长度: {len(formatted_text)}")

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
            download_name=download_name # Flask 内部会处理 Content-Disposition
        )
        # 尝试改进 Content-Disposition 处理非ASCII文件名
        try:
            from urllib.parse import quote
            encoded_download_name = quote(download_name)
            # RFC 6266 推荐格式
            response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\"; filename*=UTF-8''{encoded_download_name}"
            print("设置了 Content-Disposition header (RFC 6266 格式)")
        except Exception as e:
             print(f"警告：设置 Content-Disposition 出错: {e}")
             # 回退到简单格式
             response.headers['Content-Disposition'] = f"attachment; filename=\"{download_name}\""

        print("文件发送成功。")
        return response

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
    print("启动 Flask 服务器 (V4 - 果冻效果)...")
    print("访问 http://127.0.0.1:5000 或 http://[你的局域网IP]:5000")
    print("按 Ctrl+C 停止服务器")
    print("---------------------------------------------")
    app.run(debug=True, host='0.0.0.0', port=5000)