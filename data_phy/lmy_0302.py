#比较adapt mrc irc ，以验证adapt算法的性能
import paramiko
import pandas as pd
import io
from scipy.io import loadmat
import numpy as np

# 1. 服务器基础配置
SERVERS = {
    '175': {
        'host': '192.168.90.175', 
        'user': 'mengyao.li', 
        'pwd': 'test1234', 
        'base_path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'
    },
    '177': {
        'host': '192.168.90.177', 
        'user': 'mengyao.li', 
        'pwd': 'test1234', 
        'base_path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'
    }
}

# 2. 
SOURCES = [
    ('175', 'simu_case', 'adapt'),
    ('177', 'simu_case', 'irc'),
    ('177', 'simu_case_mrc', 'mrc')
]

# 3. 
CASES = [
    ('case001', 'case001 (TDLA30-10 + 1T2R)'),
    ('case003', 'case003 (TDLA30-10 + 1T2R)'),
    ('case005', 'case005 (TDLA30-10 + 1T2R)'),
    ('case007', 'case007 (TDLA30-10 + 1T2R)')
]

def parse_mat_structure(remote_file_content):
    """提取 SNR 和 Throughput"""
    try:
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
    except:
        return None, None

def main():
    output_path = 'C:/Users/tools/Desktop/PUSCH_ThreeWay_Compare.xlsx'
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Comparison_Summary')
    
    # 格式定义
    case_title_fmt = workbook.add_format({'bold': True, 'bg_color': "#D9E1F2", 'border': 1})
    border_fmt = workbook.add_format({'border': 1, 'align': 'center'})
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#F2F2F2'})

    current_row = 0
    all_charts = []

    # 建立 SSH 连接池
    ssh_conns = {}
    for sid in SERVERS:
        conf = SERVERS[sid]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(conf['host'], username=conf['user'], password=conf['pwd'])
        ssh_conns[sid] = ssh

    for idx, (case_folder, case_desc) in enumerate(CASES):
        print(f"正在处理 {case_folder}...")
        
        worksheet.merge_range(current_row, 0, current_row, 9, f"Case {idx+1}: {case_desc}", case_title_fmt)
        current_row += 1
        
        case_results = []
        common_snrs = None
        
        # 初始化
        min_snr, max_snr = float('inf'), float('-inf')
        min_thp, max_thp = float('inf'), float('-inf')

        for sid, folder, label in SOURCES:
            conf = SERVERS[sid]

            full_path = f"{conf['base_path']}{folder}/{case_folder}/sfn366_slot18_ul_result.mat"
            
            try:
                sftp = ssh_conns[sid].open_sftp()
                with sftp.open(full_path, 'rb') as f:
                    snr, thp = parse_mat_structure(f.read())
                sftp.close()
                
                if snr is not None and len(snr) > 0:
                    sort_idx = np.argsort(snr)
                    s_sorted, t_sorted = snr[sort_idx], thp[sort_idx]
                    
                    min_snr = min(min_snr, np.min(s_sorted))
                    max_snr = max(max_snr, np.max(s_sorted))
                    min_thp = min(min_thp, np.min(t_sorted))
                    max_thp = max(max_thp, np.max(t_sorted))
                    
                    case_results.append({'label': label, 'snr': s_sorted, 'thp': t_sorted})
                    
                    if common_snrs is None or len(s_sorted) > len(common_snrs):
                        common_snrs = s_sorted
            except Exception as e:
                print(f"  -> {label} 读取失败: {e}")

        if not case_results:
            current_row += 2
            continue

        # 写入数据表格
        worksheet.write(current_row, 0, "SNR (dB)", header_fmt)
        for i, val in enumerate(common_snrs):
            worksheet.write(current_row, i + 1, val, border_fmt)
        
        for r_idx, res in enumerate(case_results):
            row = current_row + 1 + r_idx
            worksheet.write(row, 0, res['label'], border_fmt)
            for i, val in enumerate(res['thp']):
                worksheet.write(row, i + 1, val, border_fmt)

        # 创建图表
        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
        colors = ['#4F81BD', '#C0504D', '#9BBB59']
        
        for r_idx, res in enumerate(case_results):
            data_row = current_row + 1 + r_idx
            num_points = len(res['snr'])
            
            if num_points > 0:
                chart.add_series({
                    'name':       ['Comparison_Summary', data_row, 0],
                    'categories': ['Comparison_Summary', current_row, 1, current_row, num_points],
                    'values':     ['Comparison_Summary', data_row, 1, data_row, num_points],
                    'line':       {'color': colors[r_idx % len(colors)]},
                    'marker':     {'type': 'circle', 'size': 4}
                })

        # 设置动态坐标轴范围
        chart.set_title({'name': f'{case_folder}'})
        chart.set_x_axis({
            'name': 'SNR (dB)', 
            'min': min_snr, 
            'max': max_snr,
            'major_unit': 0.5, 
            'major_gridlines': {'visible': True}
        })
        chart.set_y_axis({
            'name': 'Throughput', 
            'min': max(0, min_thp), 
            'max': min(1.0, max_thp), 
            'major_gridlines': {'visible': True}
        })
        
        chart.set_size({'width': 600, 'height': 400})
        all_charts.append(chart)

        current_row += (len(case_results) + 2)

    # 图表排版
    chart_start_row = current_row + 2
    for i, chart in enumerate(all_charts):
        worksheet.insert_chart(chart_start_row + (i * 21), 1, chart)

    for ssh in ssh_conns.values():
        ssh.close()
    
    writer.close()
    print(f"处理完成！文件已保存至: {output_path}")

if __name__ == "__main__":
    main()