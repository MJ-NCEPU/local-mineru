import requests
import os
import sys
import json
import base64
import tempfile
import shutil
import atexit
import re
import random
from pathlib import Path
import argparse
from loguru import logger
from . import md2docx

# 导入日志配置
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
import log_config

API_URLS = ["http://127.0.0.1:8001/file_parse", "http://127.0.0.1:8002/file_parse", "http://127.0.0.1:8003/file_parse"]

def get_random_api_url():
    selected_url = random.choice(API_URLS)
    return selected_url

parse_params = {
    "output_dir": tempfile.gettempdir(),
    "lang_list": ["ch"],
    "backend": "vlm-auto-engine",
    "parse_method": "auto",
    "formula_enable": True,
    "table_enable": True,
    "server_url": "",
    "return_md": True,
    "return_middle_json": False,
    "return_model_output": False,
    "return_content_list": False,
    "return_images": True,
    "response_format_zip": False,
    "start_page_id": 0,
    "end_page_id": 99999
}

def call_mineru_api(PDF_FILE_PATHS, RESULT_SAVE_DIR):
    success_count = 0
    failed_count = 0
    error_messages = []
    
    # 创建一个专用的临时目录用于本次转换
    # temp_output_dir = tempfile.mkdtemp(prefix="mineru_temp_")
    # original_output_dir = parse_params["output_dir"]
    
    # 临时修改全局参数
    # parse_params["output_dir"] = temp_output_dir
    
    logger.info(f"输入文件:{PDF_FILE_PATHS}")
    logger.info(f"输出目录:{RESULT_SAVE_DIR}")

    file_handles = []
    try:
        files = []
        valid_file_names = []
        for file_path in PDF_FILE_PATHS:
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在：{file_path}，跳过该文件")
                failed_count += 1
                error_messages.append(f"文件不存在：{file_path}")
                continue
            
            f = open(file_path, "rb")
            file_handles.append(f)
            
            file_name = os.path.basename(file_path)
            file_stem = os.path.splitext(file_name)[0]
            
            logger.info(f"处理文件路径: {file_path}")
            logger.info(f"提取的文件名: {file_name}")
            logger.info(f"提取的文件名(无扩展名): {file_stem}")
            
            # 处理中文文件名 - 确保能正确处理中文字符
            try:
                file_stem = file_stem.encode('utf-8').decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                # 如果编码有问题，使用原始名称
                pass
            
            # 确保文件名作为目录名时是有效的
            # 替换可能引起问题的字符
            file_stem = re.sub(r'[<>:"/\\|?*]', '_', file_stem)
            
            logger.info(f"处理后的文件名: {file_stem}")
            valid_file_names.append(file_stem)
            
            files.append(("files", (file_name, f, "application/pdf")))

        if not files:
            logger.warning("没有有效的PDF-PPTX-XLSX-DOCX-PNG-JPG-JPEG文件可上传")
            return {
                'success': False,
                'success_count': 0,
                'failed_count': len(PDF_FILE_PATHS),
                'error_messages': error_messages
            }

        logger.info("开始调用mineru API解析PDF...")
        selected_api_url = get_random_api_url()
        response = requests.post(
            selected_api_url,
            files=files,
            data=parse_params,
            timeout=2400
        )

        if response.status_code == 200:
            logger.info("API调用成功，开始处理解析结果...")
            result = response.json()

            if "results" not in result:
                error_msg = f"响应结果缺少核心字段'results'，完整响应：{result}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'success_count': 0,
                    'failed_count': len(valid_file_names),
                    'error_messages': [error_msg]
                }

            results_dict = result["results"]
            logger.info(f"API返回的键列表: {list(results_dict.keys())}")

            # 为每个期望的文件名寻找对应的API响应
            for expected_file_stem in valid_file_names:
                # 先尝试直接匹配
                if expected_file_stem in results_dict:
                    file_result = results_dict[expected_file_stem]
                    actual_file_stem = expected_file_stem
                    logger.info(f"找到直接匹配的文件：{actual_file_stem}")
                else:
                    # 如果直接匹配失败，尝试从API返回的键中找到最匹配的一个
                    matched_key = None
                    for api_key in results_dict.keys():
                        # 检查是否可能是相同文件的不同表示
                        if api_key == expected_file_stem or api_key.startswith(expected_file_stem) or expected_file_stem.startswith(api_key):
                            matched_key = api_key
                            break
                    
                    if matched_key:
                        file_result = results_dict[matched_key]
                        actual_file_stem = expected_file_stem  # 使用我们期望的文件名
                        logger.info(f"找到相似匹配的文件：{expected_file_stem} <- {matched_key}")
                    else:
                        # 如果完全找不到匹配项，尝试使用第一个可用的键（作为备选方案）
                        if results_dict:
                            first_key = next(iter(results_dict))
                            file_result = results_dict[first_key]
                            actual_file_stem = expected_file_stem  # 使用我们期望的文件名
                            logger.warning(f"未找到匹配的文件，使用第一个可用结果：{expected_file_stem} <- {first_key}")
                        else:
                            logger.warning(f"未找到文件'{expected_file_stem}'的解析结果，跳过")
                            failed_count += 1
                            error_messages.append(f"未找到文件'{expected_file_stem}'的解析结果")
                            continue

                logger.info(f"处理文件：{actual_file_stem}.pdf")

                MID_RESULT_SAVE_DIR = os.path.join(RESULT_SAVE_DIR, actual_file_stem)
                Path(MID_RESULT_SAVE_DIR).mkdir(parents=True, exist_ok=True)

                md_content = file_result.get("md_content", "")
                if md_content:
                    md_file_name = f"{actual_file_stem}.md"
                    # 可以等markdown转word后删除该md文件
                    md_save_path = os.path.join(MID_RESULT_SAVE_DIR, md_file_name)
                    with open(md_save_path, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    logger.success(f"Markdown文件已保存：{md_save_path}")
                else:
                    logger.warning(f"文件'{actual_file_stem}'无Markdown内容")

                images_dict = file_result.get("images", {})
                if images_dict and isinstance(images_dict, dict):
                    # 可以等markdown转word后删除该文件夹
                    img_save_dir = os.path.join(MID_RESULT_SAVE_DIR, "images")
                    Path(img_save_dir).mkdir(parents=True, exist_ok=True)

                    for img_name, img_base64_str in images_dict.items():
                        try:
                            if "," in img_base64_str:
                                img_base64 = img_base64_str.split(",")[1]
                            else:
                                img_base64 = img_base64_str

                            img_data = base64.b64decode(img_base64)
                            img_save_path = os.path.join(img_save_dir, img_name)
                            with open(img_save_path, "wb") as f:
                                f.write(img_data)
                            logger.success(f"图片已保存：{img_save_path}")
                        except base64.binascii.Error as e:
                            logger.error(f"图片'{img_name}'base64解码失败：{e}")
                        except Exception as e:
                            logger.error(f"保存图片'{img_name}'失败：{e}")
                else:
                    logger.warning(f"文件'{actual_file_stem}'无图片内容或图片格式错误")

                try:
                    # 使用相对于当前文件的路径
                    template_path = Path(__file__).parent / "template" / "font_template.docx"
                    md2docx.markdown_to_docx(md_file_path=Path(md_save_path),
                                             template_path=template_path)
                    success_count += 1
                    #  TODO:删除md文件和图片文件，仅保留word文件
                    # if os.path.exists(md_save_path):
                    #     os.remove(md_save_path)
                    # if 'img_save_dir' in locals() and os.path.exists(img_save_dir):
                    #     shutil.rmtree(img_save_dir)
                        
                except Exception as e:
                    logger.error(f"转换DOCX失败：{e}")
                    failed_count += 1
                    error_messages.append(f"文件'{actual_file_stem}'转换DOCX失败：{str(e)}")

        else:
            error_msg = f"API调用失败，状态码：{response.status_code}，错误信息：{response.text}"
            logger.error(error_msg)
            return {
                'success': False,
                'success_count': 0,
                'failed_count': len(valid_file_names),
                'error_messages': [error_msg]
            }

    except FileNotFoundError as e:
        error_msg = f"文件未找到：{e}"
        logger.error(error_msg)
        error_messages.append(error_msg)
        failed_count += len(PDF_FILE_PATHS)
    except requests.RequestException as e:
        error_msg = f"网络请求异常：{e}"
        logger.error(error_msg)
        error_messages.append(error_msg)
        failed_count += len(PDF_FILE_PATHS)
    except json.JSONDecodeError as e:
        error_msg = f"响应JSON解析失败：{e}"
        logger.error(error_msg)
        error_messages.append(error_msg)
        failed_count += len(PDF_FILE_PATHS)
    except Exception as e:
        error_msg = f"未知错误：{e}"
        logger.error(error_msg)
        error_messages.append(error_msg)
        failed_count += len(PDF_FILE_PATHS)
    finally:
        # 恢复原始参数值
        # parse_params["output_dir"] = original_output_dir
        
        # 清理临时目录
        # try:
        #     import shutil
        #     shutil.rmtree(temp_output_dir)
        #     logger.info(f"临时目录已清理：{temp_output_dir}")
        # except Exception as e:
        #     logger.warning(f"临时目录清理失败：{e}")
        
        for f in file_handles:
            try:
                f.close()
            except:
                pass
    
    # 返回处理结果
    return {
        'success': success_count > 0,
        'success_count': success_count,
        'failed_count': failed_count,
        'error_messages': error_messages
    }

def get_all_pdfs(root_dir):
    pdf_list = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(dirpath, file)
                pdf_list.append(full_path)
    return pdf_list

def resolve_input_paths(inputs):
    pdf_files = []
    base_dirs = set()
    
    for input_path in inputs:
        input_path = Path(input_path).resolve()
        
        if input_path.is_file() and input_path.suffix.lower() == '.pdf':
            pdf_files.append(str(input_path))
            base_dirs.add(str(input_path.parent))
        elif input_path.is_dir():
            dir_pdfs = get_all_pdfs(str(input_path))
            pdf_files.extend(dir_pdfs)
            base_dirs.add(str(input_path))
        else:
            logger.warning(f"输入无效：{input_path}，跳过")
    
    return pdf_files, base_dirs

def get_default_output_dir(base_dirs):
    if not base_dirs:
        return None
    
    base_dirs_list = list(base_dirs)
    
    # 如果只有一个基础目录，使用其父目录作为基础目录
    if len(base_dirs_list) == 1:
        base_dir = os.path.dirname(base_dirs_list[0])
    else:
        base_dir = os.path.commonpath(base_dirs_list)
    
    return os.path.join(base_dir, "md_out")

def main():
    parser = argparse.ArgumentParser(
        description="将PDF文件或文件夹解析为markdown"
    )

    parser.add_argument(
        "inputs",
        nargs='+',
        type=str,
        help="输入文件或文件夹路径，支持多个（文件或文件夹）"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出文件夹路径（可选），默认为输入文件所在文件夹同一级的md_out"
    )

    args = parser.parse_args()

    try:
        PDF_FILE_PATHS, base_dirs = resolve_input_paths(args.inputs)
        
        if not PDF_FILE_PATHS:
            logger.error("未找到有效的PDF文件")
            exit(1)
        
        logger.info(f"找到 {len(PDF_FILE_PATHS)} 个PDF文件")
        
        if args.output:
            RESULT_SAVE_DIR = args.output
        else:
            RESULT_SAVE_DIR = get_default_output_dir(base_dirs)
        Path(RESULT_SAVE_DIR).mkdir(parents=True, exist_ok=True)
        logger.info(f"Markdown保存目录：{RESULT_SAVE_DIR}")

        call_mineru_api(PDF_FILE_PATHS, RESULT_SAVE_DIR)

    except Exception as e:
        logger.error(f"程序执行失败：{str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
