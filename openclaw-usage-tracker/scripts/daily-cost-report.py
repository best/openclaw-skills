#!/usr/bin/env python3
"""
OpenClaw Usage Tracker — 模型用量和费用统计

Usage:
  python3 daily-cost-report.py                          # 昨天
  python3 daily-cost-report.py 2026-03-14               # 指定单日
  python3 daily-cost-report.py 2026-03-10 2026-03-15    # 日期范围
  python3 daily-cost-report.py --all                    # 全量历史
  python3 daily-cost-report.py 2026-03-14 --top-sessions 10  # 含 Top N session
  python3 daily-cost-report.py --all --top-sessions 5   # 组合使用
"""
import json, os, sys, datetime, argparse, re
from collections import defaultdict


def parse_args():
    p = argparse.ArgumentParser(description='OpenClaw usage & cost report')
    p.add_argument('dates', nargs='*', help='Single date (YYYY-MM-DD) or range (FROM TO)')
    p.add_argument('--all', action='store_true', help='Scan all history')
    p.add_argument('--top-sessions', type=int, default=0, metavar='N',
                   help='Include top N most expensive sessions')
    return p.parse_args()


def load_cost_map():
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
    return cost_map


def build_session_classification():
    """Build file_category map + session metadata (key, agent, first user message)."""
    agents_dir = os.path.expanduser('~/.openclaw/agents')
    file_category = {}   # basename -> category
    session_meta = {}    # basename -> {key, agent, preview}

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
                        bn = os.path.basename(sf).replace('.jsonl', '')
                        file_category[bn] = cat
                        session_meta[bn] = {'key': key, 'agent': agent}
                    sid = entry.get('sessionId', '')
                    if sid:
                        file_category[sid] = cat
                        session_meta[sid] = {'key': key, 'agent': agent}
            except:
                pass

        # Content-based fallback for orphaned sessions
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
                                content = _extract_text(msg)
                                if content.startswith('[cron:'):
                                    file_category[basename] = 'cron'
                                break
                        except:
                            continue
            except:
                pass

    return file_category, session_meta


def _extract_text(msg):
    content = msg.get('content', '')
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                return block.get('text', '')
        return ''
    return content if isinstance(content, str) else ''


def classify(fname, file_category):
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
        provider, model = parts[0], parts[1]
        p_short = {
            'astralor': 'astralor', 'gptclub-openai': 'gptclub',
            'gptclub-claude': 'gptclub', 'gptclub-google': 'gptclub',
            'deeprouter': 'deeprouter', 'minimax': 'minimax',
            'kimi-coding': 'kimi',
        }.get(provider, provider)
        return f"{p_short}/{model}"
    return mk


def extract_usage(usage):
    """Extract token counts from various usage field formats."""
    inp = usage.get('input', usage.get('inputTokens',
          usage.get('input_tokens', usage.get('promptTokens', 0)))) or 0
    out = usage.get('output', usage.get('outputTokens',
          usage.get('output_tokens', usage.get('completionTokens', 0)))) or 0
    cr = usage.get('cacheRead', usage.get('cache_read',
         usage.get('cache_read_input_tokens', usage.get('cached_tokens', 0)))) or 0
    if cr == 0:
        ptd = usage.get('prompt_tokens_details', {})
        if isinstance(ptd, dict):
            cr = ptd.get('cached_tokens', 0) or 0
    cw = usage.get('cacheWrite', usage.get('cache_write',
         usage.get('cache_creation_input_tokens', 0))) or 0
    return inp, out, cr, cw


def calc_cost(usage, mk, cost_map):
    """Calculate cost: prefer provider-returned, fallback to config estimate."""
    usage_cost = usage.get('cost')
    if isinstance(usage_cost, dict) and usage_cost.get('total') is not None:
        return usage_cost['total']
    inp, out, cr, cw = extract_usage(usage)
    if mk in cost_map:
        c = cost_map[mk]
        return (inp * c.get('input', 0) + out * c.get('output', 0) +
                cr * c.get('cacheRead', 0) + cw * c.get('cacheWrite', 0)) / 1_000_000
    return 0.0


def date_matches(ts, date_from, date_to):
    """Check if timestamp string falls within date range (inclusive)."""
    if not isinstance(ts, str) or len(ts) < 10:
        return False
    day = ts[:10]
    return date_from <= day <= date_to


def get_first_user_message(fpath):
    """Read first user message from a .jsonl file for session preview."""
    try:
        with open(fpath) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    msg = entry.get('message', {})
                    if isinstance(msg, dict) and msg.get('role') == 'user':
                        text = _extract_text(msg)
                        # Truncate for preview
                        text = text.replace('\n', ' ')[:120]
                        return text
                except:
                    continue
    except:
        pass
    return ''


def make_bucket():
    return {'entries': 0, 'cost': 0.0, 'input': 0, 'output': 0,
            'cacheRead': 0, 'cacheWrite': 0}


def add_to_bucket(b, inp, out, cr, cw, cost_val):
    b['entries'] += 1
    b['input'] += inp
    b['output'] += out
    b['cacheRead'] += cr
    b['cacheWrite'] += cw
    b['cost'] += cost_val


