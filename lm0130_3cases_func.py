# 基础版本，主要用来检查可行性
# 需要保证不同分支的数据在不同的服务器上，且路径相同
# 同lmy0121.py

# 在基础版本上调整，支持文件路径不同的场景，方便区分
# 修改参考点的位置，统一对齐
# 修改横轴的刻度值为0.5
# version2.0
# 但其实总能想办法把它们的路径设置为相同的（0130 

# 修改大标题
# 修改小标题为原来的版式
# version3.0

# 在version 2.0 的基础上，封装为函数，方便直接生成不同的比较结果（sheet
# version 4.0

import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter

# 1. 服务器基础配置 
SERVERS = {
    '174': {
        'host': '192.168.90.174', 
        'user': 'mengyao.li', 
        'pwd': 'test1234', 
        'base_path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/',
        'display_name': 'acc100'  
    },
    '175': {
        'host': '192.168.90.175', 
        'user': 'mengyao.li', 
        'pwd': 'test1234', 
        'base_path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/',
        'display_name': 'master'  
    },
    '176': {
        'host': '192.168.90.176', 
        'user': 'mengyao.li', 
        'pwd': 'test1234', 
        'base_path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/',
        'display_name': 'dev_v1'  
    },
    '177': {
        'host': '192.168.90.177', 
        'user': 'mengyao.li', 
        'pwd': 'test1234', 
        'base_path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/',
        'display_name': 'dev_v2'  
    }
}

# 2. Cases 配置
CASES = [
    [
        {'174': 'pusch_compare_mrc/case001', '175': 'pusch_compare_mrc/case001', '176': 'pusch_compare_mrc/case001', '177': 'pusch_compare_mrc/case001'}, 
        'case001 (TDLB100-400 + 2T2R + G-FR1-A3-27)'
    ],
    [
        {'174': 'pusch_compare_mrc/case002', '175': 'pusch_compare_mrc/case002', '176': 'pusch_compare_mrc/case002', '177': 'pusch_compare_mrc/case002'}, 
        'case002 (TDLC300-100 + 2T2R + G-FR1-A4-27)'
    ],
    [
        {'174': 'pusch_compare_mrc/case003', '175': 'pusch_compare_mrc/case003', '176': 'pusch_compare_mrc/case003', '177': 'pusch_compare_mrc/case003'}, 
        'case003 (TDLB100-400 + 1T2R + G-FR1-A3-32)'
    ]
]

# 3. 参考点
CUSTOM_POINTS = {
    0: (1.3, 0.7),  # Case 1
    1: (19.5, 0.7), # Case 2 
    2: (-2.5, 0.7)  # Case 3 
}

def parse_mat_structure(remote_file_content):
    """提取 SNR 和 Throughput"""
    data = loadmat(io.BytesIO(remote_file_content), squeeze_me=True, struct_as_record=False)
    if 'demodResult' not in data: return None, None
    res = data['demodResult']
    if not isinstance(res, (list, np.ndarray)): res = [res]
    snrs, thps = [], []
    for item in res:
        try:
            snrs.append(float(item.snr))
            thps.append(float(item.pusch.throughtput))
        except Exception: continue
    return np.array(snrs), np.array(thps)

