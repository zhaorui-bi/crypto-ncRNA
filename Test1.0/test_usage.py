import random
import string
import os
import csv
from dataclasses import dataclass, field
from collections import defaultdict
import psutil  # 新增：用于监控资源消耗
import tracemalloc  # 新增：用于更精确的内存追踪

@dataclass
class EncryptionArgs:
    plaintext: str
    data_length: int
    params: tuple

def generate_random_string(length=32, charset=string.ascii_letters + string.digits, secure=False):
    if secure:
        return ''.join(random.SystemRandom().choices(charset, k=length))
    return ''.join(random.choices(charset, k=length))

def benchmark_encryption(algorithm_name, encrypt_function, decrypt_function, data_lengths, run_times, *args):
    times = defaultdict(lambda: {"data_lengths": [],
                                 "encryption_memory": [],
                                 "decryption_memory": []})

    loaded_args = {}
    for data_length in data_lengths:
        plaintext = generate_random_string(data_length)
        loaded_args[data_length] = EncryptionArgs(plaintext, data_length, ())

    for data_length in data_lengths:
        preloaded_data = loaded_args[data_length]
        plaintext = preloaded_data.plaintext

        for _ in range(run_times):
            # 加密过程内存统计
            snapshot_before_enc = tracemalloc.take_snapshot()
            if algorithm_name == "AES":
                seed = generate_random_string(32, string.digits, secure=True)
                salt = generate_random_string(16, secure=True)
                encrypted_data = encrypt_function(plaintext, seed, salt)
            elif algorithm_name == "RSA":
                encrypted_data, public_key, private_key = encrypt_function(plaintext)
            elif algorithm_name == "ncRNA":
                seed = generate_random_string(32, string.digits, secure=True).encode()
                seed_sequence = generate_random_string(32, charset='ACGU', secure=True)
                salt = generate_random_string(16, secure=True)
                encrypted_data_tuple = encrypt_function(plaintext, seed, seed_sequence, salt)
                encrypted_data = encrypted_data_tuple[0]
            snapshot_after_enc = tracemalloc.take_snapshot()
            
            # 计算加密内存消耗
            stats_enc = snapshot_after_enc.compare_to(snapshot_before_enc, 'lineno')
            enc_memory = sum(stat.size_diff for stat in stats_enc if stat.size_diff > 0) / (1024 * 1024)
            times[algorithm_name]["encryption_memory"].append(enc_memory)
            times[algorithm_name]["data_lengths"].append(data_length)

            # 解密过程内存统计
            snapshot_before_dec = tracemalloc.take_snapshot()
            if algorithm_name == "AES":
                decrypt_function(encrypted_data, seed, salt)
            elif algorithm_name == "RSA":
                decrypt_function(encrypted_data, private_key)
            elif algorithm_name == "ncRNA":
                decrypt_function(encrypted_data, seed, seed_sequence, salt, *encrypted_data_tuple[1:])
            snapshot_after_dec = tracemalloc.take_snapshot()
            
            # 计算解密内存消耗
            stats_dec = snapshot_after_dec.compare_to(snapshot_before_dec, 'lineno')
            dec_memory = sum(stat.size_diff for stat in stats_dec if stat.size_diff > 0) / (1024 * 1024)
            times[algorithm_name]["decryption_memory"].append(dec_memory)

    return times

def setup_algorithms():
    from algorithm.ncRNA3_5 import encrypt as ncRNA_encrypt, decrypt as ncRNA_decrypt
    from algorithm.AES import aes_encrypt, aes_decrypt
    from algorithm.RSA import rsa_encrypt, rsa_decrypt

    algorithms = [
        ("ncRNA", ncRNA_encrypt, ncRNA_decrypt),
        ("AES", aes_encrypt, aes_decrypt),
        ("RSA", rsa_encrypt, rsa_decrypt)
    ]

    return algorithms

def find_next_file_number(directory="./results/csv/usage"):
    """返回下一个可用的文件编号"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    existing_files = os.listdir(directory)
    existing_numbers = []
    
    for file_name in existing_files:
        if file_name.endswith(".csv"):
            try:
                num = int(file_name.split("_")[1].split(".")[0])
                existing_numbers.append(num)
            except ValueError:
                continue
    
    next_number = max(existing_numbers, default=0) + 1
    return next_number

def save_to_csv(all_times, file_number):
    """将所有结果汇总到一个CSV文件"""
    file_path = f"./results/csv/usage/usage_{file_number}.csv"
    
    # 如果文件不存在，写入表头
    file_exists = os.path.exists(file_path)
    with open(file_path, mode='a', newline='') as f:
        writer = csv.writer(f)
        
        if not file_exists:
            # 写入表头
            writer.writerow(["Algorithm", "Data Length", 
                             "Encryption Memory Usage (MB)", 
                             "Decryption Memory Usage (MB)"])

        # 遍历所有算法及其结果
        for algo_name, time_data in all_times.items():
            for i in range(len(time_data["encryption_memory"])):
                data_length = time_data["data_lengths"][i]
                enc_mem = time_data["encryption_memory"][i]
                dec_mem = time_data["decryption_memory"][i]
                writer.writerow([algo_name, data_length, enc_mem, dec_mem])

    print(f"Results saved to {file_path}")

def main():
    data_lengths = [1000, 100000, 1000000]
    run_times = 5

    algorithms = setup_algorithms()

    # 生成下一个文件编号
    file_number = find_next_file_number()

    # 存储所有算法的结果
    all_times = defaultdict(lambda: {"data_lengths": [],
                                     "encryption_memory": [],
                                     "decryption_memory": []})

    # 循环算法并进行加密解密基准测试
    for algo_name, encrypt_fn, decrypt_fn in algorithms:
        times = benchmark_encryption(algo_name, encrypt_fn, decrypt_fn, data_lengths, run_times)
        
        # 合并每个算法的结果
        for key in times:
            all_times[key]["encryption_memory"].extend(times[key]["encryption_memory"])
            all_times[key]["decryption_memory"].extend(times[key]["decryption_memory"])
            all_times[key]["data_lengths"].extend(times[key]["data_lengths"])

    # 将所有结果保存到同一个CSV文件
    save_to_csv(all_times, file_number)

if __name__ == "__main__":
    tracemalloc.start()  # 启动内存追踪
    main()