#4G2天线仿真
import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter

# --- 配置信息 ---
SERVERS = {
    '174': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'test1234', 'cases': range(297, 299)},
    '175': {'host': '192.168.90.175', 'user': 'mengyao.li', 'pwd': 'test1234', 'cases': range(299, 303)},
    '176': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'test1234', 'cases': range(303, 305)},
    '177': {'host': '192.168.90.177', 'user': 'mengyao.li', 'pwd': 'test1234', 'cases': range(305, 307)},
}

# --- 参考点与自定义名称配置 (请在此处修改名称) ---
# 格式: { case_num: ( [(snr, thp), ...], "自定义名称" ) }
REQUIREMENT_POINTS = {
    297: ([(-4.2, 0.3), (-0.4, 0.7)], "2Ant/EPA5/100RB/QPSK/MCS6/1Layer"), 
    298: ([(11.5, 0.7)], "2Ant/EPA5/100RB/16QAM/MCS20/1Layer"),
    299: ([(19.7, 0.7)], "2Ant/EPA5/100RB/64QAM/MCS28/1Layer"),
    300: ([(-2.7, 0.8), (1.8, 0.7)], "2Ant/EVA5/1RB/QPSK/MCS7/1Layer"), 
    301: ([(4.3, 0.3), (11.5, 0.7)], "2Ant/EVA5/1RB/16QAM/MCS20/1Layer"), 
    302: ([(18.7, 0.7)], "2Ant/EVA5/1RB/64QAM/MCS28/1Layer"), 
    303: ([(-4.1, 0.3), (0.2, 0.7)], "2Ant/EVA70/100RB/QPSK/MCS6/1Layer"), 
    304: ([(4.2, 0.3), (13.0, 0.7)], "2Ant/EVA70/1RB/16QAM/MCS20/1Layer"), 
    305: ([(-2.4, 0.3), (2.4, 0.7)], "2Ant/ETU70/1RB/QPSK/MCS7/1Layer"), 
    306: ([(-2.1, 0.3), (2.9, 0.7)], "2Ant/ETU300/1RB/QPSK/MCS7/1Layer"), 
}

BASE_PATH = '/home/mengyao.li/Code/ts_lte_simulation/test_and_sim/ulsim/simuCase/BW20M_2Rx/'
FILE_NAME = 'demod_result.mat'
OUTPUT_FILE = 'C:/Users/tools/Desktop/0309_2Rx.xlsx'

def parse_mat_structure(remote_file_content):
    """提取 SNR 和 Throughput"""
    try:
        data = loadmat(io.BytesIO(remote_file_content), squeeze_me=True, struct_as_record=False)
        if 'Result' not in data: return None, None
        res = data['Result']
        if not isinstance(res, (list, np.ndarray)): res = [res]
        snrs, thps = [], []
        for item in res:
            try:
                snrs.append(float(item.snr))
                thps.append(float(item.pusch.thp))
            except AttributeError: continue
        if not snrs: return None, None
        snrs, thps = np.array(snrs), np.array(thps)
        sort_idx = np.argsort(snrs)
        return snrs[sort_idx], thps[sort_idx]
    except Exception:
        return None, None