def generate_comparison_sheet(writer, server_id_a, server_id_b, sheet_name=None):
    """
    封装的 Sheet 生成函数
    server_id_a:  
    server_id_b: 
    """
    workbook = writer.book
    conf_a = SERVERS[server_id_a]
    conf_b = SERVERS[server_id_b]
    
    name_a = conf_a['display_name']
    name_b = conf_b['display_name']
    
    if not sheet_name:
        sheet_name = f'{name_a} 和 {name_b}'
    
    worksheet = workbook.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = worksheet

    # --- 格式定义 (保持原版) ---
    case_title_fmt = workbook.add_format({'bold': True, 'bg_color': "#F3EFEFE8", 'border': 1})
    border_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
    highlight_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': "#FFFFFF", 'bold': True})
    point_title_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': "#FFFFFF"})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'align': 'left', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1, 'text_wrap': True, 'indent': 1})

    global_title_1 = (
        "1. 协议版本：TS38104 V17.7.0\n"
        "2. 章节名称：8.2.1节“Requirements for PUSCH with transform precoding disabled”\n"
        "3. 仿真表格：Table8.2.1.2-6"
    )
    global_title_2 = (
        "1. 协议版本：TS38104 V17.7.0\n"
        "2. 章节名称：8.2.2节“Requirements for PUSCH with transform precoding enabled”\n"
        "3. 仿真表格：Table8.2.2.2-2"
    )

    worksheet.set_row(0, 55) 
    worksheet.merge_range('A1:R1', global_title_1, title_fmt)

    current_row = 2
    all_case_charts = []
    results_cache = []
    max_snr_len = 0

    # --- 第一阶段：读取数据 ---
    for idx, (paths, title_str) in enumerate(CASES):
        print(f"[{sheet_name}] 正在读取 Case {idx+1}...")
        case_data = {}
        for sid in [server_id_a, server_id_b]:
            conf = SERVERS[sid]
            case_sub_path = paths.get(sid)  
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(conf['host'], username=conf['user'], password=conf['pwd'])
                
                full_path = f"{conf['base_path']}{case_sub_path}/sfn0_slot8_ul_result.mat"
                
                sftp = ssh.open_sftp()
                with sftp.open(full_path, 'rb') as f:
                    snr, thp = parse_mat_structure(f.read())
                sftp.close()
                ssh.close()
                
                if snr is not None:
                    sort_idx = np.argsort(snr)
                    case_data[sid] = {'snr': snr[sort_idx], 'thp': thp[sort_idx]}
                    if len(snr) > max_snr_len: max_snr_len = len(snr)
            except Exception as e: 
                print(f"  -> 服务器 {sid} ({conf['host']}) 读取失败: {e}")
        results_cache.append(case_data)

    # --- 第二阶段：写入 Excel ---
    for idx, ((paths, title_str), case_data) in enumerate(zip(CASES, results_cache)):
        if server_id_a in case_data and server_id_b in case_data:
            if idx == 2:
                current_row += 1 
                worksheet.set_row(current_row, 55)
                worksheet.merge_range(current_row, 0, current_row, 17, global_title_2, title_fmt)
                current_row += 2 

            snr_vals = case_data[server_id_b]['snr']
            thp_b = case_data[server_id_b]['thp'] 
            thp_a = case_data[server_id_a]['thp'] 
            c_snr, c_thp = CUSTOM_POINTS.get(idx, (None, None))
            
            worksheet.write(current_row, 0, f"Case {idx+1}: {title_str}", case_title_fmt)
            
            worksheet.write(current_row + 1, 0, "commit", border_fmt)
            worksheet.write(current_row + 1, 1, "snr", border_fmt)
            for i, val in enumerate(snr_vals): 
                worksheet.write(current_row + 1, i + 2, val, border_fmt)

            worksheet.write(current_row + 2, 0, name_b, border_fmt)  
            worksheet.write(current_row + 2, 1, "Thp1", border_fmt)
            for i, val in enumerate(thp_b): 
                worksheet.write(current_row + 2, i + 2, val, border_fmt)

            worksheet.write(current_row + 3, 0, name_a, border_fmt)  
            worksheet.write(current_row + 3, 1, "Thp2", border_fmt)
            for i, val in enumerate(thp_a): 
                worksheet.write(current_row + 3, i + 2, val, border_fmt)

            custom_col = 2 + max_snr_len + 1 
            if c_snr is not None:
                worksheet.set_column(custom_col, custom_col, 10)
                worksheet.write(current_row, custom_col, "Request", point_title_fmt)
                worksheet.write(current_row + 1, custom_col, c_snr, highlight_fmt)
                worksheet.merge_range(current_row + 2, custom_col, current_row + 3, custom_col, c_thp, highlight_fmt)

            # 图表
            chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
            all_snrs = snr_vals.tolist() + ([c_snr] if c_snr is not None else [])
            all_thps = thp_b.tolist() + thp_a.tolist() + ([c_thp] if c_thp is not None else [])
            x_min, x_max = min(all_snrs), max(all_snrs)
            y_min = min(all_thps)

            chart.add_series({
                'name': [sheet_name, current_row + 2, 0], 
                'categories': [sheet_name, current_row + 1, 2, current_row + 1, 2 + len(snr_vals) - 1],
                'values':     [sheet_name, current_row + 2, 2, current_row + 2, 2 + len(snr_vals) - 1],
                'line': {'color': '#4F81BD'},
            })
            chart.add_series({
                'name': [sheet_name, current_row + 3, 0],
                'categories': [sheet_name, current_row + 1, 2, current_row + 1, 2 + len(snr_vals) - 1],
                'values':     [sheet_name, current_row + 3, 2, current_row + 3, 2 + len(snr_vals) - 1],
                'line': {'color': '#C0504D'},
            })
            if c_snr is not None:
                chart.add_series({
                    'name': 'Request',
                    'categories': [sheet_name, current_row + 1, custom_col, current_row + 1, custom_col],
                    'values':     [sheet_name, current_row + 2, custom_col, current_row + 2, custom_col],
                    'marker':     {'type': 'diamond', 'size': 7, 'fill': {'color': "#ECE031"}},
                    'line':       {'none': True},
                })

            chart.set_title({'name': f'Case {idx+1}: {title_str}', 'name_font': {'size': 12, 'bold': True}})
            chart.set_x_axis({'name': 'SNR (dB)', 'min': x_min, 'max': x_max, 'major_unit': 0.5, 'major_gridlines': {'visible': True}, 'crossing': -200, 'axis_position': 'on_tick'})
            chart.set_y_axis({'name': 'Throughput', 'min': y_min, 'max': 1.0, 'num_format': '0.000', 'major_gridlines': {'visible': True}})
            chart.set_size({'width': 500, 'height': 340})
            all_case_charts.append(chart)
            current_row += 6 

    # 图表排版
    chart_base_row = current_row + 2
    for i, chart in enumerate(all_case_charts):
        r_pos, c_pos = i // 2, i % 2
        worksheet.insert_chart(chart_base_row + (r_pos * 17), c_pos * 8, chart)

# --- 主程序执行部分 ---
output_path = 'C:/Users/tools/Desktop/PUSCH_MultiCompare.xlsx'
writer = pd.ExcelWriter(output_path, engine='xlsxwriter')

TASKS = [
    ('177', '174', 'acc100_vs_masterwinsize'),
    ('177', '175', 'acc100_vs_winsize'),
    ('177', '176', 'acc100_vs_sedft')
]

for s_a, s_b, s_name in TASKS:
    generate_comparison_sheet(writer, s_a, s_b, s_name)

writer.close()
#print(f"Excel 生成完毕！文件保存至: {output_path}")