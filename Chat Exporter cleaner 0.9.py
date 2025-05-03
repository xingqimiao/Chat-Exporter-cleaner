import os
import re
from flask import Flask, request, Response, render_template_string, flash, redirect, url_for
import secrets

app = Flask(__name__)

# --- 配置 (保持不变) ---
app.secret_key = secrets.token_hex(16)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 Megabytes

# --- 核心清理函数 (保持不变) ---
def clean_text_content(text_content, remove_timestamp=True):
    # ... (function logic remains the same) ...
    image_marker = "[图片] 路径: "
    video_marker = "[视频] 路径: "
    timestamp_pattern = r"^\d+\s+"
    processed_lines = []
    lines = text_content.splitlines()

    for line in lines:
        if remove_timestamp:
            current_line_after_ts = re.sub(timestamp_pattern, '', line)
        else:
            current_line_after_ts = line

        img_index = current_line_after_ts.find(image_marker)
        vid_index = current_line_after_ts.find(video_marker)

        trunc_index = -1
        if img_index != -1 and vid_index != -1:
            trunc_index = min(img_index, vid_index)
        elif img_index != -1:
            trunc_index = img_index
        elif vid_index != -1:
            trunc_index = vid_index

        final_line_content = ""
        if trunc_index != -1:
            final_line_content = current_line_after_ts[:trunc_index].rstrip()
        else:
            final_line_content = current_line_after_ts.rstrip()

        if final_line_content or line.strip() == '':
             processed_lines.append(final_line_content)

    return '\n'.join(processed_lines)


