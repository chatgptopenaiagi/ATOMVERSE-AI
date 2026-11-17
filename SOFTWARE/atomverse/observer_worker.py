"""Owned subprocess: collect, commit one batch, emit bounded JSON, await cancellation."""
import argparse
import json
import sys
import threading
import time
from uuid import uuid4
from .core import Memory, utc_now
from .observer import Collector, ObserverConfig
from .storage import retain


def main(arguments):
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--gui-pid', type=int)
    parser.add_argument('--samples', type=int, default=0)
    args = parser.parse_args(arguments)
    stop = threading.Event()
    def listen():
        try:
            for line in sys.stdin:
                if line.strip() == 'stop':
                    break
        finally:
            stop.set()
    threading.Thread(target=listen, daemon=True, name='observer-cancel').start()
    memory, collector = None, None
    session = str(uuid4()); count = 0
    def emit(data):
        print(json.dumps(data, allow_nan=False, separators=(',', ':')), flush=True)
    try:
        config = ObserverConfig(**json.loads(args.config)); config.validate()
        memory = Memory(args.database)
        with memory.db:
            memory.db.execute('INSERT INTO sessions VALUES (?,?,NULL,?)', (session, utc_now(), json.dumps(config.validate())))
        collector = Collector(config, session, args.gui_pid)
        due = time.perf_counter()
        while not stop.is_set():
            start = time.perf_counter(); delay = max(0, (start - due) * 1000)
            events = collector.sample()
            removed = retain(memory, len(events), config.max_rows, config.retention_hours)
            memory.add(events)
            count += 1
            emit({'type': 'sample', 'session': session, 'sequence': count, 'events': events,
                  'sample_duration_ms': (time.perf_counter() - start) * 1000, 'scheduling_delay_ms': delay,
                  'retention_removed': removed, 'committed': True})
            if args.samples and count >= args.samples:
                break
            # Never catch up in a busy loop after a delayed sample.
            due = max(due + config.interval_s, time.perf_counter() + 0.01)
            stop.wait(max(0, due - time.perf_counter()))
        emit({'type': 'stopped', 'session': session, 'samples': count})
    except Exception as exc:
        emit({'type': 'error', 'message': str(exc)[:1000]})
        return 1
    finally:
        if collector:
            collector.close()
        if memory:
            with memory.db:
                memory.db.execute('UPDATE sessions SET ended=? WHERE id=?', (utc_now(), session))
            memory.close()
    return 0
