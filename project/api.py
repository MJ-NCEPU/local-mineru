"""
前端API路由模块
处理PDF转换请求、任务状态管理及文件下载
"""
from flask import Blueprint, request, jsonify, send_file, send_from_directory, current_app
from pathlib import Path
import os
import tempfile
import uuid
import threading
import zipfile
import shutil
import time
from datetime import datetime, timedelta
from loguru import logger

from . import celery_tasks
from . import db_pool

api_bp = Blueprint('api', __name__, static_folder='../web')


@api_bp.route('/source/<path:filename>')
def serve_static(filename):
    """提供静态文件服务（如图标、图片等）"""
    web_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
    return send_from_directory(os.path.join(web_folder, 'source'), filename)


def get_client_ip():
    """获取客户端真实IP地址"""
    ip = None
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        logger.info(f"从X-Forwarded-For获取IP: {ip}")
    elif request.headers.get('X-Real-IP'):
        ip = request.headers['X-Real-IP']
        logger.info(f"从X-Real-IP获取IP: {ip}")
    else:
        ip = request.remote_addr
        logger.info(f"从request.remote_addr获取IP: {ip}")
    
    logger.info(f"所有请求头: {dict(request.headers)}")
    return ip


@api_bp.route('/')
def index():
    """渲染前端首页"""
    try:
        ip_address = get_client_ip()
        user_agent = request.headers.get('User-Agent', '')[:500]
        session_id = request.cookies.get('session_id', str(uuid.uuid4()))
        
        query = """
        INSERT INTO user_visits (ip_address, user_agent, session_id)
        VALUES (:ip_address, :user_agent, :session_id)
        """
        db_pool.execute_update(query, {'ip_address': ip_address, 'user_agent': user_agent, 'session_id': session_id})
        
        query = """
        INSERT INTO active_sessions (ip_address, user_agent, session_id, last_activity)
        VALUES (:ip_address, :user_agent, :session_id, :last_activity)
        ON DUPLICATE KEY UPDATE last_activity = :last_activity_dup
        """
        current_time = datetime.now()
        db_pool.execute_update(query, {'ip_address': ip_address, 'user_agent': user_agent, 'session_id': session_id, 'last_activity': current_time, 'last_activity_dup': current_time})
        
        logger.info(f"记录用户访问: {ip_address}, session: {session_id}")
    except Exception as e:
        logger.error(f"记录用户访问失败: {e}")
    
    with open(str(Path(__file__).parent.parent / "web" / "index.html"), 'r', encoding='utf-8') as f:
        html_content = f.read()
    response = current_app.make_response(html_content)
    return response


@api_bp.route('/convert', methods=['POST'])
def convert_pdf_to_md():
    """处理PDF转换请求"""
    pdf_files_info = []
    saved_files = []
    
    try:
        input_type = request.form.get('inputType')
        ip_address = get_client_ip()
        user_agent = request.headers.get('User-Agent', '')[:500]
        
        base_output_path = Path(__file__).parent.parent / "output"
        base_output_path.mkdir(parents=True, exist_ok=True)
        
        task_output_path = base_output_path / f"task_{uuid.uuid4()}"
        task_output_path.mkdir(exist_ok=True)
        output_path = str(task_output_path)
        
        if input_type == 'files' or input_type == 'folder':
            uploaded_files = request.files.getlist('files')
            
            if not uploaded_files:
                return jsonify({'error': '没有上传任何文件'}), 400
            
            for uploaded_file in uploaded_files:
                filename_lower = uploaded_file.filename.lower()
                if not (filename_lower.endswith('.pdf') or 
                        filename_lower.endswith('.png') or 
                        filename_lower.endswith('.jpg') or 
                        filename_lower.endswith('.jpeg') or
                        filename_lower.endswith('.pptx') or
                        filename_lower.endswith('.xlsx') or
                        filename_lower.endswith('.docx')):
                    return jsonify({'error': f'文件 {uploaded_file.filename} 不是支持的文件类型（仅支持PDF-PPTX-XLSX-DOCX-PNG-JPG-JPEG文件）'}), 400
                
                logger.info(f"原始上传文件名: {uploaded_file.filename}")
                
                original_filename = uploaded_file.filename
                file_name_only = os.path.basename(original_filename)
                file_stem = os.path.splitext(file_name_only)[0]
                logger.info(f"提取的原始文件名(不含扩展名): {file_stem}")
                
                safe_filename = file_name_only.replace('/', '_').replace('\\', '_').replace('\0', '_')
                logger.info(f"安全处理后的文件名: {safe_filename}")
                
                temp_file_path = os.path.join(tempfile.gettempdir(), f"flask_upload_{uuid.uuid4()}_{safe_filename}")
                uploaded_file.save(temp_file_path)
                logger.info(f"保存到临时路径: {temp_file_path}")
                
                pdf_files_info.append((temp_file_path, file_name_only))
                saved_files.append(temp_file_path)
        
        else:
            return jsonify({'error': '无效的输入类型'}), 400
        
        if not pdf_files_info:
            return jsonify({'error': '没有有效的PDF-PPTX-XLSX-DOCX-PNG-JPG-JPEG文件可处理'}), 400
        
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        task = celery_tasks.process_pdf_files.delay(pdf_files_info, output_path, ip_address)
        
        logger.info(f"异步任务已提交，任务ID: {task.id}")
        
        session_query = """
        INSERT INTO task_sessions (task_id, ip_address, user_agent, created_at)
        VALUES (:task_id, :ip_address, :user_agent, :created_at)
        """
        db_pool.execute_update(session_query, params={
            'task_id': task.id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.now()
        })
        
        return jsonify({
            'message': '文件处理任务已提交，正在后台处理中',
            'task_id': task.id,
            'file_count': len(pdf_files_info),
            'output_path': output_path
        })
    
    except Exception as e:
        logger.error(f"提交文件处理任务失败: {e}")
        for temp_file in saved_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"已清理临时文件: {temp_file}")
            except Exception as cleanup_error:
                logger.error(f"清理临时文件失败: {cleanup_error}")
        return jsonify({'error': f'提交任务失败: {str(e)}'}), 500


