# import gymnasium as gym
# import torch
# import torch.nn as nn
# import torch.optim as optim
# import numpy as np
# from collections import deque
# import random

# class DQN(nn.Module):
#     def __init__(self, state_dim, action_dim):
#         super().__init__()
#         self.net = nn.Sequential(
#             nn.Linear(state_dim, 128),
#             nn.ReLU(),
#             nn.Linear(128, 128),
#             nn.ReLU(),
#             nn.Linear(128, action_dim)
#         )
    
#     def forward(self, x):
#         return self.net(x)

# # 超参
# env = gym.make("CartPole-v1")   # 也可换成 "LunarLander-v2"
# state_dim = env.observation_space.shape[0]
# action_dim = env.action_space.n

# policy_net = DQN(state_dim, action_dim)
# target_net = DQN(state_dim, action_dim)
# target_net.load_state_dict(policy_net.state_dict())
# optimizer = optim.Adam(policy_net.parameters(), lr=1e-3)

# replay_buffer = deque(maxlen=10000)
# batch_size = 64
# gamma = 0.99
# epsilon = 1.0
# epsilon_min = 0.01
# epsilon_decay = 0.995
# update_target_every = 100
# steps = 0

# for episode in range(1000):
#     state, _ = env.reset()
#     state = torch.FloatTensor(state).unsqueeze(0)
#     total_reward = 0
#     done = False
    
#     while not done:
#         steps += 1
#         # ε-greedy 探索
#         if random.random() < epsilon:
#             action = env.action_space.sample()
#         else:
#             with torch.no_grad():
#                 q_values = policy_net(state)
#                 action = q_values.argmax().item()
        
#         next_state, reward, terminated, truncated, _ = env.step(action)
#         done = terminated or truncated
#         next_state = torch.FloatTensor(next_state).unsqueeze(0)
        
#         replay_buffer.append((state, action, reward, next_state, done))
#         state = next_state
#         total_reward += reward
        
#         # 训练
#         if len(replay_buffer) > batch_size:
#             batch = random.sample(replay_buffer, batch_size)
#             states, actions, rewards, next_states, dones = zip(*batch)
            
#             states = torch.cat(states)
#             next_states = torch.cat(next_states)
#             actions = torch.LongTensor(actions).unsqueeze(1)
#             rewards = torch.FloatTensor(rewards)
#             dones = torch.FloatTensor(dones)
            
#             q_values = policy_net(states).gather(1, actions).squeeze(1)
#             with torch.no_grad():
#                 next_q = target_net(next_states).max(1)[0]
#                 targets = rewards + gamma * next_q * (1 - dones)
            
#             loss = nn.MSELoss()(q_values, targets)
#             optimizer.zero_grad()
#             loss.backward()
#             optimizer.step()
        
#         # 更新 target 网络
#         if steps % update_target_every == 0:
#             target_net.load_state_dict(policy_net.state_dict())
    
#     epsilon = max(epsilon_min, epsilon * epsilon_decay)
    
#     if episode % 50 == 0:
#         print(f"Episode {episode}, Reward: {total_reward}, Epsilon: {epsilon:.3f}")

# env.close()

