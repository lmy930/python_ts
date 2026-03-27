###批量处理数据

# import os
# import shutil
# import json

# def get_mapping_data(mcs_index):
#     """
#     
#     MCS Index (Imcs) -> Modulation Order (Qm)
#     """
#     if 0 <= mcs_index <= 4:
#         return 2
#     elif 5 <= mcs_index <= 10:
#         return 4
#     elif 11 <= mcs_index <= 19:
#         return 6
#     elif 20 <= mcs_index <= 27:
#         return 8
#     return 2

# def main():
#   
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     src_folder_name = "case000"
#     src_path = os.path.join(base_dir, src_folder_name)
    
#     if not os.path.exists(src_path):
#         print(f"错误：在 {base_dir} 下未找到 {src_folder_name}")
#         return

#     
#     case_list_path = os.path.join(base_dir, "case-list.txt")
#     all_cases = [f"case{str(i).zfill(3)}" for i in range(28)]
#     with open(case_list_path, 'w', encoding='utf-8') as f:
#         f.write("\n".join(all_cases))
#     print(f"√ 已更新 case-list.txt (共 28 行)")

#     
#     for i in range(1, 28):
#         new_case_name = f"case{str(i).zfill(3)}"
#         new_case_path = os.path.join(base_dir, new_case_name)
        
#         
#         if os.path.exists(new_case_path):
#             shutil.rmtree(new_case_path)
#         shutil.copytree(src_path, new_case_path)
        
#         target_qam = get_mapping_data(i)
#         current_snr = "未知"

#        
#         
#         tti_path = os.path.join(new_case_path, "in", "sfn0_slot8_ul_tti.json")
#         if os.path.exists(tti_path):
#             with open(tti_path, 'r', encoding='utf-8') as f:
#                 tti_data = json.load(f)
            
#             try:
#                 # 定位到源码中的具体位置[cite: 1]
#                 pusch_pdu = tti_data["vec_pdu"][0]["ul_pdu_configuration"]["pusch_pdu"][0]
#                 pusch_pdu["mcs_index"] = i
#                 pusch_pdu["qam_mod_order"] = target_qam
#             except (KeyError, IndexError) as e:
#                 print(f"错误：{new_case_name} 的 TTI JSON 结构解析失败")

#             with open(tti_path, 'w', encoding='utf-8') as f:
#                 json.dump(tti_data, f, indent=4)

#        
#         # 对应源码结构: snr -> snr (这是一个列表 [-6, -4.5])
#         cfg_path = os.path.join(new_case_path, "in", "ul_simu_cfg.json")
#         if os.path.exists(cfg_path):
#             with open(cfg_path, 'r', encoding='utf-8') as f:
#                 cfg_data = json.load(f)
            
#             try:
#                 # 获取源码中的 SNR 列表[cite: 2]
#                 base_snr_list = cfg_data["snr"]["snr"]
#                 # 左右端点各加 i
#                 new_snr = [round(float(val) + i, 2) for val in base_snr_list]
#                 cfg_data["snr"]["snr"] = new_snr
#                 current_snr = new_snr
#             except (KeyError, TypeError) as e:
#                 print(f"错误：{new_case_name} 的 CFG JSON SNR修改失败")
            
#             with open(cfg_path, 'w', encoding='utf-8') as f:
#                 json.dump(cfg_data, f, indent=4)

#         print(f"已完成 {new_case_name}: mcs_index={i}, qam_mod_order={target_qam}, SNR={current_snr}")

#     print("\n所有操作已严谨执行完毕！")

# if __name__ == "__main__":
#     main()




import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter
import math

 
SERVERS = {
    '174': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'test1234'},
    '175': {'host': '192.168.90.175', 'user': 'mengyao.li', 'pwd': 'test1234'},
    '176': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'test1234'}
}

BASE_PATH = '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/case_0326/'
FILE_NAME = 'sfn0_slot8_ul_result.mat'
OUTPUT_FILE = 'C:/Users/tools/Desktop/Simulation_Detailed_Matrix_0326.xlsx'

def get_mapping_data(mcs_index):
  
    if 0 <= mcs_index <= 4: return 2
    elif 5 <= mcs_index <= 10: return 4
    elif 11 <= mcs_index <= 19: return 6
    elif 20 <= mcs_index <= 27: return 8
    return 2

def get_target_server(case_idx):
    
    if 0 <= case_idx <= 6:   return '174'
    if 7 <= case_idx <= 13:  return '175'
    if 14 <= case_idx <= 23: return '176'
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
    for s_id in ['174', '175', '176']:
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