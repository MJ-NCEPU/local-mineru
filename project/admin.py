"""
管理后台API路由模块
处理统计数据显示、文件清理等管理功能
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from pathlib import Path
import os
import shutil
import threading
import time
import traceback
import csv
import io
from datetime import datetime, timedelta, date
from loguru import logger

from . import db_pool

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/files')
def files():
    """渲染已处理文件列表页面"""
    with open(str(Path(__file__).parent.parent / "web" / "files.html"), 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content


@admin_bp.route('/api/files/completed')
def get_completed_files():
    """获取已完成的文件列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        sort_by = request.args.get('sort_by', 'start_time')
        sort_order = request.args.get('sort_order', 'desc')
        
        valid_sort_fields = ['file_name', 'file_size', 'start_time', 'end_time']
        if sort_by not in valid_sort_fields:
            sort_by = 'start_time'
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        offset = (page - 1) * per_page
        
        count_query = """
        SELECT COUNT(*) as total
        FROM file_processing
        WHERE processing_status = 'completed'
        """
        count_result = db_pool.execute_query(count_query, fetch_all=True)
        total = count_result[0]['total'] if count_result else 0
        
        query = f"""
        SELECT file_name, file_size, start_time, end_time
        FROM file_processing
        WHERE processing_status = 'completed'
        ORDER BY {sort_by} {sort_order}
        LIMIT :per_page OFFSET :offset
        """
        
        results = db_pool.execute_query(query, params={'per_page': per_page, 'offset': offset}, fetch_all=True)
        
        files_list = []
        for row in results:
            file_size = row['file_size']
            if file_size is not None:
                if file_size >= 1024 * 1024 * 1024:
                    file_size_str = f"{file_size / (1024 * 1024 * 1024):.2f} GB"
                elif file_size >= 1024 * 1024:
                    file_size_str = f"{file_size / (1024 * 1024):.2f} MB"
                elif file_size >= 1024:
                    file_size_str = f"{file_size / 1024:.2f} KB"
                else:
                    file_size_str = f"{file_size} B"
            else:
                file_size_str = "未知"
            
            start_time = row['start_time']
            if start_time:
                if isinstance(start_time, datetime):
                    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    start_time_str = str(start_time)
            else:
                start_time_str = "未知"
            
            end_time = row['end_time']
            if end_time:
                if isinstance(end_time, datetime):
                    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    end_time_str = str(end_time)
            else:
                end_time_str = "未知"
            
            files_list.append({
                'file_name': row['file_name'],
                'file_size': file_size_str,
                'start_time': start_time_str,
                'end_time': end_time_str
            })
        
        return jsonify({
            'files': files_list,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"获取已完成文件列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/pdf2word/admin')
def admin():
    """渲染管理后台首页"""
    with open(str(Path(__file__).parent.parent / "web" / "admin.html"), 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content


@admin_bp.route('/api/stats/overview')
def get_stats_overview():
    """获取统计数据概览"""
    try:
        query = """
        SELECT COUNT(*) as total_users FROM (
            SELECT DISTINCT ip_address, user_agent 
            FROM user_visits
        ) as unique_users
        """
        result = db_pool.execute_query(query, fetch_all=True)
        total_users = result[0]['total_users'] if result else 0
        
        query = "SELECT COUNT(*) as total_visits FROM user_visits"
        result = db_pool.execute_query(query, fetch_all=True)
        total_visits = result[0]['total_visits'] if result else 0
        
        query = """
        SELECT COUNT(*) as active_users FROM (
            SELECT DISTINCT ip_address, user_agent
            FROM active_sessions
            WHERE last_activity >= :last_activity
        ) as unique_users
        """
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        result = db_pool.execute_query(query, params={'last_activity': five_minutes_ago}, fetch_all=True)
        active_users = result[0]['active_users'] if result else 0
        
        query = "SELECT COUNT(*) as total_files FROM file_processing WHERE processing_status = 'completed'"
        result = db_pool.execute_query(query, fetch_all=True)
        total_files = result[0]['total_files'] if result else 0
        
        query = "SELECT COUNT(*) as processing_files FROM file_processing WHERE processing_status = 'processing'"
        result = db_pool.execute_query(query, fetch_all=True)
        processing_files = result[0]['processing_files'] if result else 0
        
        return jsonify({
            'total_users': total_users,
            'total_visits': total_visits,
            'active_users': active_users,
            'total_files': total_files,
            'processing_files': processing_files
        })
    except Exception as e:
        logger.error(f"获取统计数据概览失败: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/stats/visits')
def get_visits_stats():
    """获取访问量统计"""
    try:
        period = request.args.get('period', 'week')
        
        if period == 'week':
            start_date = datetime.now() - timedelta(days=7)
        elif period == 'month':
            start_date = datetime.now() - timedelta(days=30)
        elif period == 'quarter':
            start_date = datetime.now() - timedelta(days=90)
        elif period == 'half_year':
            start_date = datetime.now() - timedelta(days=180)
        else:
            return jsonify({'error': '无效的时间周期'}), 400
        
        if period == 'half_year':
            query = """
            SELECT MAX(visit_time) as visit_time, COUNT(*) as visit_count
            FROM user_visits
            WHERE visit_time >= :start_date
            GROUP BY DATE_FORMAT(visit_time, '%%Y-%%m')
            ORDER BY visit_time
            """
        else:
            query = """
            SELECT MAX(visit_time) as visit_time, COUNT(*) as visit_count
            FROM user_visits
            WHERE visit_time >= :start_date
            GROUP BY DATE(visit_time)
            ORDER BY visit_time
            """
        
        result = db_pool.execute_query(query, params={'start_date': start_date}, fetch_all=True)
        
        dates = []
        for row in result:
            visit_time = row['visit_time']
            if isinstance(visit_time, (datetime, date)):
                if period == 'half_year':
                    formatted_date = visit_time.strftime('%Y-%m')
                else:
                    formatted_date = visit_time.strftime('%Y-%m-%d')
                dates.append(formatted_date)
            else:
                dates.append(str(visit_time))
        
        counts = [row['visit_count'] for row in result]
        
        return jsonify({
            'dates': dates,
            'counts': counts
        })
    except Exception as e:
        logger.error(f"获取访问量统计失败: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/stats/files')
def get_files_stats():
    """获取文件处理统计"""
    try:
        period = request.args.get('period', 'week')
        
        if period == 'week':
            start_date = datetime.now() - timedelta(days=7)
        elif period == 'month':
            start_date = datetime.now() - timedelta(days=30)
        elif period == 'quarter':
            start_date = datetime.now() - timedelta(days=90)
        elif period == 'half_year':
            start_date = datetime.now() - timedelta(days=180)
        else:
            return jsonify({'error': '无效的时间周期'}), 400
        
        if period == 'half_year':
            query = """
            SELECT MAX(start_time) as start_time, COUNT(*) as file_count
            FROM file_processing
            WHERE start_time >= :start_date AND processing_status = 'completed'
            GROUP BY DATE_FORMAT(start_time, '%%Y-%%m')
            ORDER BY start_time
            """
        else:
            query = """
            SELECT MAX(start_time) as start_time, COUNT(*) as file_count
            FROM file_processing
            WHERE start_time >= :start_date AND processing_status = 'completed'
            GROUP BY DATE(start_time)
            ORDER BY start_time
            """
        
        result = db_pool.execute_query(query, params={'start_date': start_date}, fetch_all=True)
        
        dates = []
        for row in result:
            start_time = row['start_time']
            if isinstance(start_time, (datetime, date)):
                if period == 'half_year':
                    formatted_date = start_time.strftime('%Y-%m')
                else:
                    formatted_date = start_time.strftime('%Y-%m-%d')
                dates.append(formatted_date)
            else:
                dates.append(str(start_time))
        
        counts = [row['file_count'] for row in result]
        
        return jsonify({
            'dates': dates,
            'counts': counts
        })
    except Exception as e:
        logger.error(f"获取文件处理统计失败: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/stats/download')
def download_stats():
    """下载统计数据为CSV文件"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['统计类型', '数据项', '数值'])
        
        query = """
        SELECT COUNT(*) as total_users FROM (
            SELECT DISTINCT ip_address, user_agent 
            FROM user_visits
        ) as unique_users
        """
        result = db_pool.execute_query(query, fetch_all=True)
        total_users = result[0]['total_users'] if result else 0
        writer.writerow(['概览数据', '总访问用户数', total_users])
        
        query = "SELECT COUNT(*) as total_visits FROM user_visits"
        result = db_pool.execute_query(query, fetch_all=True)
        total_visits = result[0]['total_visits'] if result else 0
        writer.writerow(['概览数据', '用户总访问量', total_visits])
        
        query = "SELECT COUNT(*) as total_files FROM file_processing WHERE processing_status = 'completed'"
        result = db_pool.execute_query(query, fetch_all=True)
        total_files = result[0]['total_files'] if result else 0
        writer.writerow(['概览数据', '已处理文件数', total_files])
        
        writer.writerow([])
        writer.writerow(['近半年数据趋势'])
        writer.writerow(['日期', '用户访问量', '文件处理量'])
        
        start_date = datetime.now() - timedelta(days=180)
        
        query = """
        SELECT MAX(visit_time) as visit_time, COUNT(*) as visit_count
        FROM user_visits
        WHERE visit_time >= :start_date
        GROUP BY DATE(visit_time)
        ORDER BY visit_time
        """
        visits_result = db_pool.execute_query(query, params={'start_date': start_date}, fetch_all=True)
        
        visits_dict = {}
        for row in visits_result:
            visit_time = row['visit_time']
            if isinstance(visit_time, (datetime, date)):
                formatted_date = visit_time.strftime('%Y-%m-%d')
            else:
                formatted_date = str(visit_time)
            visits_dict[formatted_date] = row['visit_count']
        
        query = """
        SELECT MAX(start_time) as start_time, COUNT(*) as file_count
        FROM file_processing
        WHERE start_time >= :start_date AND processing_status = 'completed'
        GROUP BY DATE(start_time)
        ORDER BY start_time
        """
        files_result = db_pool.execute_query(query, params={'start_date': start_date}, fetch_all=True)
        
        files_dict = {}
        for row in files_result:
            start_time = row['start_time']
            if isinstance(start_time, (datetime, date)):
                formatted_date = start_time.strftime('%Y-%m-%d')
            else:
                formatted_date = str(start_time)
            files_dict[formatted_date] = row['file_count']
        
        for date_str in sorted(visits_dict.keys()):
            visit_count = visits_dict[date_str]
            file_count = files_dict.get(date_str, 0)
            writer.writerow([date_str, visit_count, file_count])
        
        output.seek(0)
        
        csv_bytes = output.getvalue().encode('utf-8-sig')
        
        csv_io = io.BytesIO(csv_bytes)
        
        filename = f'统计数据_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            csv_io,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"下载统计数据失败: {e}")
        return jsonify({'error': str(e)}), 500


def cleanup_old_files_internal():
    """内部清理文件函数，供定时任务调用"""
    try:
        one_hour_ago = datetime.now() - timedelta(hours=2)
        batch_size = 100
        
        query = """
        SELECT DISTINCT output_path, task_id
        FROM file_processing
        WHERE start_time < :one_hour_ago
        AND processing_status = 'completed'
        LIMIT :batch_size
        """
        results = db_pool.execute_query(query, params={
            'one_hour_ago': one_hour_ago,
            'batch_size': batch_size
        }, fetch_all=True)
        
        if not results:
            return
            
        cleaned_count = 0
        for row in results:
            output_path = row['output_path']
            task_id = row['task_id']
            
            if not output_path or not isinstance(output_path, str):
                logger.warning(f"无效的输出路径: {output_path}, task_id: {task_id}")
                continue
            
            session_query = """
            SELECT created_at
            FROM task_sessions
            WHERE task_id = :task_id
            """
            session_result = db_pool.execute_query(session_query, params={'task_id': task_id})
            
            if session_result:
                session_created_at = session_result.get('created_at')
                if session_created_at and datetime.now() - session_created_at > timedelta(hours=1):
                    try:
                        output_path_str = str(output_path)
                        if os.path.exists(output_path_str):
                            shutil.rmtree(output_path_str)
                            logger.info(f"已清理过期任务文件: {output_path_str}")
                            cleaned_count += 1
                    except Exception as e:
                        logger.error(f"清理过期文件失败: {output_path_str}, error: {e}")
        
        if cleaned_count > 0:
            logger.info(f'定时清理: 清理了 {cleaned_count} 个过期任务目录')
    except Exception as e:
        logger.error(f"定时清理文件失败: {e}\n{traceback.format_exc()}")


def cleanup_old_sessions_internal():
    """内部清理会话函数，供定时任务调用"""
    try:
        thirty_minutes_ago = datetime.now() - timedelta(minutes=120)
        query = """
        DELETE FROM active_sessions 
        WHERE last_activity < :last_activity
        """
        deleted_count = db_pool.execute_update(query, {'last_activity': thirty_minutes_ago})
        if deleted_count > 0:
            logger.info(f'定时清理: 删除了 {deleted_count} 个过期会话')
    except Exception as e:
        logger.error(f"定时清理会话失败: {e}")


def run_cleanup_task():
    """运行清理任务的循环函数"""
    while True:
        try:
            # 暂时关闭定时文件清理任务
            # cleanup_old_files_internal()
            cleanup_old_sessions_internal()
            time.sleep(600*6)
        except Exception as e:
            logger.error(f"定时清理任务出错: {e}")
            time.sleep(60)


def start_cleanup_task():
    """启动定时清理任务"""
    cleanup_thread = threading.Thread(target=run_cleanup_task, daemon=True)
    cleanup_thread.start()
    return cleanup_thread
