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

# --- 1. 环境配置 ---
plt.rcParams['font.sans-serif'] = ['KaiTi'] 
plt.rcParams['axes.unicode_minus'] = False  
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- 2. 加载与清洗数据 ---
train_path = r"C:\Users\tools\Desktop\lmy\movie\data\train.csv"
test_path = r"C:\Users\tools\Desktop\lmy\movie\data\test.csv"

df_train = pd.read_csv(train_path)
df_test = pd.read_csv(test_path)
df = pd.concat([df_train, df_test]).reset_index(drop=True)

def preprocess_text(s):
    if isinstance(s, bytes): s = s.decode('utf-8')
    s = re.sub(r"\\n", " ", str(s))
    s = re.sub(r"\\'", "'", s)
    s = s.strip().replace("b'",'').replace('b"','')
    return s.lower()

df['text'] = df['text'].apply(preprocess_text)

# --- 3. Hugging Face Tokenizer ---
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
X_full = tokenizer(list(df['text'].values), padding='max_length', truncation=True, max_length=200, return_tensors='pt')['input_ids']
Y_full = torch.LongTensor(df['label'].values)

# 三路划分：60% 训练, 20% 验证 (调优), 20% 测试 (最终对比)
X_train_val, X_test, Y_train_val, Y_test = train_test_split(X_full, Y_full, test_size=0.2, shuffle=True, random_state=42)
X_train, X_val, Y_train, Y_val = train_test_split(X_train_val, Y_train_val, test_size=0.25, shuffle=True, random_state=42)

# --- 4. 统一网络架构 ---
class TransformerBlock(nn.Module):
    def __init__(self, embed_dim, num_heads, dense_dim):
        super().__init__()
        self.attention = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.dense_proj = nn.Sequential(nn.Linear(embed_dim, dense_dim), nn.ReLU(), nn.Linear(dense_dim, embed_dim))
        self.layernorm_1 = nn.LayerNorm(embed_dim)
        self.layernorm_2 = nn.LayerNorm(embed_dim)
    def forward(self, x):
        attn_out, _ = self.attention(x, x, x)
        x = self.layernorm_1(x + attn_out)
        return self.layernorm_2(x + self.dense_proj(x))