def generate_report():
    workbook = xlsxwriter.Workbook(OUTPUT_FILE)
    worksheet = workbook.add_worksheet('4Rx_Results')

    # 格式定义
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'align': 'center'})
    border_fmt = workbook.add_format({'border': 1, 'align': 'center'})
    ref_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#FFF2CC', 'align': 'center', 'font_color': "#000000"})
    # 表格上方的 Case 标题格式
    title_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'font_color': "#000000", 'underline': True})

    # 1. 收集所有数据
    all_cases_data = []
    for s_id, info in SERVERS.items():
        print(f"正在连接服务器: {s_id}...")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(info['host'], username=info['user'], password=info['pwd'])
            sftp = ssh.open_sftp()
            for case_num in info['cases']:
                case_name = f"test_case_{case_num}"
                full_path = f"{BASE_PATH}{case_name}/{FILE_NAME}"
                print(f"  -> 读取 {case_name}...")
                snr, thp = None, None
                try:
                    with sftp.open(full_path, 'rb') as f:
                        snr, thp = parse_mat_structure(f.read())
                except FileNotFoundError:
                    print(f"     [Skip] 文件不存在: {full_path}")
                all_cases_data.append((case_name, snr, thp, case_num))
            sftp.close()
            ssh.close()
        except Exception as e:
            print(f"无法连接服务器 {s_id}: {e}")

    # 2. 分组写入 Excel (4+4+2)
    current_row = 0
    case_groups = [all_cases_data[0:4], all_cases_data[4:8], all_cases_data[8:len(all_cases_data)]]

    for group in case_groups:
        if not group: continue
        group_charts = []
        
        # --- 写入表格 ---
        for case_name, snr, thp, case_num in group:
            # 解析配置中的参考点和自定义名称
            req_data = REQUIREMENT_POINTS.get(case_num, ([], f"Case {case_num}"))
            ref_points = req_data[0]
            custom_name = req_data[1]

            # 写入自定义标题
            worksheet.write(current_row, 0, f"Case {case_num}: {custom_name}", title_fmt)
            worksheet.write(current_row + 1, 0, "SNR (dB)", header_fmt)
            worksheet.write(current_row + 2, 0, "Thp", border_fmt)
            
            data_len = 0
            if snr is not None:
                data_len = len(snr)
                for i, (s_val, t_val) in enumerate(zip(snr, thp)):
                    worksheet.write(current_row + 1, i + 1, s_val, header_fmt)
                    worksheet.write(current_row + 2, i + 1, t_val, border_fmt)

            # --- 写入参考点表格 ---
            ref_col_start = 13 
            if ref_points:
                num_points = len(ref_points)
                if num_points > 1:
                    worksheet.merge_range(current_row, ref_col_start, current_row, ref_col_start + num_points - 1, "Request", ref_fmt)
                else:
                    worksheet.write(current_row, ref_col_start, "Request", ref_fmt)
                
                for i, (r_snr, r_thp) in enumerate(ref_points):
                    worksheet.write(current_row + 1, ref_col_start + i, r_snr, ref_fmt)
                    worksheet.write(current_row + 2, ref_col_start + i, r_thp, border_fmt)

            # --- 创建图表 ---
            chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
            
            # 序列1: 仿真数据线
            if snr is not None:
                chart.add_series({
                    'name': 'ulak reference link',
                    'categories': ['4Rx_Results', current_row + 1, 1, current_row + 1, data_len],
                    'values':     ['4Rx_Results', current_row + 2, 1, current_row + 2, data_len],
                    'line':       {'width': 1.5, 'color': '#4472C4'},
                    'marker':     {'type': 'circle', 'size': 4},
                })

            # 序列2: 参考点 (Requirement)
            if ref_points:
                chart.add_series({
                    'name': 'Requirement',
                    'categories': ['4Rx_Results', current_row + 1, ref_col_start, current_row + 1, ref_col_start + len(ref_points) - 1],
                    'values':     ['4Rx_Results', current_row + 2, ref_col_start, current_row + 2, ref_col_start + len(ref_points) - 1],
                    'marker':     {'type': 'diamond', 'size': 7, 'fill': {'color': "#C9C503"}, 'border': {'color': "#E6D70B"}},
                    'line':       {'none': True}, 
                })

            # 坐标轴动态范围与名称同步
            x_min = min(snr) if snr is not None else -5
            x_max = max(snr) if snr is not None else 15
            if ref_points:
                ref_snrs = [p[0] for p in ref_points]
                x_min = min(x_min, min(ref_snrs))
                x_max = max(x_max, max(ref_snrs))

            chart.set_title({'name': custom_name,'name_font': {'size':11}})# 图表标题设为自定义名称
            chart.set_x_axis({
                'name': 'snr (dB)', 
                'major_gridlines': {'visible': True},
                'min': x_min, 'max': x_max,
                'major_unit': 1, 'num_format': '0.0', 'crossing': -200
            })
            chart.set_y_axis({
                'name': 'Thp', 'major_gridlines': {'visible': True},
                'min': 0, 'max': 1.0, 'num_format': '0.00'
            })
            chart.set_size({'width': 440, 'height': 280})
            group_charts.append(chart)
            
            current_row += 5 

        # --- 插入图表矩阵 ---
        chart_start_row = current_row + 1
        for idx, chart in enumerate(group_charts):
            worksheet.insert_chart(chart_start_row + (idx // 2 * 16), (idx % 2 * 8), chart)
        
        rows_needed = 34 if len(group) > 2 else 18
        current_row = chart_start_row + rows_needed

    workbook.close()
    print(f"\n任务完成！文件已生成: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_report()