def bucket_to_dict(b):
    tokens = b['input'] + b['output'] + b['cacheRead'] + b['cacheWrite']
    return {
        'entries': b['entries'], 'cost': round(b['cost'], 2),
        'tokens': tokens, 'tokens_fmt': fmt_tokens(tokens),
        'input': b['input'], 'input_fmt': fmt_tokens(b['input']),
        'output': b['output'], 'output_fmt': fmt_tokens(b['output']),
        'cacheRead': b['cacheRead'], 'cacheRead_fmt': fmt_tokens(b['cacheRead']),
        'cacheWrite': b['cacheWrite'], 'cacheWrite_fmt': fmt_tokens(b['cacheWrite']),
    }


def main():
    args = parse_args()

    # Determine date range
    if args.all:
        date_from, date_to = '0000-00-00', '9999-99-99'
    elif len(args.dates) == 2:
        date_from, date_to = args.dates[0], args.dates[1]
    elif len(args.dates) == 1:
        date_from = date_to = args.dates[0]
    else:
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        date_from = date_to = yesterday

    is_range = date_from != date_to
    cost_map = load_cost_map()
    file_category, session_meta = build_session_classification()
    agents_dir = os.path.expanduser('~/.openclaw/agents')

    # Accumulators
    total = make_bucket()
    daily = defaultdict(make_bucket)           # date -> bucket
    cat_total = {}                              # cat -> bucket + models
    model_total = defaultdict(make_bucket)      # model_key -> bucket
    session_costs = defaultdict(lambda: {       # (agent, fname) -> session data
        **make_bucket(), 'model': '', 'fpath': ''
    })

    # Scan all sessions
    for agent in os.listdir(agents_dir):
        sessions_dir = os.path.join(agents_dir, agent, 'sessions')
        if not os.path.isdir(sessions_dir):
            continue
        for fname in os.listdir(sessions_dir):
            if not fname.endswith('.jsonl'):
                continue
            cat = classify(fname, file_category)
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
                        if not date_matches(ts, date_from, date_to):
                            continue
                        msg = entry.get('message', {})
                        if not isinstance(msg, dict) or msg.get('role') != 'assistant':
                            continue
                        usage = msg.get('usage') or entry.get('usage')
                        if not usage or not isinstance(usage, dict):
                            continue

                        provider = msg.get('provider', entry.get('provider', ''))
                        model = msg.get('model', entry.get('model', ''))
                        mk = f"{provider}/{model}" if provider else model

                        inp, out, cr, cw = extract_usage(usage)
                        cost_val = calc_cost(usage, mk, cost_map)
                        day = ts[:10]

                        # Total
                        add_to_bucket(total, inp, out, cr, cw, cost_val)

                        # Daily
                        add_to_bucket(daily[day], inp, out, cr, cw, cost_val)

                        # Category
                        if cat not in cat_total:
                            cat_total[cat] = {**make_bucket(), 'models': defaultdict(lambda: {'entries': 0, 'cost': 0.0})}
                        add_to_bucket(cat_total[cat], inp, out, cr, cw, cost_val)
                        cat_total[cat]['models'][mk]['entries'] += 1
                        cat_total[cat]['models'][mk]['cost'] += cost_val

                        # Model total
                        add_to_bucket(model_total[mk], inp, out, cr, cw, cost_val)

                        # Session tracking (for top-sessions)
                        if args.top_sessions > 0:
                            sk = (agent, fname)
                            add_to_bucket(session_costs[sk], inp, out, cr, cw, cost_val)
                            session_costs[sk]['model'] = mk
                            session_costs[sk]['fpath'] = fpath
            except:
                pass

    # Build output
    output = {}

    if is_range:
        output['range'] = {'from': date_from, 'to': date_to}
    else:
        output['date'] = date_from

    # Summary (total)
    output['total'] = bucket_to_dict(total)

    # Daily breakdown (only for range mode)
    if is_range:
        daily_list = []
        for day in sorted(daily.keys()):
            d = bucket_to_dict(daily[day])
            d['date'] = day
            daily_list.append(d)
        output['daily'] = daily_list

    # Categories
    output['categories'] = {}
    total_cost = total['cost']
    for cat_name in ['interactive', 'cron', 'heartbeat']:
        c = cat_total.get(cat_name)
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

    # Models
    output['models'] = []
    for mk, mt in sorted(model_total.items(), key=lambda x: -x[1]['cost']):
        sm = short_model(mk)
        if 'delivery-mirror' in sm or 'acp-runtime' in sm:
            continue
        output['models'].append({
            'name': sm,
            **bucket_to_dict(mt),
        })

    # Top sessions
    if args.top_sessions > 0:
        top = sorted(session_costs.items(), key=lambda x: -x[1]['cost'])[:args.top_sessions]
        top_list = []
        for (agent, fname), data in top:
            if data['cost'] <= 0:
                continue
            basename = fname.replace('.jsonl', '')
            meta = session_meta.get(basename, {})
            cat = classify(fname, file_category)
            preview = get_first_user_message(data['fpath'])
            top_list.append({
                'agent': agent,
                'category': cat,
                'session_key': meta.get('key', basename),
                'preview': preview,
                'model': short_model(data['model']),
                **bucket_to_dict(data),
            })
        output['topSessions'] = top_list

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
