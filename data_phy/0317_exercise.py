'''
#100以内的素数
for num in range(2,101):
    is_prime = True
    for i in range(2, num):
    #for i in range(2, int(num**0.5)+1):
        if num % i == 0:
            is_prime = False
            break
    if is_prime:
        print(f"{num} is a prime number")


#输出斐波那契数列的前20个数，从第三个数开始，每个数都是前面两个数的和
a, b = 0, 1
for _ in range(20):
    a, b = b, a + b
    print(a)

#找出 100 到 999 范围内的所有水仙花数，水仙花数是指一个 n 位数，其各位数字的 n 次幂之和等于它本身的数
for num in range(100,1000):
    bai = num//100
    shi = (num%100)//10
    ge = num%10
    if num == bai**3 + shi**3 + ge**3:
        print(f"{num} is a narcissistic number")


#古代数学问题
for x in range(0, 21):
    for y in range(0, 34):
        z = 100 - x - y
        if z % 3 == 0 and 5 * x + 3 * y + z // 3 == 100:
            print(f'公鸡: {x}只, 母鸡: {y}只, 小鸡: {z}只')




#说明：CRAPS又称花旗骰，是美国拉斯维加斯非常受欢迎的一种的桌上赌博游戏。该游戏使用两粒骰子，玩家通过摇两粒骰子获得点数进行游戏。
# 简化后的规则是：玩家第一次摇骰子如果摇出了 7 点或 11 点，玩家胜；玩家第一次如果摇出 2 点、3 点或 12 点，庄家胜；
# 玩家如果摇出其他点数则游戏继续，玩家重新摇骰子，如果玩家摇出了 7 点，庄家胜；如果玩家摇出了第一次摇的点数，玩家胜；
# 其他点数玩家继续摇骰子，直到分出胜负。为了增加代码的趣味性，我们设定游戏开始时玩家有 1000 元的赌注，每局游戏开始之前，玩家先下注，
# 如果玩家获胜就可以获得对应下注金额的奖励，如果庄家获胜，玩家就会输掉自己下注的金额。游戏结束的条件是玩家破产（输光所有的赌注）。

import random
money= 1000
a = random.randint(1,6)
b = random.randint(1,6)
point = a + b
if point == 7 or point == 11:
    print('玩家胜出！')
elif point in [2,3,12]:
    print('庄家胜出！')
else:
    while money != 0:
        c = random.randint(1,6)
        d = random.randint(1,6)
        point_new = c + d
        if point_new == 7:
            print('庄家胜出！')
            break
        elif point_new == point:
            print('玩家胜出！')
            break


import random
money = 1000
while money > 0:
    print(f'你的总资产为: {money}元')
    while True:
        debt = int(input('请下注: '))
        if 0 < debt <= money:
            break
    first_point = random.randrange(1, 7) + random.randrange(1, 7)
    print(f'\n玩家摇出了{first_point}点')
    if first_point == 7 or first_point == 11:
        print('玩家胜!\n')
        money += debt
    elif first_point == 2 or first_point == 3 or first_point == 12:
        print('庄家胜!\n')
        money -= debt
    else:
        while True:
            current_point = random.randrange(1, 7) + random.randrange(1, 7)
            print(f'玩家摇出了{current_point}点')
            if current_point == 7:
                print('庄家胜!\n')
                money -= debt
                break
            elif current_point == first_point:
                print('玩家胜!\n')
                money += debt
                break
print('你破产了, 游戏结束!')



'''
'''
languages = ['Python', 'SQL', 'Java', 'C++', 'JavaScript']
list.append()
list.insert()
list.remove()
list.pop()
list.clear()
del list[ ]
list.index()
list.count()
list.sort()
list.reverse()
list.copy()
#列表生成式
#嵌套列表
#拼接 + *
#比较
#循环遍历


#红色球号码从1到33中选择，蓝色球号码从1到16中选择。每注需要选择6个红色球号码和1个蓝色球号码
import random
red_balls = random.sample(range(1, 34), 6)
blue_ball = random.randint(1, 17)

print(f"红色球号码: {red_balls}")
print(f"蓝色球号码: {blue_ball}")
'''

'''
#()表示空元组，但是如果元组中只有一个元素，需要加上一个逗号,
#type(tuple)
#len(tuple)

str.capitalize()  # 将字符串的首字母大写，其他字母小写
str.title()       # 将字符串中每个单词的首字母大写，其他字母小写
str.upper()       # 将字符串中的所有字母转换为大写
str.lower()       # 将字符串中的所有字母转换为小写

str.find()  # 返回子字符串在字符串中首次出现的位置，如果未找到则返回 -1
str.index() # 返回子字符串在字符串中首次出现的位置，如果未找到则抛出 ValueError
str.rindex() # 返回子字符串在字符串中最后一次出现的位置，如果未找到则抛出 ValueError
str.rfind()  # 返回子字符串在字符串中最后一次出现的位置，如果未找到则返回 -1  

str.startswith() # 判断字符串是否以指定的子字符串开头
str.endswith()   # 判断字符串是否以指定的子字符串结尾
str.isalpha()   # 判断字符串是否只包含字母
str.isdigit()   # 判断字符串是否只包含数字
str.isalnum()   # 判断字符串是否只包含字母和数字

str.replace() # 替换字符串中的指定子字符串
str.split()   # 将字符串分割成列表
str.strip()    # 去除字符串两端的空白字符


set.add()
set.discard()
set.clear()
set1.union(set2)
set1.intersection(set2)
set1.difference(set2)   

*args
**kwargs 

'''

"""
#设计一个生成随机验证码的函数，验证码由数字和英文大小写字母构成，长度可以通过参数设置
import random
import string

def lmy_func1(length):
    code = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return code
print(lmy_func1(6))


#设计一个函数，判断一个数是否为素数
def lmy_func2(num):
    for _ in range(2, num):
        if num % _ == 0:
            return f"{num} is not a prime number"
            break 
    else:
        return f"{num} is a prime number"
    
print(lmy_func2(2))


#最大公约数和最小公倍数
def lmy_func3(a, b):
    for _ in range(2, min(a, b) + 1):
        if a % _ == 0 and b % _ == 0:
            gys = _
            return f"{a}和{b}的最大公约数是{gys}"
        
print(lmy_func3(12,15))

def lmy_func4(a, b):
    for _ in range(max(a, b), a * b + 1):
        if _ % a == 0 and _ % b == 0:
            gbs = _
            return f"{a}和{b}的最小公倍数是{gbs}"
print(lmy_func4(12,15))

"""