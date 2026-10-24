#!/usr/bin/env python3
"""Generate a realistic SQL workload for the tokenizer benchmark.

~4000 statements mixing DDL, inserts with varied literals,
selects with joins/aggregates, comments, parameters and quoted
identifiers -- the token shapes a real parser feed sees.
Deterministic (fixed seed); one statement per line so both
benches tokenize line by line.
"""
import random

rng = random.Random(20261023)

FIRST = ["alice", "bob", "carol", "dave", "erin", "frank", "grace",
         "héloïse", "zoë", "müller"]
CITIES = ["Vancouver", "Toronto", "Montréal", "Calgary", "Halifax",
          "Québec", "Winnipeg", "Saskatoon"]
WORDS = ["alpha", "beta", "gamma", "delta", "omega", "sigma", "kappa"]


def ident():
    return rng.choice(WORDS) + "_" + str(rng.randint(0, 999))


def literal():
    r = rng.random()
    if r < 0.3:
        return str(rng.randint(-100000, 100000))
    if r < 0.5:
        return "%.3f" % (rng.random() * 1000)
    if r < 0.6:
        return "'%s'" % rng.choice(FIRST)
    if r < 0.7:
        return "'it''s %s'" % rng.choice(WORDS)
    if r < 0.8:
        return "x'%02X%02X'" % (rng.randint(0, 255), rng.randint(0, 255))
    if r < 0.9:
        return "0x%X" % rng.randint(0, 65535)
    return "?%d" % rng.randint(1, 50)


def insert():
    cols = ", ".join(ident() for _ in range(rng.randint(2, 6)))
    vals = ", ".join(literal() for _ in range(rng.randint(2, 6)))
    return "INSERT INTO %s (%s) VALUES (%s);" % (ident(), cols, vals)


def select():
    t = ident()
    where = " WHERE %s %s %s" % (ident(), rng.choice(["=", ">", "<", "!=", "LIKE", "IN"]),
                                 literal()) if rng.random() < 0.7 else ""
    if rng.random() < 0.3:
        where += " AND %s IS NOT NULL" % ident()
    agg = rng.choice(["COUNT(*)", "SUM(%s)" % ident(), "AVG(%s)" % ident(), "*"])
    grp = " GROUP BY %s" % ident() if rng.random() < 0.3 else ""
    ord_ = " ORDER BY %s %s" % (ident(), rng.choice(["ASC", "DESC"])) if rng.random() < 0.4 else ""
    lim = " LIMIT %d" % rng.randint(1, 100) if rng.random() < 0.4 else ""
    join = ""
    if rng.random() < 0.3:
        join = " JOIN %s ON %s.id = %s.id" % (ident(), t, ident())
    return "SELECT %s FROM %s%s%s%s%s%s;" % (agg, t, join, where, grp, ord_, lim)


def ddl():
    return ("CREATE TABLE IF NOT EXISTS %s (id INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL DEFAULT 'unknown', score REAL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE(name));" % ident())


def misc():
    r = rng.random()
    if r < 0.3:
        return "-- comment about %s and %s" % (ident(), ident())
    if r < 0.5:
        return "/* block comment %s */ SELECT 1;" % ident()
    if r < 0.7:
        return 'SELECT "quoted col", `bt`, [br] FROM "%s";' % ident()
    if r < 0.85:
        return "UPDATE %s SET %s = %s WHERE id = :id;" % (ident(), ident(), literal())
    return "DELETE FROM %s WHERE %s IN (SELECT %s FROM %s);" % (
        ident(), ident(), ident(), ident())


lines = []
for i in range(4000):
    r = rng.random()
    if r < 0.4:
        lines.append(insert())
    elif r < 0.75:
        lines.append(select())
    elif r < 0.85:
        lines.append(ddl())
    else:
        lines.append(misc())

out = "\n".join(lines) + "\n"
open("workload.sql", "w").write(out)
print("workload.sql: %d lines, %d bytes" % (len(lines), len(out)))