@api_bp.route('/task_status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    try:
        task = celery_tasks.process_pdf_files.AsyncResult(task_id)
        
        query = """
        SELECT id, file_name, processing_status, start_time, end_time, error_message, output_path
        FROM file_processing
        WHERE task_id = :task_id
        ORDER BY start_time
        """
        results = db_pool.execute_query(query, params={'task_id': task_id}, fetch_all=True)
        
        return jsonify({
            'task_id': task_id,
            'task_status': task.status,
            'task_result': task.result if task.ready() else None,
            'files': results
        })
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return jsonify({
            'task_id': task_id,
            'error': str(e)
        }), 500


@api_bp.route('/download_all/<task_id>')
def download_all_files(task_id):
    """下载整个任务的转换结果（打包成zip）"""
    try:
        ip_address = get_client_ip()
        session_query = """
        SELECT ip_address, created_at FROM task_sessions
        WHERE task_id = :task_id
        """
        session_result = db_pool.execute_query(
            session_query, 
            params={'task_id': task_id},
            fetch_all=True
        )
        
        if not session_result:
            return jsonify({'error': '无权访问此任务的文件'}), 403
            
        if session_result[0]['ip_address'] != ip_address:
            return jsonify({'error': '无权访问此任务的文件'}), 403
            
        created_at = session_result[0]['created_at']
        if datetime.now() - created_at > timedelta(hours=1):
            return jsonify({'error': '任务已过期，无法下载'}), 403
        
        query = """
        SELECT output_path, processing_status
        FROM file_processing
        WHERE task_id = :task_id
        LIMIT 1
        """
        result = db_pool.execute_query(query, params={'task_id': task_id}, fetch_all=True)
        
        if not result:
            return jsonify({'error': '任务不存在'}), 404
            
        result = result[0]
        
        if result['processing_status'] != 'completed':
            return jsonify({'error': '任务尚未完成，无法下载'}), 400
        
        output_path = result['output_path']
        output_path_obj = Path(output_path)
        
        if not output_path_obj.exists():
            return jsonify({'error': '输出目录不存在'}), 404
        
        temp_zip_path = tempfile.mktemp(suffix=f'_converted_files_{task_id}.zip')
        
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_path_obj):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        arcname = file_path.relative_to(output_path_obj.parent)
                    except ValueError:
                        arcname = file_path.name
                    zipf.write(file_path, arcname)
        
        def delayed_directory_removal():
            time.sleep(3000)
            try:
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
                    logger.info(f"下载后已删除临时ZIP文件: {temp_zip_path}")
                # if output_path_obj.exists():
                #     shutil.rmtree(output_path_obj)
                #     logger.info(f"下载后已删除任务目录: {output_path_obj}")
            except Exception as e:
                logger.error(f"下载后删除目录失败: {e}")
        
        removal_thread = threading.Thread(target=delayed_directory_removal, daemon=True)
        removal_thread.start()
        
        return send_file(
            temp_zip_path,
            as_attachment=True,
            download_name=f'转换后markdown文件_{task_id}.zip'
        )
        
    except Exception as e:
        logger.error(f"下载所有文件失败: {e}")
        return jsonify({'error': f'下载失败: {str(e)}'}), 500
