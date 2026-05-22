import re
from pathlib import Path
from bs4 import BeautifulSoup  # 4.14.3
import tempfile
import os
import sys
import pypandoc # pypandoc==1.16.2
from tqdm import tqdm
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
import log_config

def html_table_to_markdown_table(html_table_str: str) -> str:
    """
    将单个 <table>...</table> 的 HTML 字符串转换为 Markdown pipe 表格。
    支持 colspan（但不支持 rowspan，因 Markdown 本身不支持）。
    """
    soup = BeautifulSoup(html_table_str, 'html.parser')
    table = soup.find('table')
    if not table:
        return html_table_str  # 不是表格，原样返回

    rows = []
    max_cols = 0

    # 第一步：解析所有行和单元格，处理 colspan
    for tr in table.find_all('tr'):
        cells = []
        for cell in tr.find_all(['td', 'th']):
            text = ' '.join(cell.stripped_strings)  # 提取纯文本，去除多余空白
            colspan = int(cell.get('colspan', 1))
            cells.append((text, colspan))
        rows.append(cells)
        # 计算该行实际列数（考虑 colspan）
        total_cols = sum(colspan for _, colspan in cells)
        if total_cols > max_cols:
            max_cols = total_cols

    if not rows or max_cols == 0:
        return ""

    # 第二步：标准化每行为 max_cols 列（用空字符串填充 colspan 占位）
    md_rows = []
    for cells in rows:
        md_row = []
        col_index = 0
        for text, colspan in cells:
            md_row.append(text)
            # 如果 colspan > 1，则后面补空字符串占位（Markdown 不支持真正的合并，只能模拟）
            for _ in range(1, colspan):
                md_row.append("")
                col_index += 1
            col_index += 1
        # 补齐到 max_cols（防止错位）
        while len(md_row) < max_cols:
            md_row.append("")
        md_rows.append(md_row)

    # 第三步：生成 Markdown 表格
    if not md_rows:
        return ""

    # 表头 + 分隔线
    header = '| ' + ' | '.join(md_rows[0]) + ' |'
    separator = '| ' + ' | '.join(['---'] * len(md_rows[0])) + ' |'
    body = '\n'.join('| ' + ' | '.join(row) + ' |' for row in md_rows[1:])

    if body:
        markdown_table = header + '\n' + separator + '\n' + body
    else:
        # 只有一行（可能是无表头的数据）
        markdown_table = header + '\n' + separator

    return markdown_table


def convert_html_tables_in_md(md_content: str) -> str:
    """
    在整个 Markdown 内容中查找所有 <table>...</table> 块，并替换为 Markdown 表格。
    """
    # 非贪婪匹配所有 <table>...</table>
    def replace_func(match):
        html_block = match.group(0)
        return html_table_to_markdown_table(html_block)

    # 使用 re.DOTALL 使得 . 匹配换行符
    pattern = r'<table\b[^>]*>.*?</table>'
    new_content = re.sub(pattern, replace_func, md_content, flags=re.IGNORECASE | re.DOTALL)
    return new_content


def preprocess_md_replace_html_tables(md_path: Path) -> Path:
    """
    读取 Markdown 文件，将其中所有 HTML 表格转换为 Markdown 表格，
    返回临时文件路径。
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = convert_html_tables_in_md(content)

    # 创建临时文件
    temp_fd, temp_path = tempfile.mkstemp(suffix='.md')
    os.close(temp_fd)
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return Path(temp_path)


def markdown_to_docx(md_file_path: str | Path,
                     docx_output_path: str | Path = None,
                     template_path: str | Path = None):

    # 处理路径
    md_path = Path(md_file_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown文件不存在：{md_path.absolute()}")

    template_path = Path(template_path)
    if not template_path.exists():
        raise FileNotFoundError(f"字体模板文件不存在：{template_path.absolute()}")

    # 默认输出路径（同目录，替换后缀为docx）
    if docx_output_path is None:
        docx_output_path = md_path.with_suffix(".docx")
    else:
        file_stem = os.path.splitext(os.path.basename(md_file_path))[0]  # 无后缀的文件名
        docx_output_path = str(docx_output_path)+"/"+str(file_stem)+".docx"
        docx_output_path = Path(docx_output_path)

    # 👇 新增：将 HTML 表格转为 Markdown 表格
    temp_md_path = preprocess_md_replace_html_tables(md_path)

    try:
        output = pypandoc.convert_file(
            str(temp_md_path),  # 注意：这里用预处理后的临时文件
            'docx',
            format='markdown+tex_math_dollars+pipe_tables+grid_tables+simple_tables',  # raw_html 可以去掉了
            outputfile=str(docx_output_path),
            extra_args=[
                '--mathjax',
                f'--resource-path={str(md_path.parent)}',
                f'--reference-doc={str(template_path)}',
                '--wrap=none',
                '-M', 'table-width=100%',
            ]
        )

        if docx_output_path.exists():
            logger.success(f"转换成功！输出文件：{docx_output_path.absolute()}")
            return docx_output_path
        else:
            raise RuntimeError("转换失败：未生成docx文件")

    except Exception as e:
        logger.error(f"转换出错：{str(e)}")
        raise
    finally:
        # 清理临时文件
        if temp_md_path.exists():
            os.unlink(temp_md_path)


def get_all_md(root_dir):
    md_list = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file.lower().endswith('.md'):
                full_path = os.path.join(dirpath, file)
                md_list.append(full_path)
    return md_list

# ========== 调用示例 ==========
if __name__ == "__main__":

    input_md_paths = get_all_md(r"D:\工作\课题1")
    logger.info(f"找到 {len(input_md_paths)} 个 Markdown 文件")
    docx_output_path = Path(r"D:\工作\课题1\out_docx")
    template_file = Path("./md_out/font_template.docx")
    for input_md_path in tqdm(input_md_paths, desc="处理文件", unit="个", colour="green"):
        # 可以将引用图片类的markdown替换为完整docx
        input_md = Path(input_md_path)
        # 执行转换
        markdown_to_docx(md_file_path=input_md,
                         docx_output_path=docx_output_path,
                         template_path=template_file)


    # markdown_to_docx(
    #     md_file_path=Path(r"xxx"),
    #     docx_output_path=Path(r"xxxx"),
    #     template_path=template_file
    # )