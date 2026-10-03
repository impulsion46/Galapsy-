"""Galapsy′ — construction du site sur Netlify (lancé automatiquement à chaque dépôt sur GitHub).

1. Décompresse les archives galapsy-*.zip dans le dossier « site » (les voix d'abord, le site en dernier).
2. Écrit config.js à partir des variables d'environnement Netlify SUPABASE_URL et SUPABASE_KEY
   (sans elles : atlas en lecture seule, sans comptes ni contributions).
3. Si SUPABASE_DB est renseignée (chaîne de connexion « Session pooler » de Supabase),
   installe ou met à jour la base partagée. Le script SQL peut être rejoué sans risque.
Les mots de passe ne sont jamais affichés dans le journal."""
import glob, json, os, re, shutil, subprocess, sys, zipfile

SITE = "site"
shutil.rmtree(SITE, ignore_errors=True)
archives = sorted(glob.glob("galapsy-*.zip"), key=lambda f: "site" in f)
if not archives:
    sys.exit("Aucune archive galapsy-*.zip dans le dépôt : déposez les fichiers envoyés par Claude.")
for f in archives:
    zipfile.ZipFile(f).extractall(SITE)
    print("décompressé :", f)

# les fichiers d'installation ne sont jamais publiés
INST = "_installation"
shutil.rmtree(INST, ignore_errors=True)
if os.path.isdir(os.path.join(SITE, INST)):
    shutil.move(os.path.join(SITE, INST), INST)

url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
cle = os.environ.get("SUPABASE_KEY", "").strip()
db = os.environ.get("SUPABASE_DB", "").strip()

if url and cle:
    open(os.path.join(SITE, "config.js"), "w", encoding="utf-8").write(
        "/* Galapsy — connexion à la base partagée (Supabase), écrite par Netlify.\n"
        "   Ces deux valeurs sont publiques par nature : la sécurité repose sur les règles de la base. */\n"
        f"window.GALAPSY_CONFIG = {json.dumps({'supabaseUrl': url, 'supabaseKey': cle}, indent=2)};\n")
    print("config.js : base partagée", url)
elif os.path.exists("config.js"):
    shutil.copy("config.js", os.path.join(SITE, "config.js"))
    print("config.js : fichier du dépôt")
else:
    print("config.js : atlas seul (pas encore de base partagée)")

if db:
    masque = re.sub(r"://([^:/@]+):[^@]*@", r"://\1:•••@", db)
    print("installation de la base :", masque)
    try:
        import psycopg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "psycopg[binary]"], check=True)
        import psycopg
    sql = open(os.path.join(INST, "galapsy-installation.sql"), encoding="utf-8").read()
    try:
        with psycopg.connect(db, autocommit=True, connect_timeout=20) as cx:
            cx.execute(sql)
            nb = dict(cx.execute("select type, count(*) from galapsy.objets group by 1").fetchall())
    except Exception as e:
        message = re.sub(r"://([^:/@]+):[^@]*@", r"://\1:•••@", str(e)).strip()
        sys.exit("La base n'a pas pu être installée : " + message
                 + "\nVérifiez SUPABASE_DB dans Netlify (chaîne « Session pooler », mot de passe compris).")
    print("base à jour :", ", ".join(f"{v} {k}" for k, v in sorted(nb.items())))
else:
    print("base : SUPABASE_DB non renseignée, rien à installer")
shutil.rmtree(INST, ignore_errors=True)
print("site prêt :", sum(len(f) for _, _, f in os.walk(SITE)), "fichiers")