# --- HTML & CSS & JavaScript 模板 (CSS & HTML for Toggle Switch) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>次元聊天记录整理术</title>
    <style>
        /* ... (body, container, h1, p, upload-area, file-info, submit-button, flash-messages styles remain the same) ... */
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 20px;
            background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%); color: #333; display: flex; justify-content: center; align-items: center; min-height: 100vh; box-sizing: border-box;
        }
        .container {
            background-color: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px) saturate(150%); -webkit-backdrop-filter: blur(12px) saturate(150%);
            padding: 35px 45px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 8px 32px rgba(100, 100, 150, 0.2);
            text-align: center; max-width: 650px; width: 95%; transition: box-shadow 0.3s ease;
        }
        .container:hover { box-shadow: 0 12px 40px rgba(100, 100, 150, 0.25); }
        h1 { color: #1a2b4d; margin-bottom: 25px; font-weight: 600; }
        p { color: #4a5568; margin-bottom: 35px; line-height: 1.7; }
        .upload-area {
            border: 2px dashed #60a5fa; border-radius: 10px; padding: 50px 25px; margin-bottom: 25px; background-color: rgba(240, 245, 255, 0.6);
            transition: background-color 0.3s ease, border-color 0.3s ease; cursor: pointer; position: relative; overflow: hidden;
        }
        .upload-area.dragover { background-color: rgba(220, 235, 255, 0.8); border-color: #2563eb; }
        .upload-area p { margin: 0; color: #4a5568; font-size: 1.15em; font-weight: 500; }
        .upload-area span { display: block; margin-top: 12px; font-size: 0.95em; color: #2563eb; font-weight: 600; }
        #fileInput { display: none; } /* Removed 'required' attribute from the input tag below */
        #file-info { margin-top: 20px; font-weight: 500; color: #10b981; min-height: 1.2em; }
        #file-info.error { color: #ef4444; }

        /* --- Toggle Switch Styles --- */
        .options-container {
            display: flex; /* Use flexbox for alignment */
            align-items: center; /* Center items vertically */
            justify-content: flex-start; /* Align to the left */
            margin-bottom: 30px;
            padding-left: 5px;
        }

        .switch {
            position: relative;
            display: inline-block;
            width: 50px; /* Width of the switch */
            height: 26px; /* Height of the switch */
            margin-right: 12px; /* Space between switch and text */
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc; /* Default off color */
            transition: .4s ease, box-shadow .3s ease; /* Added box-shadow transition */
            border-radius: 26px; /* Fully rounded */
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 20px; /* Knob height */
            width: 20px; /* Knob width */
            left: 3px; /* Initial position */
            bottom: 3px; /* Initial position */
            background-color: white;
            transition: .4s ease;
            border-radius: 50%; /* Circular knob */
            box-shadow: 0 1px 3px rgba(0,0,0,0.2); /* Subtle knob shadow */
        }

        /* Checked state */
        input:checked + .slider {
            background-color: #2563eb; /* Active color (same as button) */
        }

        /* Knob position when checked */
        input:checked + .slider:before {
            transform: translateX(24px); /* Move knob (width - knob_width - 2*padding) = 50-20-2*3 = 24 */
        }

        /* --- Toggle Switch Glow Effect --- */
        .switch:hover .slider, /* Glow on hover over the entire switch */
        .switch input:focus + .slider /* Glow when hidden input has focus */
        {
            box-shadow: 0 0 10px 3px rgba(37, 99, 235, 0.5); /* Glow effect (adjust color/size as needed) */
        }
        /* --- End Toggle Switch Glow Effect --- */

        .switch-label {
            color: #4a5568;
            font-size: 0.95em;
            cursor: pointer; /* Make text clickable too */
        }
        /* --- End Toggle Switch Styles --- */

        .submit-button {
            background-color: #2563eb; color: white; padding: 14px 30px; border: none; border-radius: 8px; font-size: 1.1em; font-weight: 600; cursor: pointer;
            transition: background-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
            opacity: 0.6; pointer-events: none;
        }
        .submit-button:not(:disabled) { opacity: 1; pointer-events: auto; }
        .submit-button:hover:not(:disabled) { background-color: #1d4ed8; box-shadow: 0 0 18px 5px rgba(37, 99, 235, 0.6); transform: translateY(-2px); }
        .submit-button:active:not(:disabled) { transform: translateY(0px); box-shadow: 0 2px 5px rgba(37, 99, 235, 0.4); }
        .flash-messages { list-style: none; padding: 0; margin-bottom: 20px; }
        .flash-messages li { padding: 12px 18px; margin-bottom: 12px; border-radius: 6px; font-weight: 500;}
        .flash-messages .error { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
        .flash-messages .success { background-color: #dcfce7; color: #14532d; border: 1px solid #bbf7d0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>次元聊天记录整理术</h1>
        <!-- Flash messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <ul class=flash-messages>
            {% for category, message in messages %}
              <li class="{{ category }}">{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}

        <p>将您的聊天记录 <code>.txt</code> 文件拖拽到下方区域，或点击区域选择文件。工具将自动移除图片和视频路径信息以便LLM分析您的聊天内容防止数据污染。不过您需要愉快地安装Flsak</p>

        <form action="/process" method="post" enctype="multipart/form-data" id="uploadForm">
            <!-- File Upload Area -->
            <div class="upload-area" id="drop-zone">
                <!-- Removed 'required' from input below -->
                <input type="file" name="inputFile" id="fileInput" accept=".txt">
                <p>将文件拖拽到这里</p>
                <span>或点击选择文件</span>
                <div id="file-info"></div>
            </div>

            <!-- Options Container with Toggle Switch -->
            <div class="options-container">
                 <label class="switch" for="removeTimestampToggle">
                    <input type="checkbox" id="removeTimestampToggle" name="remove_timestamp" value="yes" checked>
                    <span class="slider"></span>
                 </label>
                 <label class="switch-label" for="removeTimestampToggle">移除行首时间戳</label>
            </div>

            <!-- Submit Button -->
            <button type="submit" class="submit-button" id="submitBtn" disabled>清理并下载</button>
        </form>
    </div>

    <!-- JavaScript (保持不变 - relies on previous fix) -->
    <script>
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('file-info');
        const submitBtn = document.getElementById('submitBtn');
        const uploadForm = document.getElementById('uploadForm');

        dropZone.addEventListener('dragenter', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('dragover'); });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        dropZone.addEventListener('click', () => { fileInput.click(); });

        fileInput.addEventListener('change', (e) => {
            if (fileInput.files.length > 0) {
                 handleFile(fileInput.files[0]);
            } else {
                clearFileInfo();
            }
        });

        function handleFile(file) {
            if (file && file.name.toLowerCase().endsWith('.txt')) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files; // Ensure file is associated
                displayFileInfo(file);
            } else {
                displayFileError('错误：请上传有效的 .txt 文件。');
                fileInput.value = '';
            }
        }

        function displayFileInfo(file) {
             if (file) {
                 fileInfo.textContent = `已选文件: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
                 fileInfo.classList.remove('error');
                 submitBtn.disabled = false;
             } else {
                 clearFileInfo();
             }
        }

        function displayFileError(message) {
            fileInfo.textContent = message;
            fileInfo.classList.add('error');
            submitBtn.disabled = true;
        }

        function clearFileInfo() {
            fileInfo.textContent = '';
            fileInfo.classList.remove('error');
            submitBtn.disabled = true;
            fileInput.value = '';
        }

        // Allow clicking the text label to toggle the switch
        const switchLabel = document.querySelector('.switch-label');
        if (switchLabel) {
            switchLabel.addEventListener('click', function() {
                const checkbox = document.getElementById('removeTimestampToggle');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    // Optionally trigger change event if needed by other scripts, but not necessary here
                }
            });
        }

    </script>
</body>
</html>
"""

# --- Flask 路由 (保持不变) ---
@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process_text():
    # ... (backend logic remains the same) ...
    if 'inputFile' not in request.files:
        flash('未找到上传的文件部分', 'error')
        return redirect(url_for('index'))
    file = request.files['inputFile']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('index'))

    should_remove_timestamp = 'remove_timestamp' in request.form

    if file and file.filename.lower().endswith('.txt'):
        try:
            try:
                input_text = file.read().decode('utf-8')
            except UnicodeDecodeError:
                 file.seek(0)
                 try:
                     input_text = file.read().decode('gbk')
                     flash('文件以 GBK 编码读取。', 'success')
                 except UnicodeDecodeError:
                     flash('无法解码文件内容，请确保文件是 UTF-8 或 GBK 编码。', 'error')
                     return redirect(url_for('index'))

            cleaned_text = clean_text_content(input_text, remove_timestamp=should_remove_timestamp)

            output_filename = f"cleaned_{os.path.splitext(file.filename)[0]}.txt"
            return Response(
                cleaned_text,
                mimetype="text/plain",
                headers={"Content-Disposition": f"attachment;filename={output_filename}"}
            )
        except Exception as e:
            app.logger.error(f"处理文件时出错: {e}") # Log the error
            flash(f'处理文件时发生错误: {e}', 'error')
            return redirect(url_for('index'))
    else:
        flash('无效的文件类型，请上传 .txt 文件。', 'error')
        return redirect(url_for('index'))

# --- 启动 Flask 应用 (保持不变) ---
if __name__ == '__main__':
    print("服务已启动，请在浏览器访问 http://127.0.0.1:5000/")
    app.run(host='0.0.0.0', port=5000, debug=True)
