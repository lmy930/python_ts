# import paramiko
# import pd
# import io
# from scipy.io import loadmat
# import numpy as np
# import xlsxwriter
# import os

# # --- 1. 配置信息 ---
# SERVERS = {
#     '174': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'test1234'},
#     '175': {'host': '192.168.90.175', 'user': 'mengyao.li', 'pwd': 'test1234'},
#     '176': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'test1234'}, 
#     '177': {'host': '192.168.90.177', 'user': 'mengyao.li', 'pwd': 'test1234'}  
# }

# BASE_PATH = '/home/mengyao.li/Code/ts_nr_simulation/satellite/'
# OUTPUT_FILE = 'C:/Users/tools/Desktop/Simulation_Results.xlsx'

# def parse_mat_bler(remote_file_content):
#     """提取结构体中的bler两列数据: 第一列bler, 第二列snr"""
#     try:
#         data = loadmat(io.BytesIO(remote_file_content), squeeze_me=True, struct_as_record=False)
#         target_struct = None
#         for key in data.keys():
#             if not key.startswith('__'):
#                 target_struct = data[key]
#                 break
        
#         if target_struct is None or not hasattr(target_struct, 'bler'):
#             return None
        
#         bler_data = np.array(target_struct.bler)
#         if bler_data.ndim != 2 or bler_data.shape[1] < 2:
#             return None
            
#         return {
#             'bler': bler_data[:, 0],
#             'snr': bler_data[:, 1]
#         }
#     except Exception as e:
#         print(f"  [Error] 解析失败: {e}")
#         return None

# def process_server(ssh_client, sftp_client, workbook, sheet_name):
#     """处理单个服务器的所有数据并在Sheet底部并排生成图片"""
#     worksheet = workbook.add_worksheet(sheet_name)
    
#     # --- 格式定义 ---
#     # 标题行格式
#     header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'align': 'center'})
#     # SNR格式：保留两位小数
#     snr_data_fmt = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '0.00'})
#     # BLER格式：科学计数法
#     bler_data_fmt = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '0.000E+00'})
#     # Case名称格式
#     title_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#BDD7EE', 'border': 1})

#     # 设置列宽，防止数据被遮挡
#     worksheet.set_column('A:A', 20)  # 第一列（名称列）宽度设为20
#     worksheet.set_column('B:Z', 12)  # 数据列宽度设为12

#     try:
#         files = [f for f in sftp_client.listdir(BASE_PATH) if f.startswith('case') and f.endswith('.mat')]
#         files.sort()
#     except Exception as e:
#         print(f"  [Error] 无法访问路径 {BASE_PATH}: {e}")
#         return

#     current_row = 0
#     chart_info_list = [] 
#     max_cols_used = 0 # 用于记录最长的数据列，以便后续微调列宽

#     # --- 第一步：写入所有数据表格 ---
#     for file_name in files:
#         full_path = os.path.join(BASE_PATH, file_name)
#         try:
#             with sftp_client.open(full_path, 'rb') as f:
#                 res = parse_mat_bler(f.read())
            
#             if res is None: continue

#             # 写入标题 (Case文件名)
#             worksheet.write(current_row, 0, file_name, title_fmt)
            
#             # 写入 SNR 行 (第一行数据)
#             worksheet.write(current_row + 1, 0, "SNR (dB)", header_fmt)
#             for i, val in enumerate(res['snr']):
#                 worksheet.write(current_row + 1, i + 1, val, snr_data_fmt)
            
#             # 写入 BLER 行 (第二行数据)
#             worksheet.write(current_row + 2, 0, "BLER", header_fmt)
#             for i, val in enumerate(res['bler']):
#                 worksheet.write(current_row + 2, i + 1, val, bler_data_fmt)

#             # 记录绘图信息
#             data_len = len(res['snr'])
#             chart_info_list.append({
#                 'name': file_name,
#                 'row_idx': current_row,
#                 'data_len': data_len
#             })
#             max_cols_used = max(max_cols_used, data_len)

#             current_row += 5 # 表格间留白

#         except Exception as e:
#             print(f"    处理 {file_name} 出错: {e}")

#     # --- 第二步：在表格下方统一绘制图片 (一排两个) ---
#     chart_start_row = current_row + 2 
    
#     for idx, info in enumerate(chart_info_list):
#         chart = workbook.add_chart({'type': 'line'})
        
#         chart.add_series({
#             'name':       f"BLER - {info['name']}",
#             'categories': [sheet_name, info['row_idx'] + 1, 1, info['row_idx'] + 1, info['data_len']],
#             'values':     [sheet_name, info['row_idx'] + 2, 1, info['row_idx'] + 2, info['data_len']],
#             'line':       {'color': '#C00000', 'width': 1.5},
#             'marker':     {'type': 'circle', 'size': 4, 'border': {'color': '#C00000'}, 'fill': {'color': 'white'}},
#         })
        
#         chart.set_title({'name': f"Performance: {info['name']}"})
#         chart.set_x_axis({'name': 'SNR (dB)', 'major_gridlines': {'visible': True}})
#         chart.set_y_axis({
#             'name': 'BLER', 
#             'log_base': 10, 
#             'major_gridlines': {'visible': True},
#             'num_format': '0.E+00'
#         })
#         chart.set_size({'width': 480, 'height': 320})
#         chart.set_legend({'none': True})

#         # 计算位置：一排2个
#         col_pos = (idx % 2) * 8  
#         row_pos = chart_start_row + (idx // 2) * 18 # 图表垂直间距稍大一点
        
#         worksheet.insert_chart(row_pos, col_pos, chart)

# def main():
#     workbook = xlsxwriter.Workbook(OUTPUT_FILE)
    
