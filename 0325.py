import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter

# --- 1. 配置信息 ---
SERVERS = {
    '174': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'test1234'},
    '176': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'test1234'}
}


CASE_FOLDERS = ['case001', 'case002', 'case003', 'case004']

# 自定义标题
CUSTOM_NAMES = [
    "Case001: TDL-A QPSK",
    "Case002: TDL-B QPSK",
    "Case003: TDL-A 64QAM",
    "Case004: TDL-B 64QAM"
]

BASE_PATH = '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/simu_0325/'
FILE_NAME = 'sfn0_slot8_ul_result.mat'
OUTPUT_FILE = 'C:/Users/tools/Desktop/Simulation_Comparison_0325.xlsx'

def parse_mat_structure(remote_file_content):
    """提取 SNR 和 Throughtput """
    try:
        data = loadmat(io.BytesIO(remote_file_content), squeeze_me=True, struct_as_record=False)
        target_data = None
        for key in data.keys():
            if not key.startswith('__'):
                target_data = data[key]
                break
        
        if target_data is None: return None, None
        if not isinstance(target_data, (list, np.ndarray)): target_data = [target_data]
            
        snrs, thps = [], []
        for item in target_data:
            try:
                s_val = float(item.snr)
                t_val = float(item.pusch.throughtput)
                snrs.append(s_val)
                thps.append(t_val)
            except Exception: continue
                
        if not snrs: return None, None
        
        snrs, thps = np.array(snrs), np.array(thps)
        sort_idx = np.argsort(snrs)
        return snrs[sort_idx], thps[sort_idx]
    except Exception as e:
        print(f"  [Error] 解析文件失败: {e}")
        return None, None

def get_remote_data(ssh_client, sftp_client, folder_name):
    full_path = f"{BASE_PATH}{folder_name}/{FILE_NAME}"
    try:
        with sftp_client.open(full_path, 'rb') as f:
            return parse_mat_structure(f.read())
    except FileNotFoundError:
        print(f"  [Error] 文件不存在: {full_path}")
        return None, None

def generate_report():
    workbook = xlsxwriter.Workbook(OUTPUT_FILE)
    worksheet = workbook.add_worksheet('Comparison_Results')

    # --- 格式定义 ---
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'align': 'center'})
    label_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#F3F3F3', 'align': 'left'})
    data_fmt = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '0.000'})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'underline': True})

    # --- 2. 建立服务器连接 ---
    ssh_conns, sftp_conns = {}, {}
    for s_id in ['174', '176']:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SERVERS[s_id]['host'], username=SERVERS[s_id]['user'], password=SERVERS[s_id]['pwd'])
            ssh_conns[s_id] = ssh
            sftp_conns[s_id] = ssh.open_sftp()
            print(f"已连接服务器 {s_id}")
        except Exception as e:
            print(f"连接服务器 {s_id} 失败: {e}")
            return

    # --- 3. 抓取数据并写入表格 (合并SNR) ---
    comparison_data = [] 
    current_row = 0

    for idx, folder in enumerate(CASE_FOLDERS):
        print(f"正在处理 {folder}...")
        custom_title = CUSTOM_NAMES[idx] if idx < len(CUSTOM_NAMES) else folder
        
        snr174, thp174 = get_remote_data(ssh_conns['174'], sftp_conns['174'], folder)
        snr176, thp176 = get_remote_data(ssh_conns['176'], sftp_conns['176'], folder)
        
        active_snr = snr174 if snr174 is not None else snr176
        case_info = {
            'title': custom_title, 
            'rows': {}, 
            'raw_thp': [],
            'snr_values': active_snr 
        }

        worksheet.write(current_row, 0, custom_title, title_fmt)
        
       
        worksheet.write(current_row + 1, 0, "snr", label_fmt)
        if active_snr is not None:
            for i, s in enumerate(active_snr):
                worksheet.write(current_row + 1, i + 1, s, header_fmt)
            case_info['rows']['snr_row'] = current_row + 1
            case_info['data_len'] = len(active_snr)

        # 写入 174 Thp
        worksheet.write(current_row + 2, 0, "old", label_fmt)
        if thp174 is not None:
            for i, t in enumerate(thp174):
                worksheet.write(current_row + 2, i + 1, t, data_fmt)
            case_info['rows']['174_thp'] = current_row + 2
            case_info['raw_thp'].extend(thp174)

        # 写入 176 Thp
        worksheet.write(current_row + 3, 0, "new", label_fmt)
        if thp176 is not None:
            for i, t in enumerate(thp176):
                worksheet.write(current_row + 3, i + 1, t, data_fmt)
            case_info['rows']['176_thp'] = current_row + 3
            case_info['raw_thp'].extend(thp176)

        comparison_data.append(case_info)
        current_row += 6 

    # --- 4. 绘制 2x2 图表矩阵 ---
    chart_start_row = current_row + 2
    valid_chart_count = 0 

    for info in comparison_data:
        has_snr = 'snr_row' in info['rows']
        has_174 = '174_thp' in info['rows']
        has_176 = '176_thp' in info['rows']
        
        if not has_snr or not (has_174 or has_176):
            continue 

        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
        
        if has_174:
            chart.add_series({
                'name': 'old',
                'categories': ['Comparison_Results', info['rows']['snr_row'], 1, info['rows']['snr_row'], info['data_len']],
                'values':     ['Comparison_Results', info['rows']['174_thp'], 1, info['rows']['174_thp'], info['data_len']],
                'line':       {'color': '#4472C4', 'width': 1.5},
                'marker':     {'type': 'circle', 'size': 5},
            })
        
        if has_176:
            chart.add_series({
                'name': 'new',
                'categories': ['Comparison_Results', info['rows']['snr_row'], 1, info['rows']['snr_row'], info['data_len']],
                'values':     ['Comparison_Results', info['rows']['176_thp'], 1, info['rows']['176_thp'], info['data_len']],
                'line':       {'color': '#C00000', 'width': 1.5},
                'marker':     {'type': 'square', 'size': 5},
            })

     
        this_snr = info['snr_values']
        snr_min = min(this_snr) if this_snr is not None else -10
        snr_max = max(this_snr) if this_snr is not None else 20
        min_thp = min(info['raw_thp']) if info['raw_thp'] else 0

        chart.set_title({'name': info['title']})
        chart.set_x_axis({
            'name': 'SNR (dB)', 
            'major_gridlines': {'visible': True},
            'min': snr_min,          
            'max': snr_max,           
            'major_unit': 1,          
            'crossing': -200          
        })
        chart.set_y_axis({
            'name': 'Throughput', 
            'min': min_thp,           
            'max': 1.0, 
            'major_gridlines': {'visible': True}
        })
        chart.set_size({'width': 450, 'height': 300})

        # 2x2 布局
        r_pos = chart_start_row + (valid_chart_count // 2) * 17
        c_pos = (valid_chart_count % 2) * 8
        worksheet.insert_chart(r_pos, c_pos, chart)
        valid_chart_count += 1

    for s_id in sftp_conns:
        sftp_conns[s_id].close()
        ssh_conns[s_id].close()
    
    workbook.close()
    print(f"\n报告生成成功！文件已导出至: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_report()
