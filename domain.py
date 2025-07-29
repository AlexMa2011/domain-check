#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import itertools
import aiodns
import whois
import time
from tqdm import tqdm

async def check_domain(domain: str, resolver: aiodns.DNSResolver) -> bool:
    """
    DNS 查询 NS 记录：
      - NXDOMAIN (错误码 3/4) → 很可能未注册 → 返回 True
      - 有记录或其他错误 → 当作已注册 → 返回 False
    """
    try:
        await resolver.query(domain, 'NS')
        return False
    except aiodns.error.DNSError as e:
        # 3 = Name error, 4 = Not found
        if e.args and e.args[0] in (3, 4):
            return True
        return False

async def scan_domain(domain: str,
                      resolver: aiodns.DNSResolver,
                      sem: asyncio.Semaphore) -> (str, bool):
    """受限并发地扫描一个域名，返回 (domain, is_available)。"""
    async with sem:
        ok = await check_domain(domain, resolver)
    return domain, ok

async def main_async(args):
    # 1. 生成所有待测域名列表
    domains = []
    for L in range(args.min_len, args.max_len + 1):
        for tpl in itertools.product(args.chars, repeat=L):
            prefix = ''.join(tpl)
            for tld in args.tlds:
                domains.append(f"{prefix}{tld}")

    total = len(domains)
    print(f"总共 {total} 个域名，开始扫描…")

    # 2. 准备 DNS resolver 和并发 Semaphore
    resolver = aiodns.DNSResolver(nameservers=args.dns or ['1.1.1.1'])
    sem = asyncio.Semaphore(args.concurrency)

    # 3. 为每个域名创建协程
    tasks = [
        asyncio.create_task(scan_domain(dom, resolver, sem))
        for dom in domains
    ]

    # 4. 使用 tqdm 对 as_completed 进行包裹，实时更新进度
    available = []
    with tqdm(total=total, desc="扫描进度", ncols=80) as pbar:
        for coro in asyncio.as_completed(tasks):
            dom, ok = await coro
            if ok:
                available.append(dom)
            pbar.update(1)

    # 5. 输出结果及 WHOIS 查询
    print(f"\n扫描完毕，用时 {time.time() - start:.1f}s，可用 {len(available)} 个域名。开始 WHOIS 查询…")
    # 执行 WHOIS 查询
    whois_results = []
    for dom in tqdm(available, desc="WHOIS 进度", ncols=80):
        try:
            info = await asyncio.get_event_loop().run_in_executor(None, whois.whois, dom)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import itertools
import aiodns
import whois
import time
from tqdm import tqdm

async def check_domain(domain: str, resolver: aiodns.DNSResolver) -> bool:
    """
    DNS 查询 NS 记录：
      - NXDOMAIN (错误码 3/4) → 很可能未注册 → 返回 True
      - 有记录或其他错误 → 当作已注册 → 返回 False
    """
    try:
        await resolver.query(domain, 'NS')
        return False
    except aiodns.error.DNSError as e:
        # 3 = Name error, 4 = Not found
        if e.args and e.args[0] in (3, 4):
            return True
        return False

async def scan_domain(domain: str,
                      resolver: aiodns.DNSResolver,
                      sem: asyncio.Semaphore) -> (str, bool):
    """受限并发地扫描一个域名，返回 (domain, is_available)。"""
    async with sem:
        ok = await check_domain(domain, resolver)
    return domain, ok

async def main_async(args):
    # 1. 生成所有待测域名列表
    domains = []
    for L in range(args.min_len, args.max_len + 1):
        for tpl in itertools.product(args.chars, repeat=L):
            prefix = ''.join(tpl)
            for tld in args.tlds:
                domains.append(f"{prefix}{tld}")

    total = len(domains)
    print(f"总共 {total} 个域名，开始扫描…")

    # 2. 准备 DNS resolver 和并发 Semaphore
    resolver = aiodns.DNSResolver(nameservers=args.dns or ['1.1.1.1'])
    sem = asyncio.Semaphore(args.concurrency)

    # 3. 为每个域名创建协程
    tasks = [
        asyncio.create_task(scan_domain(dom, resolver, sem))
        for dom in domains
    ]

    # 4. 使用 tqdm 对 as_completed 进行包裹，实时更新进度
    available = []
    with tqdm(total=total, desc="扫描进度", ncols=80) as pbar:
        for coro in asyncio.as_completed(tasks):
            dom, ok = await coro
            if ok:
                available.append(dom)
            pbar.update(1)

    # 5. 输出结果及 WHOIS 查询
    print(f"\n扫描完毕，用时 {time.time() - start:.1f}s，可用 {len(available)} 个域名。开始 WHOIS 查询…")
    # 执行 WHOIS 查询
    whois_results = []
    for dom in tqdm(available, desc="WHOIS 进度", ncols=80):
        try:
            info = await asyncio.get_event_loop().run_in_executor(None, whois.whois, dom)
        except Exception as e:
            info = str(e)
        whois_results.append((dom, info))
    # 写入结果到文件
    with open(args.out, 'w', encoding='utf-8') as f:
        for dom, _ in whois_results:
            f.write(dom + '\n')
    print(f"结果已写入 {args.out}")

def parse_args():
    p = argparse.ArgumentParser(
        description="异步 DNS 批量检测未注册域名（带进度条）"
    )
    p.add_argument('-t', '--tlds', nargs='+', required=True,
                   help="后缀列表，如 .com .net .im")
    p.add_argument('-c', '--chars', required=True,
                   help="字符集，如 abc123")
    p.add_argument('--min-len', type=int, default=3,
                   help="最小长度，默认3")
    p.add_argument('--max-len', type=int, default=3,
                   help="最大长度，默认3")
    p.add_argument('-C', '--concurrency', type=int, default=500,
                   help="最大并发 DNS 查询数，默认500")
    p.add_argument('-o', '--out', default='available.txt',
                   help="输出文件，默认 available.txt")
    p.add_argument('--dns', nargs='*',
                   help="上游 DNS 服务器，默认 1.1.1.1")
    return p.parse_args()

if __name__ == '__main__':
    args = parse_args()
    start = time.time()
    asyncio.run(main_async(args))lable.txt")
    p.add_argument('--dns', nargs='*',
                   help="上游 DNS 服务器，默认 1.1.1.1")
    return p.parse_args()

if __name__ == '__main__':
    args = parse_args()
    start = time.time()
    asyncio.run(main_async(args))
