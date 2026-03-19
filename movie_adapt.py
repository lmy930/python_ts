import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import ReduceLROnPlateau
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from transformers import AutoTokenizer
import optuna
import os
import json

# --- 1. 环境配置 ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
plt.rcParams['font.sans-serif'] = ['KaiTi'] 
plt.rcParams['axes.unicode_minus'] = False 

# 全局参数记录
best_configs = {}

# --- 2. 数据处理 ---
def preprocess_text(s):
    if isinstance(s, bytes): s = s.decode('utf-8')
    s = re.sub(r"\\n", " ", str(s))
    s = re.sub(r"\\'", "'", s)
    s = s.strip().replace("b'",'').replace('b"','')
    return s.lower()

# 数据读取 (请确保路径正确)
train_path = r"C:\Users\tools\Desktop\lmy\movie\data\train.csv"
test_path = r"C:\Users\tools\Desktop\lmy\movie\data\test.csv"
df = pd.concat([pd.read_csv(train_path), pd.read_csv(test_path)]).reset_index(drop=True)
df['text'] = df['text'].apply(preprocess_text)

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
MAX_LEN = 200
X_full = tokenizer(list(df['text'].values), padding='max_length', truncation=True, max_length=MAX_LEN, return_tensors='pt')['input_ids']
Y_full = torch.LongTensor(df['label'].values)

# 划分比例：60% 训练, 20% 验证, 20% 测试
X_train_val, X_test, Y_train_val, Y_test = train_test_split(X_full, Y_full, test_size=0.2, random_state=42)
X_train, X_val, Y_train, Y_val = train_test_split(X_train_val, Y_train_val, test_size=0.25, random_state=42)

# --- 3. 核心模型架构 (全量复刻 14 种模式) ---

class PositionalEmbedding(nn.Module):
    """复刻 Keras 版 PositionalEmbedding: Token + Position"""
    def __init__(self, sequence_length, vocab_size, embed_dim):
        super().__init__()
        self.token_embeddings = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.position_embeddings = nn.Embedding(sequence_length, embed_dim)

    def forward(self, inputs):
        length = inputs.size(-1)
        positions = torch.arange(length, device=inputs.device).unsqueeze(0)
        return self.token_embeddings(inputs) + self.position_embeddings(positions)

class TransformerEncoderBlock(nn.Module):
    """标准 Transformer 编码器单元"""
    def __init__(self, embed_dim, dense_dim, num_heads, dropout):
        super().__init__()
        self.attention = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True, dropout=dropout)
        self.dense_proj = nn.Sequential(
            nn.Linear(embed_dim, dense_dim), nn.ReLU(), nn.Linear(dense_dim, embed_dim)
        )
        self.layernorm_1 = nn.LayerNorm(embed_dim)
        self.layernorm_2 = nn.LayerNorm(embed_dim)

    def forward(self, x, mask=None):
        attn_out, _ = self.attention(x, x, x, key_padding_mask=mask)
        x = self.layernorm_1(x + attn_out)
        return self.layernorm_2(x + self.dense_proj(x))