class PyTorchNLPModel(nn.Module):
    def __init__(self, mode, vocab_size, embed_dim, hidden_dim, dropout, max_len=200):
        super().__init__()
        self.mode = mode
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        
        # 核心逻辑分支
        if mode == 'MLP':
            self.net = nn.Sequential(nn.Flatten(), nn.Linear(max_len * embed_dim, hidden_dim))
        elif mode in ['RNN', 'LSTM', 'GRU']:
            self.rnn = getattr(nn, mode)(embed_dim, hidden_dim, batch_first=True)
        elif mode == 'CNN':
            self.conv = nn.Conv1d(embed_dim, 32, kernel_size=3, padding=1)
            self.fc = nn.Linear(32 * (max_len // 2), hidden_dim)
        elif mode == 'BiLSTM':
            self.rnn = nn.LSTM(embed_dim, hidden_dim//2, batch_first=True, bidirectional=True)
        elif 'Attention' in mode or 'Transformer' in mode:
            self.mha = nn.MultiheadAttention(embed_dim, num_heads=4, batch_first=True)
            if 'Bi' in mode:
                cell = nn.LSTM if 'LSTM' in mode else nn.GRU
                self.rnn_post = cell(embed_dim, hidden_dim//2, batch_first=True, bidirectional=True)
            if 'Transformer' in mode:
                self.transformer = TransformerBlock(embed_dim, 4, hidden_dim)

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_dim if 'Attention' not in mode and 'Transformer' not in mode else embed_dim, 2)

    def forward(self, x):
        x = self.embedding(x)
        if self.mode == 'MLP': x = self.net(x)
        elif self.mode in ['RNN', 'LSTM', 'GRU', 'BiLSTM']:
            _, h = self.rnn(x)
            x = h[-1] if not isinstance(h, tuple) else h[0][-1]
            if 'Bi' in self.mode: 
                x = torch.cat((h[0][-2], h[0][-1]), dim=1) if isinstance(h, tuple) else torch.cat((h[-2], h[-1]), dim=1)
        elif self.mode == 'CNN':
            x = torch.relu(self.conv(x.permute(0, 2, 1)))
            x = nn.MaxPool1d(2)(x).flatten(1)
            x = self.fc(x)
        elif 'Attention' in self.mode or 'Transformer' in self.mode:
            x = self.transformer(x) if 'Transformer' in self.mode else self.mha(x, x, x)[0]
            if 'Bi' in self.mode:
                _, h = self.rnn_post(x)
                x = torch.cat((h[0][-2], h[0][-1]), dim=1) if isinstance(h, tuple) else torch.cat((h[-2], h[-1]), dim=1)
            else: x = torch.mean(x, dim=1)
        return self.classifier(self.dropout(x))

# --- 5. Optuna 贝叶斯优化目标函数 ---
def objective(trial, mode):
    # 贝叶斯搜索空间
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    hidden_dim = trial.suggest_categorical("hidden_dim", [64, 128])
    dropout = trial.suggest_float("dropout", 0.2, 0.5)
    
    model = PyTorchNLPModel(mode, tokenizer.vocab_size, 128, hidden_dim, dropout).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = ReduceLROnPlateau(optimizer, 'max', patience=1, factor=0.5)
    criterion = nn.CrossEntropyLoss()
    
    train_loader = DataLoader(TensorDataset(X_train, Y_train), batch_size=64, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_val, Y_val), batch_size=64)

    best_v_acc = 0
    for epoch in range(5): # 每个组合试跑5轮
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
        
        # 剪枝
        trial.report(acc, epoch)
        if trial.should_prune(): raise optuna.exceptions.TrialPruned()
        
        if acc > best_v_acc:
            best_v_acc = acc
            torch.save(model.state_dict(), f"temp_best_{mode}.pth")
            
    return best_v_acc

# --- 6. 执行全自动化流程 ---
modes = ['MLP', 'CNN', 'GRU', 'BiLSTM', 'Transformer']
df_eval = pd.DataFrame(columns=['Accuracy', 'F1_score', 'Best_Params'])

for m in modes:
    print(f"\n✨ 正在进行贝叶斯优化: {m}")
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, m), n_trials=5) 
    
    # 提取最优参数并加载最佳模型
    best_params = study.best_params
    print(f"🏆 {m} 最佳参数: {best_params}")
    
    # 在测试集上进行最终评估
    final_model = PyTorchNLPModel(m, tokenizer.vocab_size, 128, best_params['hidden_dim'], best_params['dropout']).to(device)
    final_model.load_state_dict(torch.load(f"temp_best_{m}.pth"))
    final_model.eval()
    
    y_true, y_pred = [], []
    with torch.no_grad():
        for i in range(0, len(X_test), 64):
            batch_x = X_test[i:i+64].to(device)
            y_true.extend(Y_test[i:i+64].numpy())
            y_pred.extend(final_model(batch_x).argmax(1).cpu().numpy())
    
    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    df_eval.loc[m] = [report['accuracy'], report['weighted avg']['f1-score'], str(best_params)]
    
    # 重命名保存最终的最佳模型
    os.rename(f"temp_best_{m}.pth", f"final_best_{m}.pth")

# --- 7. 结果展示 ---
print("\n" + "="*50)
print("所有模型最终性能对比 (基于测试集):")
print(df_eval.sort_values(by='Accuracy', ascending=False))

plt.figure(figsize=(12, 6))
sns.barplot(x=df_eval.index, y=df_eval['Accuracy'].astype(float))
plt.title("各模型调优后准确率对比")
plt.xticks(rotation=45)
plt.show()

# 最终预测函数
def final_predict(text, mode):
    final_model = PyTorchNLPModel(mode, tokenizer.vocab_size, 128, 128, 0.3).to(device) # 需匹配保存时的维度
    final_model.load_state_dict(torch.load(f"final_best_{mode}.pth"))
    final_model.eval()
    tokens = tokenizer(text, padding='max_length', truncation=True, max_length=200, return_tensors='pt')['input_ids']
    with torch.no_grad():
        pred = final_model(tokens.to(device)).argmax(1).item()
    return "正面" if pred == 1 else "负面"

print(f"Transformer 最佳模型预测: {final_predict('This is the best movie I have ever seen!', 'Transformer')}")