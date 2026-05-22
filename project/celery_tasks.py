"""
Celery异步任务模块
定义PDF文件处理等后台任务
"""
from .celery_config import celery_app
from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from . import db_pool
from . import mineru_api

# 添加配置目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
import log_config

@celery_app.task(bind=True, name='project.celery_tasks.process_pdf_files')
def process_pdf_files(self, pdf_files_info, output_path, ip_address):
    """
    异步处理PDF-PPTX-XLSX-DOCX-PNG-JPG-JPEG文件
    
    Args:
        pdf_files_info: 文件信息列表 [(file_path, file_name), ...]
        output_path: 输出路径
        ip_address: 用户IP地址
    
    Returns:
        dict: 处理结果
    """
    task_id = self.request.id
    logger.info(f"开始异步处理文件，任务ID: {task_id}, 文件数量: {len(pdf_files_info)}")
    
    processing_records = []
    file_paths = []
    original_files_to_clean = []
    
    try:
        temp_input_dir = tempfile.mkdtemp(prefix="pdf_converter_temp_")
        logger.info(f"创建临时目录: {temp_input_dir}")
        
        for file_path, file_name in pdf_files_info:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                continue
            
            original_files_to_clean.append(file_path)
            
            file_stem = Path(file_name).stem
            file_ext = Path(file_name).suffix.lower()
            safe_filename = file_stem.replace('/', '_').replace('\\', '_').replace('\0', '_')
            
            new_file_path = os.path.join(temp_input_dir, f"{safe_filename}{file_ext}")
            shutil.copy2(file_path, new_file_path)
            file_paths.append(new_file_path)
            
            file_size = os.path.getsize(new_file_path)
            query = """
            INSERT INTO file_processing (task_id, ip_address, file_name, file_size, processing_status, start_time)
            VALUES (:task_id, :ip_address, :file_name, :file_size, 'processing', :start_time)
            """
            record_id = db_pool.execute_update(query, params={'task_id': task_id, 'ip_address': ip_address, 'file_name': file_name, 'file_size': file_size, 'start_time': datetime.now()})
            processing_records.append((record_id, file_name))
            logger.info(f"记录文件处理开始，ID: {record_id}, 文件名: {file_name}")
        
        if not file_paths:
            logger.error("没有有效的文件可处理")
            return {
                'success': False,
                'success_count': 0,
                'failed_count': len(pdf_files_info),
                'error_messages': ['没有有效的文件可处理']
            }
        
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        process_result = mineru_api.call_mineru_api(file_paths, output_path)
        logger.info(f"文件处理结果: {process_result}")
        
        if process_result.get('success', False):
            success_count = process_result.get('success_count', 0)
            for i in range(min(success_count, len(processing_records))):
                record_id, file_name = processing_records[i]
                try:
                    query = """
                    UPDATE file_processing 
                    SET processing_status = 'completed', end_time = :end_time, output_path = :output_path
                    WHERE id = :id
                    """
                    result = db_pool.execute_update(query, params={'end_time': datetime.now(), 'output_path': output_path, 'id': record_id})
                    logger.info(f"更新文件处理状态为完成，ID: {record_id}, 文件名: {file_name}, 影响行数: {result}")
                except Exception as e:
                    logger.error(f"更新文件处理状态失败: {e}")
            
            failed_count = process_result.get('failed_count', 0)
            start_index = success_count
            error_messages = process_result.get('error_messages', [])
            for i in range(start_index, min(start_index + failed_count, len(processing_records))):
                record_id, file_name = processing_records[i]
                error_msg = error_messages[i - start_index] if i - start_index < len(error_messages) else "未知错误"
                try:
                    query = """
                    UPDATE file_processing 
                    SET processing_status = 'failed', end_time = :end_time, error_message = :error_message
                    WHERE id = :id
                    """
                    result = db_pool.execute_update(query, params={'end_time': datetime.now(), 'error_message': error_msg, 'id': record_id})
                    logger.info(f"更新文件处理状态为失败，ID: {record_id}, 文件名: {file_name}, 错误: {error_msg}, 影响行数: {result}")
                except Exception as e:
                    logger.error(f"更新文件处理失败状态失败: {e}")
        else:
            error_messages = process_result.get('error_messages', ['处理失败'])
            for i, (record_id, file_name) in enumerate(processing_records):
                error_msg = error_messages[i] if i < len(error_messages) else error_messages[0]
                try:
                    query = """
                    UPDATE file_processing 
                    SET processing_status = 'failed', end_time = :end_time, error_message = :error_message
                    WHERE id = :id
                    """
                    result = db_pool.execute_update(query, params={'end_time': datetime.now(), 'error_message': error_msg, 'id': record_id})
                    logger.info(f"更新文件处理状态为失败，ID: {record_id}, 文件名: {file_name}, 错误: {error_msg}, 影响行数: {result}")
                except Exception as e:
                    logger.error(f"更新文件处理失败状态失败: {e}")
        
        logger.info(f"任务 {task_id} 处理完成")
        return {
            'success': process_result.get('success', False),
            'success_count': process_result.get('success_count', 0),
            'failed_count': process_result.get('failed_count', len(pdf_files_info)),
            'error_messages': process_result.get('error_messages', [])
        }
    
    except Exception as e:
        error_msg = f"处理过程中出现异常: {str(e)}"
        logger.error(error_msg)
        
        for record_id, file_name in processing_records:
            try:
                query = """
                UPDATE file_processing 
                SET processing_status = 'failed', end_time = :end_time, error_message = :error_message
                WHERE id = :id
                """
                result = db_pool.execute_update(query, params={'end_time': datetime.now(), 'error_message': error_msg, 'id': record_id})
                logger.info(f"更新文件处理状态为失败，ID: {record_id}, 文件名: {file_name}, 错误: {error_msg}, 影响行数: {result}")
            except Exception as update_error:
                logger.error(f"更新文件处理失败状态失败: {update_error}")
        
        return {
            'success': False,
            'success_count': 0,
            'failed_count': len(pdf_files_info),
            'error_messages': [error_msg]
        }
    finally:
        try:
            if 'temp_input_dir' in locals() and os.path.exists(temp_input_dir):
                shutil.rmtree(temp_input_dir)
                logger.info(f"临时目录已清理: {temp_input_dir}")
        except Exception as e:
            logger.warning(f"临时目录清理失败: {e}")
        
        # 清理原始上传的临时文件
        for original_file in original_files_to_clean:
            try:
                if os.path.exists(original_file):
                    os.remove(original_file)
                    logger.info(f"已清理原始上传文件: {original_file}")
            except Exception as e:
                logger.warning(f"原始上传文件清理失败: {e}")

@celery_app.task(bind=True, name='project.celery_tasks.check_task_status')
def check_task_status(self, task_id):
    """
    检查任务状态
    
    Args:
        task_id: Celery任务ID
    
    Returns:
        dict: 任务状态信息
    """
    try:
        task = celery_app.AsyncResult(task_id)
        
        query = """
        SELECT id, file_name, processing_status, start_time, end_time, error_message, output_path
        FROM file_processing
        WHERE task_id = :task_id
        ORDER BY start_time
        """
        results = db_pool.execute_query(query, {'task_id': task_id}, fetch_all=True)
        
        return {
            'task_id': task_id,
            'task_status': task.status,
            'task_result': task.result if task.ready() else None,
            'files': results
        }
    except Exception as e:
        logger.error(f"检查任务状态失败: {e}")
        return {
            'task_id': task_id,
            'error': str(e)
        }
