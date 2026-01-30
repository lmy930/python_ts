# 整理不同服务器的csv结果，能够直接复制粘贴进 “原版” 的报告！
# 但需要服务器端先生成csv文件 (运行lmy0113)
import pandas as pd
import paramiko
import io

# 服务器配置保持不变
SERVERS = {
    '174': {'host': '192.168.90.174', 'user': 'mengyao.li', 'pwd': 'test1234', 'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'},
    '175': {'host': '192.168.90.175', 'user': 'mengyao.li', 'pwd': 'test1234', 'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'},
    '176': {'host': '192.168.90.176', 'user': 'mengyao.li', 'pwd': 'test1234', 'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'},
    '177': {'host': '192.168.90.177', 'user': 'mengyao.li', 'pwd': 'test1234', 'path': '/home/mengyao.li/Code/ts_nr_simulation/test_and_sim/ulsim/'}
}

def get_remote_df(server_key, file_name):
    config = SERVERS[server_key]
    full_path = f"{config['path']}{file_name}"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(config['host'], username=config['user'], password=config['pwd'])
        sftp = ssh.open_sftp()
        with sftp.open(full_path, 'r') as f:
            content = f.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content))
        sftp.close()
        ssh.close()
        return df
    except Exception as e:
        print(f"连接服务器 {server_key} 失败: {e}")
        return None

def process_segmented_vertical(df1, df2, id1, id2):
    
    snr_indices = df1[df1['RowType'] == 'SNR'].index.tolist()
    tp_indices = df1[df1['RowType'] == 'Throughput'].index.tolist()
    
    final_rows = []
    
    for s_idx, t_idx in zip(snr_indices, tp_indices):
        
        snr_row = df1.iloc[s_idx].to_dict()
        snr_row['RowType'] = 'SNR'
        final_rows.append(snr_row)
        
        tp1_row = df1.iloc[t_idx].to_dict()
        tp1_row['RowType'] = f'TP_S{id1}'
        final_rows.append(tp1_row)
        
        try:
            tp2_row = df2.iloc[t_idx].to_dict()
            tp2_row['RowType'] = f'TP_S{id2}'
            final_rows.append(tp2_row)
        except IndexError:
            print(f"警告：服务器 {id2} 的文件行数不足。")
            
        # 添加一个空行或分隔符
        separator = {k: '' for k in snr_row.keys()}
        final_rows.append(separator)

    return pd.DataFrame(final_rows)

def merge_by_group(id1, file1, id2, file2):
    """
    主封装函数
    """
    df1 = get_remote_df(id1, file1)
    df2 = get_remote_df(id2, file2)
    
    if df1 is not None and df2 is not None:
        result = process_segmented_vertical(df1, df2, id1, id2)
        return result
    else:
        return None

if __name__ == "__main__":
    
    res = merge_by_group('176', '0122_sedft_mrc_new.csv', '177', '0122_acc100_mrc_new.csv')
    
    if res is not None:
        cols = ['RowType'] + [c for c in res.columns if c != 'RowType']
        res = res[cols]
        
        print(res.to_string(index=False))
        res.to_csv("C:/Users/tools/Desktop/PUSCH_Comparison2.csv", index=False)