#     for s_name, config in SERVERS.items():
#         print(f"正在连接服务器: {s_name} ({config['host']})...")
#         try:
#             ssh = paramiko.SSHClient()
#             ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#             ssh.connect(config['host'], username=config['user'], password=config['pwd'], timeout=10)
#             sftp = ssh.open_sftp()
            
#             process_server(ssh, sftp, workbook, s_name)
            
#             sftp.close()
#             ssh.close()
#             print(f"完成服务器 {s_name} 的统计。")
#         except Exception as e:
#             print(f"无法连接到服务器 {s_name}: {e}")

#     workbook.close()
#     print(f"\n全部处理完成！\n结果文件已保存: {OUTPUT_FILE}")

# if __name__ == "__main__":
#     main()


#终版
import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np
import xlsxwriter
import os


SERVERS = {
    '174-4': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'test1234'},
    '175-6': {'host': '192.168.90.175', 'user': 'mengyao.li', 'pwd': 'test1234'},
    '176-1': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'test1234'}, 
    '177-2': {'host': '192.168.90.177', 'user': 'mengyao.li', 'pwd': 'test1234'}  
}

BASE_PATH = '/home/mengyao.li/Code/ts_nr_simulation/satellite/'
OUTPUT_FILE = 'C:/Users/tools/Desktop/Simulation_Results.xlsx'

def parse_mat_bler(remote_file_content):
    
    try:
        data = loadmat(io.BytesIO(remote_file_content), squeeze_me=True, struct_as_record=False)
        target_struct = None
        for key in data.keys():
            if not key.startswith('__'):
                target_struct = data[key]
                break
        
        if target_struct is None or not hasattr(target_struct, 'bler'):
            return None
        
        bler_data = np.array(target_struct.bler)
        if bler_data.ndim != 2 or bler_data.shape[1] < 2:
            return None
            
        return {
            'bler': bler_data[:, 0],
            'snr': bler_data[:, 1]
        }
    except Exception as e:
        print(f"  [Error] 解析失败: {e}")
        return None

def process_server(ssh_client, sftp_client, workbook, sheet_name):
   
    worksheet = workbook.add_worksheet(sheet_name)
    
    
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'align': 'center'})
    snr_data_fmt = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '0.00'})
    bler_data_fmt = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '0.000E+00'})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#BDD7EE', 'border': 1})

    # 设置列宽
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:Z', 12)

    try:
        files = [f for f in sftp_client.listdir(BASE_PATH) if f.startswith('case') and f.endswith('.mat')]
        files.sort()
    except Exception as e:
        print(f"  [Error] 无法访问路径 {BASE_PATH}: {e}")
        return

    current_row = 0
    chart_info_list = [] 

    
    for file_name in files:
        full_path = os.path.join(BASE_PATH, file_name)
        try:
            with sftp_client.open(full_path, 'rb') as f:
                res = parse_mat_bler(f.read())
            
            if res is None: continue

            # 写入标题
            worksheet.write(current_row, 0, file_name, title_fmt)
            
            # 写入 SNR 行
            worksheet.write(current_row + 1, 0, "SNR (dB)", header_fmt)
            for i, val in enumerate(res['snr']):
                worksheet.write(current_row + 1, i + 1, val, snr_data_fmt)
            
            # 写入 BLER 行
            worksheet.write(current_row + 2, 0, "BLER", header_fmt)
            for i, val in enumerate(res['bler']):
                worksheet.write(current_row + 2, i + 1, val, bler_data_fmt)

            chart_info_list.append({
                'name': file_name,
                'row_idx': current_row,
                'data_len': len(res['snr'])
            })

            current_row += 5 # 表格间留白

        except Exception as e:
            print(f"    处理 {file_name} 出错: {e}")

    
    chart_start_row = current_row + 2 
    
    for idx, info in enumerate(chart_info_list):
        
        chart = workbook.add_chart({'type': 'line'})
        
        chart.add_series({
            'name':       f"BLER - {info['name']}",
            'categories': [sheet_name, info['row_idx'] + 1, 1, info['row_idx'] + 1, info['data_len']],
            'values':     [sheet_name, info['row_idx'] + 2, 1, info['row_idx'] + 2, info['data_len']],
            'line':       {'color': '#C00000', 'width': 1.5},
            'marker':     {'type': 'circle', 'size': 4, 'border': {'color': '#C00000'}, 'fill': {'color': 'white'}},
        })
        
        chart.set_title({'name':f"{info['name']}"})
        
       
        chart.set_x_axis({
            'name': 'SNR (dB)', 
            'major_gridlines': {'visible': True},
            'label_position': 'low',   
            'crossing': 'min'          
        })
        
       
        chart.set_y_axis({
            'name': 'BLER', 
            'major_gridlines': {'visible': True},
            'num_format': '0.00E+00',
            'min': 0,                  
            'crossing': 'min'
        })
        
        chart.set_size({'width': 480, 'height': 320})
        chart.set_legend({'none': True})

        
        col_pos = (idx % 2) * 8  
        row_pos = chart_start_row + (idx // 2) * 18
        
        worksheet.insert_chart(row_pos, col_pos, chart)

def main():
    workbook = xlsxwriter.Workbook(OUTPUT_FILE)
    
    for s_name, config in SERVERS.items():
        print(f"正在连接服务器: {s_name} ({config['host']})...")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(config['host'], username=config['user'], password=config['pwd'], timeout=10)
            sftp = ssh.open_sftp()
            
            process_server(ssh, sftp, workbook, s_name)
            
            sftp.close()
            ssh.close()
            print(f"完成服务器 {s_name} 的统计。")
        except Exception as e:
            print(f"无法连接到服务器 {s_name}: {e}")

    workbook.close()
    print(f"\n全部处理完成！\n结果文件已保存: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()