import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter

### 服务器配置
SERVERS = {
    '174': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'TEST1234', 
            'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'},
    '175': {'host': '192.168.90.175', 'user': 'mengyao.li', 'pwd': 'TEST1234', 
            'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'},
    '176': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'TEST1234', 
            'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'},
    '177': {'host': '192.168.90.177', 'user': 'mengyao.li', 'pwd': 'TEST1234', 
            'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'}
}

### 
COMMIT_MAPPING = {
    '174': 'abc1234',
    '175': '9d1530',
    '176': 'b73e15',
    '177': '3e4010'
}

### Cases
CASES = [
    ['pusch_compare_mrc_big/case001', 'TDLB100-400 + 1T2R + G-FR1-A3-8'],
    ['pusch_compare_mrc_big/case002', 'TDLC300-100 + 1T2R + G-FR1-A4-8'],
    ['pusch_compare_mrc_big/case003', 'TDLA30-10 + 1T2R + G-FR1-A5-8'],
    ['pusch_compare_mrc_big/case004', 'TDLA30-10 + 1T2R + G-FR1-A9-1'],
]

### 参考点
CUSTOM_POINTS = {
    0: (-2.5, 0.7),  # Case 001
    1: (10, 0.7),  # Case 002 
    2: (12.4, 0.7),  # Case 003 
    3: (19.9, 0.7),  # Case 004 
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

def create_simulation_sheet(workbook, sheet_name, server_ids):
    
    worksheet = workbook.add_worksheet(sheet_name)
    
    # 格式定义
    case_title_fmt = workbook.add_format({'bold': True, 'bg_color': "#FFFFFF", 'border': 1})
    border_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
    highlight_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': "#FFFFFF", 'bold': True})
    point_title_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': "#FFFFFF"})
    title_fmt = workbook.add_format({
        'bold': True, 'font_size': 11, 'align': 'left', 'valign': 'vcenter', 
        'bg_color': "#FFFEFE", 'border': 1, 'text_wrap': True, 'indent': 1
    })

    global_title = (
        "1. 协议版本：TS38104 V17.7.0\n"
        "2. 章节名称：8.2.1节“Requirements for PUSCH with transform precoding disabled”\n"
        "3. 仿真表格：Table8.2.1.2-1 Minimum requirements for PUSCH with 70% of maximum throughput, Type A, 5 MHz channel bandwidth, 15 kHz SCS"
    )

    worksheet.set_row(0, 55) 
    worksheet.merge_range('A1:R1', global_title, title_fmt)

    current_row = 2
    all_case_charts = []
    id1, id2 = server_ids[0], server_ids[1]

    for idx, (case_path, title_str) in enumerate(CASES):
        print(f"[{sheet_name}] 正在读取 Case {idx+1}...")
        case_data = {}
        
        for name in server_ids:
            conf = SERVERS[name]
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(conf['host'], username=conf['user'], password=conf['pwd'])
                full_path = f"{conf['path']}{case_path}/sfn0_slot8_ul_result.mat"
                sftp = ssh.open_sftp()
                with sftp.open(full_path, 'rb') as f:
                    snr, thp = parse_mat_structure(f.read())
                sftp.close()
                ssh.close()
                if snr is not None:
                    sort_idx = np.argsort(snr)
                    case_data[name] = {'snr': snr[sort_idx], 'thp': thp[sort_idx]}
            except Exception as e: 
                print(f"  -> 服务器 {name} 失败: {e}")

        if id1 in case_data and id2 in case_data:
            snr_vals = case_data[id1]['snr']
            thp_id1 = case_data[id1]['thp']
            thp_id2 = case_data[id2]['thp']
            c_snr, c_thp = CUSTOM_POINTS.get(idx, (None, None))
            
            commit_val1 = COMMIT_MAPPING.get(id1, id1)
            commit_val2 = COMMIT_MAPPING.get(id2, id2)

            # 写入标题
            worksheet.write(current_row, 0, f"Case {idx+1}: {title_str}", case_title_fmt)
            
            # 数据表格
            worksheet.write(current_row + 1, 0, "commit", border_fmt)
            worksheet.write(current_row + 1, 1, "snr", border_fmt)
            for i, val in enumerate(snr_vals): 
                worksheet.write(current_row + 1, i + 2, val, border_fmt)

            worksheet.write(current_row + 2, 0, commit_val1, border_fmt)
            worksheet.write(current_row + 2, 1, f"thp", border_fmt)
            for i, val in enumerate(thp_id1): 
                worksheet.write(current_row + 2, i + 2, val, border_fmt)

            worksheet.write(current_row + 3, 0, commit_val2, border_fmt)
            worksheet.write(current_row + 3, 1, f"thp", border_fmt)
            for i, val in enumerate(thp_id2): 
                worksheet.write(current_row + 3, i + 2, val, border_fmt)

            # 参考点
            custom_col = 2 + len(snr_vals) + 2
            if c_snr is not None:
                worksheet.set_column(custom_col, custom_col, 9)
                worksheet.write(current_row, custom_col, "Request", point_title_fmt)
                worksheet.write(current_row + 1, custom_col, c_snr, highlight_fmt)
                worksheet.merge_range(current_row + 2, custom_col, current_row + 3, custom_col, c_thp, highlight_fmt)

            # 创建图表
            chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
            
            all_snrs = snr_vals.tolist() + ([c_snr] if c_snr is not None else [])
            all_thps = thp_id1.tolist() + thp_id2.tolist() + ([c_thp] if c_thp is not None else [])
            x_min, x_max = min(all_snrs), max(all_snrs)
            y_min = min(all_thps)

            # 曲线 1 
            chart.add_series({
                'name': commit_val1,
                'categories': [sheet_name, current_row + 1, 2, current_row + 1, 2 + len(snr_vals) - 1],
                'values':     [sheet_name, current_row + 2, 2, current_row + 2, 2 + len(snr_vals) - 1],
                'line': {'color': '#4F81BD'},
            })
            # 曲线 2 
            chart.add_series({
                'name': commit_val2,
                'categories': [sheet_name, current_row + 1, 2, current_row + 1, 2 + len(snr_vals) - 1],
                'values':     [sheet_name, current_row + 3, 2, current_row + 3, 2 + len(snr_vals) - 1],
                'line': {'color': '#C0504D'},
            })
            # 参考点
            if c_snr is not None:
                chart.add_series({
                    'name': 'Request',
                    'categories': [sheet_name, current_row + 1, custom_col, current_row + 1, custom_col],
                    'values':     [sheet_name, current_row + 2, custom_col, current_row + 2, custom_col],
                    'marker':     {'type': 'diamond', 'size': 6, 'fill': {'color': "#ECE031"}, 'border': {'color': 'black'}},
                    'line':       {'none': True},
                })

            chart.set_title({'name': f'Case {idx+1}: {title_str}', 'name_font': {'size': 12, 'bold': True}})
            
            chart.set_x_axis({
                'name': 'SNR (dB)', 
                'min': x_min, 
                'max': x_max, 
                'major_gridlines': {'visible': True},
                'crossing': -200,  
                'axis_position': 'on_tick'
            })
            chart.set_y_axis({
                'name': 'Throughput', 
                'min': y_min, 
                'max': 1.0, 
                'num_format': '0.000', 
                'major_gridlines': {'visible': True}
            })
            
            chart.set_size({'width': 500, 'height': 340})
            all_case_charts.append(chart)
            
            current_row += 6 

    # 图表布局
    chart_base_row = current_row + 2
    for i, chart in enumerate(all_case_charts):
        r_pos, c_pos = i // 2, i % 2
        worksheet.insert_chart(chart_base_row + (r_pos * 18), c_pos * 9, chart)

### 主程序
output_file = 'C:/Users/tools/Desktop/PUSCH_Comparison_Report_new.xlsx'
workbook = xlsxwriter.Workbook(output_file)

create_simulation_sheet(workbook, 'master和acc100', ['175', '177'])

create_simulation_sheet(workbook, 'acc100和时域滤波', ['176', '177'])

workbook.close()
#print(f"报告已生成: {output_file}")