class PyTorchNLPModel(nn.Module):
    def __init__(self, mode, vocab_size, embed_dim, hidden_dim, dropout):
        super().__init__()
        self.mode = mode
        # 建议1: 动态 Embedding (如果是位置编码模式则特殊处理)
        if mode == 'PositionalEmbedding+Transformer':
            self.embedding = PositionalEmbedding(MAX_LEN, vocab_size, embed_dim)
        else:
            self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)

        # --- 模型逻辑分支 (复刻 14 种) ---
        if mode == 'MLP':
            self.net = nn.Sequential(nn.Flatten(), nn.Linear(MAX_LEN * embed_dim, hidden_dim))
        elif mode in ['RNN', 'LSTM', 'GRU']:
            self.rnn = getattr(nn, mode)(embed_dim, hidden_dim, batch_first=True)
        elif mode == 'CNN':
            self.conv = nn.Conv1d(embed_dim, 32, kernel_size=3, padding=1)
            self.fc = nn.Linear(32 * (MAX_LEN // 2), hidden_dim) # 对应原代码 MaxPool1d(2)
        elif mode == 'CNN+LSTM':
            self.conv = nn.Conv1d(embed_dim, 32, kernel_size=3, padding=1)
            self.rnn = nn.LSTM(32, hidden_dim, batch_first=True)
        elif mode == 'BiLSTM':
            self.rnn = nn.LSTM(embed_dim, hidden_dim//2, batch_first=True, bidirectional=True)
        elif mode == 'TextCNN':
            self.convs = nn.ModuleList([nn.Conv1d(embed_dim, 32, k, padding=k//2) for k in [3, 4, 5]])
            self.fc = nn.Linear(32 * 3, hidden_dim)
        
        # 注意力 & Transformer 类
        elif 'Attention' in mode or 'Transformer' in mode:
            num_h = 1 if mode == 'Attention' else 8 if mode == 'MultiHeadAttention' else 4
            self.mha = nn.MultiheadAttention(embed_dim, num_heads=num_h, batch_first=True)
            if 'BiLSTM' in mode:
                self.rnn_ext = nn.LSTM(embed_dim, hidden_dim//2, batch_first=True, bidirectional=True)
            if 'BiGRU' in mode:
                self.rnn_pre = nn.GRU(embed_dim, 32, batch_first=True, bidirectional=True)
                self.rnn_post = nn.GRU(64 if 'BiGRU' in mode else embed_dim, 32, batch_first=True, bidirectional=True)
            if 'Transformer' in mode:
                self.transformer = TransformerEncoderBlock(embed_dim, 32, 4, dropout)

        self.dropout = nn.Dropout(dropout)
        
        # 特征维度适配器
        feat_dim = hidden_dim
        if 'Bi' in mode: feat_dim = hidden_dim if 'GRU' not in mode else 64
        if mode in ['Attention', 'MultiHeadAttention', 'Transformer', 'PositionalEmbedding+Transformer']:
            feat_dim = embed_dim
        self.classifier = nn.Linear(feat_dim, 2)

    def forward(self, x):
        # 建议2: Attention Masking (True 表示被遮盖)
        mask = (x == 0) 
        x = self.embedding(x)
        
        if self.mode == 'MLP': 
            x = self.net(x)
        elif self.mode in ['RNN', 'LSTM', 'GRU', 'BiLSTM']:
            _, h = self.rnn(x)
            x = h[-1] if not isinstance(h, tuple) else h[0][-1]
            if 'Bi' in self.mode: 
                x = torch.cat((h[0][-2], h[0][-1]), dim=1) if isinstance(h, tuple) else torch.cat((h[-2], h[-1]), dim=1)
        elif self.mode == 'CNN':
            x = torch.relu(self.conv(x.permute(0, 2, 1)))
            x = nn.MaxPool1d(2)(x).flatten(1)
            x = self.fc(x)
        elif self.mode == 'CNN+LSTM':
            x = torch.relu(self.conv(x.permute(0, 2, 1))).permute(0, 2, 1)
            _, (h, _) = self.rnn(x); x = h[-1]
        elif self.mode == 'TextCNN':
            x_inv = x.permute(0, 2, 1)
            x = torch.cat([torch.max(torch.relu(c(x_inv)), dim=2)[0] for c in self.convs], dim=1)
            x = self.fc(x)
        elif 'Attention' in self.mode or 'Transformer' in self.mode:
            if 'BiGRU' in self.mode: x, _ = self.rnn_pre(x)
            
            # 使用 Mask
            x = self.transformer(x, mask=mask) if 'Transformer' in self.mode else self.mha(x, x, x, key_padding_mask=mask)[0]
            
            if 'BiLSTM' in self.mode:
                _, (h, _) = self.rnn_ext(x); x = torch.cat((h[-2], h[-1]), dim=1)
            elif 'BiGRU' in self.mode:
                _, h = self.rnn_post(x); x = torch.cat((h[-2], h[-1]), dim=1)
            else:
                x = torch.mean(x, dim=1)  
            
        return self.classifier(self.dropout(x))

# --- 4. 优化与早停逻辑 (建议3) ---

def objective(trial, mode):
    # 动态参数搜索
    e_dim = trial.suggest_categorical("embed_dim", [128, 256, 512]) # 必须是4的倍数适配MHA
    h_dim = trial.suggest_categorical("hidden_dim", [128, 256])
    lr = trial.suggest_float("lr", 1e-4, 1e-3, log=True)
    drp = trial.suggest_float("dropout", 0.2, 0.5)

    model = PyTorchNLPModel(mode, tokenizer.vocab_size, e_dim, h_dim, drp).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = ReduceLROnPlateau(optimizer, 'max', patience=2, factor=0.5)
    criterion = nn.CrossEntropyLoss()
    
    train_loader = DataLoader(TensorDataset(X_train, Y_train), batch_size=64, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_val, Y_val), batch_size=64)

    best_v_acc = 0
    patience, counter = 5, 0 # 建议3: 早停机制

    for epoch in range(20): # 增加训练上限
        model.train()
        for tx, ty in train_loader:
            tx, ty = tx.to(device), ty.to(device)
            optimizer.zero_grad(); criterion(model(tx), ty).backward(); optimizer.step()
        
        model.eval()
        v_acc = 0
        with torch.no_grad():
            for tx, ty in val_loader:
                tx, ty = tx.to(device), ty.to(device)
                v_acc += (model(tx).argmax(1) == ty).sum().item()
        
        acc = v_acc / len(X_val)
        scheduler.step(acc)
        trial.report(acc, epoch)
        if trial.should_prune(): raise optuna.exceptions.TrialPruned()

        if acc > best_v_acc:
            best_v_acc = acc
            torch.save(model.state_dict(), f"temp_{mode}.pth")
            counter = 0
        else:
            counter += 1
        if counter >= patience: break

    return best_v_acc

# --- 5. 执行自动化全量流程 ---

modes = [
     'CNN', 'RNN', 'LSTM', 'GRU', 'BiLSTM', 'CNN+LSTM', 'TextCNN', 
    'Attention', 'MultiHeadAttention', 'Attention+BiLSTM', 'BiGRU+Attention', 
    'Transformer', 'PositionalEmbedding+Transformer'
]

df_eval = pd.DataFrame(columns=['Accuracy', 'F1_score', 'Best_Params'])

for m in modes:
    print(f"\n🚀 开始贝叶斯优化 - 模型: {m}")
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda t: objective(t, m), n_trials=5) # 实际运行可增加次数
    
    bp = study.best_params
    best_configs[m] = bp 
    
    # 使用最佳参数重新初始化并加载权重
    final_model = PyTorchNLPModel(m, tokenizer.vocab_size, bp['embed_dim'], bp['hidden_dim'], bp['dropout']).to(device)
    final_model.load_state_dict(torch.load(f"temp_{m}.pth"))
    final_model.eval()
    
    y_true, y_pred = [], []
    with torch.no_grad():
        for i in range(0, len(X_test), 64):
            bx = X_test[i:i+64].to(device)
            y_true.extend(Y_test[i:i+64].numpy())
            y_pred.extend(final_model(bx).argmax(1).cpu().numpy())
    
    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    df_eval.loc[m] = [report['accuracy'], report['weighted avg']['f1-score'], str(bp)]
    
    # 保存最终模型
    os.rename(f"temp_{m}.pth", f"final_best_{m}.pth")

# --- 6. 结果展示 ---
print("\n" + "="*60)
print(df_eval.sort_values(by='Accuracy', ascending=False))

def final_predict(text, mode):
    if mode not in best_configs: return "模型未训练"
    bp = best_configs[mode]
    model = PyTorchNLPModel(mode, tokenizer.vocab_size, bp['embed_dim'], bp['hidden_dim'], bp['dropout']).to(device)
    model.load_state_dict(torch.load(f"final_best_{mode}.pth"))
    model.eval()
    tokens = tokenizer(text, padding='max_length', truncation=True, max_length=MAX_LEN, return_tensors='pt')['input_ids']
    with torch.no_grad():
        pred = model(tokens.to(device)).argmax(1).item()
    return "正面" if pred == 1 else "负面"

print(f"最终预测示例 (Transformer): {final_predict('An absolute masterpiece!', 'Transformer')}")