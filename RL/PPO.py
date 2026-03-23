
import gymnasium as gym
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.distributions import Categorical, Normal

class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, continuous=False):
        super().__init__()
        self.continuous = continuous
        self.fc = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh()
        )
        if continuous:
            self.mu = nn.Linear(64, action_dim)
            self.log_std = nn.Parameter(torch.zeros(action_dim))
        else:
            self.logits = nn.Linear(64, action_dim)
    
    def forward(self, x):
        x = self.fc(x)
        if self.continuous:
            mu = torch.tanh(self.mu(x)) * 2  # 假设动作范围[-2,2]，可改
            std = torch.exp(self.log_std)
            return mu, std
        else:
            return self.logits(x)

class Critic(nn.Module):
    def __init__(self, state_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, 1)
        )
    def forward(self, x):
        return self.net(x)

# ====================== 主训练循环 ======================
env = gym.make("CartPole-v1")          # 也可换 "Pendulum-v1", "LunarLanderContinuous-v2"
state_dim = env.observation_space.shape[0]
continuous = isinstance(env.action_space, gym.spaces.Box)
action_dim = env.action_space.shape[0] if continuous else env.action_space.n

actor = Actor(state_dim, action_dim, continuous)
critic = Critic(state_dim)
actor_optim = optim.Adam(actor.parameters(), lr=3e-4)
critic_optim = optim.Adam(critic.parameters(), lr=3e-4)

GAMMA = 0.99
LAMBDA = 0.95
CLIP_EPS = 0.2
EPOCHS = 10
BATCH_SIZE = 64
MAX_EP = 2000

for episode in range(MAX_EP):
    state, _ = env.reset()
    done = False
    trajectory = {'states':[], 'actions':[], 'log_probs':[], 'rewards':[], 'values':[], 'dones':[]}
    
    while not done:
        state_t = torch.FloatTensor(state).unsqueeze(0)
        value = critic(state_t).item()
        
        if continuous:
            mu, std = actor(state_t)
            dist = Normal(mu, std)
            action = dist.sample()
            log_prob = dist.log_prob(action).sum(-1)
            action = action.numpy()[0]
        else:
            logits = actor(state_t)
            dist = Categorical(logits=logits)
            action = dist.sample()
            log_prob = dist.log_prob(action)
            action = action.item()
        
        next_state, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        
        trajectory['states'].append(state_t)
        trajectory['actions'].append(action)
        trajectory['log_probs'].append(log_prob)
        trajectory['rewards'].append(reward)
        trajectory['values'].append(value)
        trajectory['dones'].append(done)
        
        state = next_state
    
    # 计算回报与GAE
    trajectory['rewards'][-1] += critic(torch.FloatTensor(state).unsqueeze(0)).item() * (not done)
    returns = []
    gae = 0
    for r, v, d in zip(reversed(trajectory['rewards']),
                       reversed(trajectory['values']),
                       reversed(trajectory['dones'])):
        delta = r - v + GAMMA * (1 - d) * (returns[-1] if returns else 0)
        gae = delta + GAMMA * LAMBDA * (1 - d) * gae
        returns.insert(0, gae + v)
    
    # PPO 更新（多epoch，小batch）
    states = torch.cat(trajectory['states'])
    old_log_probs = torch.stack(trajectory['log_probs']).detach()
    actions = torch.tensor(trajectory['actions'])
    returns = torch.FloatTensor(returns)
    advantages = returns - torch.FloatTensor(trajectory['values'])
    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
    
    for _ in range(EPOCHS):
        for idx in range(0, len(states), BATCH_SIZE):
            batch_slice = slice(idx, idx + BATCH_SIZE)
            s = states[batch_slice]
            a = actions[batch_slice]
            old_lp = old_log_probs[batch_slice]
            adv = advantages[batch_slice]
            ret = returns[batch_slice]
            
            # actor 更新
            if continuous:
                mu, std = actor(s)
                dist = Normal(mu, std)
                new_lp = dist.log_prob(a).sum(-1)
            else:
                logits = actor(s)
                dist = Categorical(logits=logits)
                new_lp = dist.log_prob(a)
            
            ratio = (new_lp - old_lp).exp()
            surr1 = ratio * adv
            surr2 = torch.clamp(ratio, 1-CLIP_EPS, 1+CLIP_EPS) * adv
            actor_loss = -torch.min(surr1, surr2).mean()
            
            actor_optim.zero_grad()
            actor_loss.backward()
            actor_optim.step()
            
            # critic 更新
            value_pred = critic(s).squeeze()
            critic_loss = (ret - value_pred).pow(2).mean()
            
            critic_optim.zero_grad()
            critic_loss.backward()
            critic_optim.step()
    
    if episode % 20 == 0:
        print(f"[{episode}] reward = {sum(trajectory['rewards']):.1f}")

env.close()