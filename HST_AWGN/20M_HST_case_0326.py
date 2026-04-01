


import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter
import math

 
SERVERS = {
    '174': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'test1234'},
    '177': {'host': '192.168.90.177', 'user': 'mengyao.li', 'pwd': 'test1234'},
    '176': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'test1234'}
}

BASE_PATH = '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/20M_HST_case_0326/'
FILE_NAME = 'sfn0_slot8_ul_result.mat'
OUTPUT_FILE = 'C:/Users/tools/Desktop/20M_0326.xlsx'

def get_mapping_data(mcs_index):
  
    if 0 <= mcs_index <= 4: return 2
    elif 5 <= mcs_index <= 10: return 4
    elif 11 <= mcs_index <= 19: return 6
    elif 20 <= mcs_index <= 27: return 8
    return 2

def get_target_server(case_idx):
    
    if 0 <= case_idx <= 7:   return '174'
    if 8<= case_idx <= 15:  return '177'
    if 16 <= case_idx <= 23: return '176'
    return None

def parse_mat_structure(remote_file_content):
    
    try:
        data = loadmat(io.BytesIO(remote_file_content), squeeze_me=True, struct_as_record=False)
        target_data = None
        for key in data.keys():
            if not key.startswith('__'):
                target_data = data[key]
                break
        
        if target_data is None: return None
        if not isinstance(target_data, (list, np.ndarray)): 
            target_data = [target_data]
            
        records = []
        for item in target_data:
            try:
               
                thp = 0.0
                if hasattr(item.pusch, 'throughtput'):
                    thp = float(item.pusch.throughtput)
                elif hasattr(item.pusch, 'throughput'):
                    thp = float(item.pusch.throughput)
                
                
                log_post_snr = 0.0
                if hasattr(item.pusch, 'postSnr'):
                    psnr_data = item.pusch.postSnr
                    
                    mean_val = np.mean(psnr_data) if isinstance(psnr_data, (list, np.ndarray)) else float(psnr_data)
                   
                    if mean_val > 0:
                        log_post_snr = 10 * math.log10(mean_val)
                    else:
                        log_post_snr = -99.0  
                
                records.append({
                    'snr': float(item.snr),
                    'throughput': thp,
                    'postSnr_dB': log_post_snr
                })
            except Exception: continue
                
        if not records: return None
        return sorted(records, key=lambda x: x['snr'])
    except Exception as e:
        print(f"  [Error] 解析失败: {e}")
        return None

def generate_report():
    workbook = xlsxwriter.Workbook(OUTPUT_FILE)
    worksheet = workbook.add_worksheet('Full_Results')

    
    title_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    header_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 
        'align': 'center', 'valign': 'vcenter'
    })
    data_fmt = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.000'
    })

    
    ssh_conns, sftp_conns = {}, {}
    for s_id in ['174', '177', '176']:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SERVERS[s_id]['host'], username=SERVERS[s_id]['user'], password=SERVERS[s_id]['pwd'])
            ssh_conns[s_id] = ssh
            sftp_conns[s_id] = ssh.open_sftp()
            print(f"√ 已连接服务器 {s_id}")
        except Exception as e:
            print(f"× 服务器 {s_id} 无法连接: {e}")

   
    for i in range(24):
        case_folder = f"case{i:03d}"
        server_id = get_target_server(i)
        qam_order = get_mapping_data(i) 
        
        base_row = (i // 6) * 18
        base_col = (i % 6) * 4
        
       
        worksheet.set_column(base_col, base_col + 2, 13)
        
        full_title = f"{case_folder} (MCS:{i}, Qm:{qam_order})"
        worksheet.merge_range(base_row, base_col, base_row, base_col + 2, full_title, title_fmt)
        
       
        worksheet.write(base_row + 1, base_col, "SNR", header_fmt)
        worksheet.write(base_row + 1, base_col + 1, "Throughput", header_fmt)
        worksheet.write(base_row + 1, base_col + 2, "PostSNR(dB)", header_fmt)

        if server_id in sftp_conns:
            full_path = f"{BASE_PATH}{case_folder}/{FILE_NAME}"
            print(f"读取 {server_id}: {case_folder}...")
            
            try:
                with sftp_conns[server_id].open(full_path, 'rb') as f:
                    results = parse_mat_structure(f.read())
                    if results:
                        for r_idx, res in enumerate(results):
                            row = base_row + 2 + r_idx
                            worksheet.write(row, base_col, res['snr'], data_fmt)
                            worksheet.write(row, base_col + 1, res['throughput'], data_fmt)
                            worksheet.write(row, base_col + 2, res['postSnr_dB'], data_fmt)
                    else:
                        worksheet.write(base_row + 2, base_col, "N/A", data_fmt)
            except FileNotFoundError:
                worksheet.write(base_row + 2, base_col, "No File", data_fmt)
        else:
            worksheet.write(base_row + 2, base_col, "No Conn", data_fmt)

   
    for s_id in sftp_conns:
        sftp_conns[s_id].close()
        ssh_conns[s_id].close()
    
    workbook.close()
    print(f"\n任务全部完成！报表已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_report()

