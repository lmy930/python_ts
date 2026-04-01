import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter


SERVERS = {
    '177': {'host': '192.168.90.177', 'user': 'heng.jiao', 'pwd': 'test1234'}
}


CASE_FOLDERS = ['case104', 'case105', 'case106', 'case107', 'case108']


CUSTOM_NAMES = [
    "Case104",
    "Case105",
    "Case106",
    "Case107",
    "Case108"
]

BASE_PATH = '/home/heng.jiao/Code/ts_nr_simulation_soc/test_and_sim/ulsim/rach_simu/'
FILE_NAME = 'sfn0_slot0_ul_result.mat'
OUTPUT_FILE = 'C:/Users/tools/Desktop/RACH_Simulation_Results.xlsx'

def parse_mat_structure(remote_file_content, is_first_case):
    """提取 SNR 和 prach.detecter_rate """
    try:
        data = loadmat(io.BytesIO(remote_file_content), squeeze_me=True, struct_as_record=False)
        target_data = None
        for key in data.keys():
            if not key.startswith('__'):
                target_data = data[key]
                break
        
        if target_data is None: return None, None
        if not isinstance(target_data, (list, np.ndarray)): target_data = [target_data]
            
        snrs, rates = [], []
        for item in target_data:
            try:
                s_val = float(item.snr)
                
                r_val = float(item.prach.detected_rate)
                
                
                if not is_first_case:
                    r_val = 1.0 - r_val
                
                snrs.append(s_val)
                rates.append(r_val)
            except Exception: continue
                
        if not snrs: return None, None
        
        snrs, rates = np.array(snrs), np.array(rates)
        sort_idx = np.argsort(snrs)
        return snrs[sort_idx], rates[sort_idx]
    except Exception as e:
        print(f"  [Error] 解析文件失败: {e}")
        return None, None

def get_remote_data(sftp_client, folder_name, is_first_case):
    full_path = f"{BASE_PATH}{folder_name}/{FILE_NAME}"
    try:
        with sftp_client.open(full_path, 'rb') as f:
            return parse_mat_structure(f.read(), is_first_case)
    except FileNotFoundError:
        print(f"  [Error] 文件不存在: {full_path}")
        return None, None

def generate_report():
    workbook = xlsxwriter.Workbook(OUTPUT_FILE)
    worksheet = workbook.add_worksheet('RACH_Results')

   
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'align': 'center'})
    label_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#F3F3F3', 'align': 'left'})
    data_fmt = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '0.000'})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'underline': True})

   
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVERS['177']['host'], username=SERVERS['177']['user'], password=SERVERS['177']['pwd'])
        sftp = ssh.open_sftp()
        print(f"已成功连接服务器 177")
    except Exception as e:
        print(f"连接服务器 177 失败: {e}")
        return

    
    comparison_data = [] 
    current_row = 0

    for idx, folder in enumerate(CASE_FOLDERS):
        print(f"正在处理 {folder}...")
        custom_title = CUSTOM_NAMES[idx] if idx < len(CUSTOM_NAMES) else folder
        
        
        is_first = (idx == 0)
        
        snr_vals, rate_vals = get_remote_data(sftp, folder, is_first)
        
        if snr_vals is None:
            continue

        rmin = float(np.min(rate_vals))
        rmax = float(np.max(rate_vals))
        if rmin <= 0:
            rmin = min(rmax * 1e-4, 1e-6) if rmax > 0 else 1e-6
        if rmax <= rmin:
            rmax = rmin * 10.0
       
        y_lo = float(10 ** np.floor(np.log10(rmin)))
        y_hi = float(10 ** np.ceil(np.log10(rmax)))
        if y_hi <= y_lo:
            y_hi = y_lo * 10.0

        case_info = {
            'title': custom_title,
            'snr_row': current_row + 1,
            'data_row': current_row + 2,
            'data_len': len(snr_vals),
            'raw_rates': rate_vals,
            'snr_values': snr_vals,
            'min_snr': float(np.min(snr_vals)),
            'max_snr': float(np.max(snr_vals)),
            'min_rate': rmin,
            'max_rate': rmax,
            'y_chart_min': y_lo,
            'y_chart_max': y_hi,
        }

        
        worksheet.write(current_row, 0, custom_title, title_fmt)
        worksheet.write(current_row + 1, 0, "SNR (dB)", label_fmt)
        worksheet.write(current_row + 2, 0, "Rate", label_fmt)
        
        for i, (s, r) in enumerate(zip(snr_vals, rate_vals)):
            worksheet.write(current_row + 1, i + 1, s, header_fmt)
            worksheet.write(current_row + 2, i + 1, r, data_fmt)

        comparison_data.append(case_info)
        current_row += 5  

    
    chart_start_row = current_row + 2
    for idx, info in enumerate(comparison_data):
        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
        
        chart.add_series({
            'name': 'Rate',
            'categories': ['RACH_Results', info['snr_row'], 1, info['snr_row'], info['data_len']],
            'values':     ['RACH_Results', info['data_row'], 1, info['data_row'], info['data_len']],
            'line':       {'color': '#C00000', 'width': 1.5},
            'marker':     {'type': 'circle', 'size': 5},
        })

        chart.set_title({'name': info['title']})
        
        chart.set_x_axis({
            'name': 'SNR (dB)',
            'min': info['min_snr'],
            'max': info['max_snr'],
            'major_gridlines': {'visible': True},
            'label_position': 'low',
            'crossing': info['min_snr'],
        })
        chart.set_y_axis({
            'name': 'Detecter Rate / (1-DR)',
            'min': info['y_chart_min'],
            'max': info['y_chart_max'],
            'log_base': 10,
            'major_gridlines': {'visible': True},
            'num_format': '0.00000',
            'label_position': 'next_to',
            'crossing': info['y_chart_min'],
        })
        chart.set_size({'width': 450, 'height': 300})

     
        r_pos = chart_start_row + (idx // 2) * 17
        c_pos = (idx % 2) * 8
        worksheet.insert_chart(r_pos, c_pos, chart)

    sftp.close()
    ssh.close()
    workbook.close()
    print(f"\n报告生成成功！文件已导出至: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_report()
