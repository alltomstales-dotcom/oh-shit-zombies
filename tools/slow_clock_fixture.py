"""Local test databases only: stand in for an hour of waiting between the stages of
tools/mobile_slow_check.mjs. Run it while the local server is stopped.

    python tools/slow_clock_fixture.py /tmp/osz-stick.db SlowCheck give manual_carpentry
    python tools/slow_clock_fixture.py /tmp/osz-stick.db SlowCheck read-back 3590
    python tools/slow_clock_fixture.py /tmp/osz-stick.db SlowCheck jobs-back 3700

`give` puts one item in the living survivor's pack. `read-back` and `jobs-back` move the start of
the reading, or of everything on a station and in the ground, that many seconds into the past.
Nothing here is reachable from the game; it edits a SQLite file by path and refuses anything else.
"""
import json
import sqlite3
import sys


def main(path, name, what, arg):
    assert not path.startswith(("postgres", "sqlite")), "a local SQLite file path only"
    db = sqlite3.connect(path)
    (pid,) = db.execute("select id from player where name=? order by id desc limit 1", (name,)).fetchone()
    sid, raw = db.execute("select id, state from survivor where player_id=? and alive=1 order by id desc limit 1", (pid,)).fetchone()
    state = json.loads(raw)
    if what == "give":
        nid = state.get("_next_item_id", 1)
        state["items"].append({"id": nid, "code": arg, "qty": 1, "cond": None})
        state["_next_item_id"] = nid + 1
    elif what == "read-back":
        assert state.get("study") and state["study"].get("since") is not None, "nobody is reading"
        state["study"]["since"] -= float(arg)
    elif what == "jobs-back":
        (home_raw,) = db.execute("select state from player_home where player_id=?", (pid,)).fetchone()
        home = json.loads(home_raw)
        for o in home.get("objects", []):
            if "ready" in o:
                o["ready"] -= float(arg)
            if o.get("job"):
                o["job"]["ready"] -= float(arg)
                o["job"]["started"] -= float(arg)
        db.execute("update player_home set state=? where player_id=?", (json.dumps(home), pid))
    else:
        raise SystemExit(__doc__)
    db.execute("update survivor set state=? where id=?", (json.dumps(state), sid))
    db.commit()
    print("ok", what)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
