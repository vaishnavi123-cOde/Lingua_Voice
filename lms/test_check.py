from vocabulary_engine import vocabulary_engine
from database_manager import db
from api_service import api_service
vocabulary_engine.api = api_service

conn = db.get_connection()

# Check users table schema
cols = conn.execute("PRAGMA table_info(users)").fetchall()
print("Users columns:", [(c[1], c[2]) for c in cols])

users = conn.execute("SELECT * FROM users LIMIT 5").fetchall()
print("Users:", users)

if users:
    uid = users[-1][0]  # Vaishnavi
    print("\nUser ID:", uid)
    vocab = conn.execute("SELECT * FROM vocabulary WHERE user_id = ?", (uid,)).fetchall()
    print("Vocabulary count:", len(vocab))
    for v in vocab[:20]:
        print("  %s - %s (level %s)" % (v[1], v[2], v[3]))
    vcols = conn.execute("PRAGMA table_info(vocabulary)").fetchall()
    print("Vocab columns:", [(c[1], c[2]) for c in vcols])
    
    # Check discovery
    disc = conn.execute("SELECT * FROM vocabulary_discovery WHERE user_id = ? LIMIT 10", (uid,)).fetchall()
    print("Discovery entries:", disc)
    
    # Test get_recommendations
    print("\nCalling get_recommendations...")
    recs = vocabulary_engine.get_recommendations(uid, limit=10)
    print("Recommendations:", len(recs))
    for r in recs:
        print("  %s - %s (score: %s, id: %s)" % (r.get("word"), r.get("relation_type"), r.get("score"), r.get("id")))
conn.close()
