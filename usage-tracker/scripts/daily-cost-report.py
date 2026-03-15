#!/usr/bin/env python3
"""
Daily cost report - 统计指定日期的模型用量和费用
Usage: python3 daily-cost-report.py [YYYY-MM-DD]
       不传日期则默认统计昨天
"""
import json, os, sys, datetime

def main():
    # Determine target date
    if len(sys.argv) > 1:
        target_day = sys.argv[1]
    else:
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        target_day = yesterday.strftime('%Y-%m-%d')

    # Load cost config
    config_path = os.path.expanduser('~/.openclaw/openclaw.json')
    with open(config_path) as f:
        cfg = json.load(f)

    cost_map = {}
    for pname, pdata in cfg.get('models', {}).get('providers', {}).items():
        for m in pdata.get('models', []):
            key = f"{pname}/{m['id']}"
            cost = m.get('cost')
            if cost:
                cost_map[key] = cost

    agents_dir = os.path.expanduser('~/.openclaw/agents')

    # Build session classification map
    file_category = {}
    for agent in os.listdir(agents_dir):
        sfile = os.path.join(agents_dir, agent, 'sessions', 'sessions.json')
        if os.path.isfile(sfile):
            try:
                with open(sfile) as f:
                    store = json.load(f)
                for key, entry in store.items():
                    cat = 'cron' if 'cron:' in key else 'heartbeat' if 'heartbeat' in key else 'interactive'
                    sf = entry.get('sessionFile', '')
                    if sf:
                        file_category[os.path.basename(sf).replace('.jsonl', '')] = cat
                    sid = entry.get('sessionId', '')
                    if sid:
                        file_category[sid] = cat
            except:
                pass

        # Content-based: detect [cron:...] prefix in orphaned sessions
        sessions_dir = os.path.join(agents_dir, agent, 'sessions')
        if not os.path.isdir(sessions_dir):
            continue
        for fname in os.listdir(sessions_dir):
            if not fname.endswith('.jsonl'):
                continue
            basename = fname.replace('.jsonl', '')
            if basename in file_category:
                continue
            if '_' in basename:
                uuid_part = basename.split('_', 1)[1]
                if uuid_part in file_category:
                    continue
            fpath = os.path.join(sessions_dir, fname)
            try:
                with open(fpath) as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            msg = entry.get('message', {})
                            if isinstance(msg, dict) and msg.get('role') == 'user':
                                content = msg.get('content', '')
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get('type') == 'text':
                                            content = block.get('text', '')
                                            break
                                if isinstance(content, str) and content.startswith('[cron:'):
                                    file_category[basename] = 'cron'
                                break
                        except:
                            continue
            except:
                pass

    def classify(fname):
        basename = fname.replace('.jsonl', '')
        if basename in file_category:
            return file_category[basename]
        if '_' in basename:
            uuid_part = basename.split('_', 1)[1]
            if uuid_part in file_category:
                return file_category[uuid_part]
        return 'interactive'

    def fmt_tokens(n):
        if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f}B"
        if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
        if n >= 1_000: return f"{n/1_000:.1f}K"
        return str(n)

    def short_model(mk):
        parts = mk.split('/')
        if len(parts) >= 2:
            provider = parts[0]
            model = parts[1]
            # Shorten provider
            p_short = {
                'astralor': 'astralor',
                'gptclub-openai': 'gptclub',
                'gptclub-claude': 'gptclub',
                'gptclub-google': 'gptclub',
                'deeprouter': 'deeprouter',
                'minimax': 'minimax',
                'kimi-coding': 'kimi',
            }.get(provider, provider)
            return f"{p_short}/{model}"
        return mk

    # Scan
    categories = {}  # cat -> {entries, cost, input, output, cacheRead, cacheWrite, models}
    models_total = {}  # mk -> {entries, cost, input, output, cacheRead, cacheWrite}

    for agent in os.listdir(agents_dir):
        sessions_dir = os.path.join(agents_dir, agent, 'sessions')
        if not os.path.isdir(sessions_dir):
            continue
        for fname in os.listdir(sessions_dir):
            if not fname.endswith('.jsonl'):
                continue
            cat = classify(fname)
            fpath = os.path.join(sessions_dir, fname)
            try:
                with open(fpath) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except:
                            continue
                        ts = entry.get('timestamp', '')
                        if not isinstance(ts, str) or not ts.startswith(target_day):
                            continue
                        msg = entry.get('message', {})
                        if not isinstance(msg, dict) or msg.get('role') != 'assistant':
                            continue
                        usage = msg.get('usage') or entry.get('usage')
                        if not usage or not isinstance(usage, dict):
                            continue

                        inp = usage.get('input', usage.get('inputTokens', usage.get('input_tokens', usage.get('promptTokens', 0)))) or 0
                        out = usage.get('output', usage.get('outputTokens', usage.get('output_tokens', usage.get('completionTokens', 0)))) or 0
                        cr = usage.get('cacheRead', usage.get('cache_read', usage.get('cache_read_input_tokens', usage.get('cached_tokens', 0)))) or 0
                        if cr == 0:
                            ptd = usage.get('prompt_tokens_details', {})
                            if isinstance(ptd, dict):
                                cr = ptd.get('cached_tokens', 0) or 0
                        cw = usage.get('cacheWrite', usage.get('cache_write', usage.get('cache_creation_input_tokens', 0))) or 0

                        provider = msg.get('provider', entry.get('provider', ''))
                        model = msg.get('model', entry.get('model', ''))
                        mk = f"{provider}/{model}" if provider else model

                        # Cost
                        cost_val = 0.0
                        usage_cost = usage.get('cost')
                        if isinstance(usage_cost, dict) and usage_cost.get('total') is not None:
                            cost_val = usage_cost['total']
                        elif mk in cost_map:
                            c = cost_map[mk]
                            cost_val = (inp * c.get('input', 0) + out * c.get('output', 0) +
                                        cr * c.get('cacheRead', 0) + cw * c.get('cacheWrite', 0)) / 1_000_000

                        # Category accumulation
                        if cat not in categories:
                            categories[cat] = {'entries': 0, 'cost': 0.0, 'input': 0, 'output': 0,
                                               'cacheRead': 0, 'cacheWrite': 0, 'models': {}}
                        cc = categories[cat]
                        cc['entries'] += 1
                        cc['input'] += inp; cc['output'] += out; cc['cacheRead'] += cr; cc['cacheWrite'] += cw
                        cc['cost'] += cost_val
                        if mk not in cc['models']:
                            cc['models'][mk] = {'entries': 0, 'cost': 0.0}
                        cc['models'][mk]['entries'] += 1
                        cc['models'][mk]['cost'] += cost_val

                        # Model total accumulation
                        if mk not in models_total:
                            models_total[mk] = {'entries': 0, 'cost': 0.0, 'input': 0, 'output': 0,
                                                'cacheRead': 0, 'cacheWrite': 0}
                        mt = models_total[mk]
                        mt['entries'] += 1; mt['input'] += inp; mt['output'] += out
                        mt['cacheRead'] += cr; mt['cacheWrite'] += cw; mt['cost'] += cost_val
            except:
                pass

    total_cost = sum(c['cost'] for c in categories.values())
    total_entries = sum(c['entries'] for c in categories.values())
    total_input = sum(c['input'] for c in categories.values())
    total_output = sum(c['output'] for c in categories.values())
    total_cr = sum(c['cacheRead'] for c in categories.values())
    total_cw = sum(c['cacheWrite'] for c in categories.values())
    total_tokens = total_input + total_output + total_cr + total_cw

    # Build output as JSON for the cron agent to format
    output = {
        'date': target_day,
        'total': {
            'cost': round(total_cost, 2),
            'entries': total_entries,
            'tokens': total_tokens,
            'input': total_input,
            'output': total_output,
            'cacheRead': total_cr,
            'cacheWrite': total_cw,
            'tokens_fmt': fmt_tokens(total_tokens),
            'input_fmt': fmt_tokens(total_input),
            'output_fmt': fmt_tokens(total_output),
            'cacheRead_fmt': fmt_tokens(total_cr),
            'cacheWrite_fmt': fmt_tokens(total_cw),
        },
        'categories': {},
        'models': [],
    }

    for cat_name in ['interactive', 'cron', 'heartbeat']:
        c = categories.get(cat_name)
        if not c:
            continue
        cat_tokens = c['input'] + c['output'] + c['cacheRead'] + c['cacheWrite']
        cat_data = {
            'entries': c['entries'],
            'cost': round(c['cost'], 2),
            'tokens_fmt': fmt_tokens(cat_tokens),
            'pct': round(c['cost'] / total_cost * 100, 1) if total_cost > 0 else 0,
            'models': []
        }
        for mk, md in sorted(c['models'].items(), key=lambda x: -x[1]['cost']):
            sm = short_model(mk)
            if 'delivery-mirror' in sm or 'acp-runtime' in sm:
                continue
            cat_data['models'].append({
                'name': sm,
                'entries': md['entries'],
                'cost': round(md['cost'], 2),
            })
        output['categories'][cat_name] = cat_data

    for mk, mt in sorted(models_total.items(), key=lambda x: -x[1]['cost']):
        sm = short_model(mk)
        if 'delivery-mirror' in sm or 'acp-runtime' in sm:
            continue
        tok = mt['input'] + mt['output'] + mt['cacheRead'] + mt['cacheWrite']
        output['models'].append({
            'name': sm,
            'entries': mt['entries'],
            'cost': round(mt['cost'], 2),
            'tokens_fmt': fmt_tokens(tok),
            'input_fmt': fmt_tokens(mt['input']),
            'output_fmt': fmt_tokens(mt['output']),
            'cacheRead_fmt': fmt_tokens(mt['cacheRead']),
            'cacheWrite_fmt': fmt_tokens(mt['cacheWrite']),
        })

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
