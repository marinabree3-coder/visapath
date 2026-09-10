
import os, sqlite3, secrets, hashlib, mimetypes, re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "visapath.db")
UPLOAD_DIR = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

ALLOWED = {".pdf",".png",".jpg",".jpeg",".doc",".docx"}

COUNTRIES = [
    ("Kenya","KE"),("Uganda","UG"),("Tanzania","TZ"),("Rwanda","RW"),
    ("Burundi","BI"),("South Sudan","SS"),("Nigeria","NG"),("Ghana","GH"),
    ("India","IN"),("Philippines","PH"),("United Kingdom","GB"),
    ("United States","US"),("Canada","CA"),("Australia","AU"),("Other","XX")
]
DESTINATIONS = ["Canada","United Kingdom","United States","Australia","New Zealand",
                "Schengen / Europe","UAE","Other"]
PURPOSES = ["Visitor / Tourist","Student","Work","Business","Family","Transit","Other"]

PACKAGES = {
    "basic": ("Basic Assessment", 15, "Preliminary case assessment and personalized checklist"),
    "standard": ("Standard Assessment", 35, "Detailed assessment, document review and readiness report"),
    "premium": ("Premium Human Review", 75, "Standard assessment plus consultant review"),
    "full": ("Full Application Support", 150, "Human-assisted application preparation and support")
}
CURRENCIES = {"USD":1,"KES":129,"UGX":3700,"TZS":2500,"RWF":1450,"NGN":1500,"GHS":11.5,"ZAR":17.2,"GBP":0.75,"EUR":0.86,"CAD":1.37,"AUD":1.52,"AED":3.67,"INR":83.5,"PHP":58.0}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'client', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS assessments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, nationality TEXT, residence TEXT,
      destination TEXT, purpose TEXT, travel_date TEXT, previous_refusal TEXT,
      visa_category TEXT, score INTEGER DEFAULT 0, status TEXT DEFAULT 'unpaid',
      package TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS documents(
      id INTEGER PRIMARY KEY AUTOINCREMENT, assessment_id INTEGER, filename TEXT, stored_name TEXT,
      size INTEGER, status TEXT DEFAULT 'uploaded', finding TEXT, uploaded_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT, assessment_id INTEGER, sender_role TEXT,
      body TEXT, created_at TEXT NOT NULL
    );
    """)
    # Demo consultant account (change password before production)
    if not con.execute("SELECT 1 FROM users WHERE email=?", ("consultant@visapath.local",)).fetchone():
        con.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                    ("VisaPath Consultant","consultant@visapath.local",hashpw("ChangeMe123!"),"consultant",datetime.utcnow().isoformat()))
    con.commit(); con.close()

def hashpw(p): return hashlib.sha256(p.encode()).hexdigest()
def current_user():
    uid=session.get("uid")
    if not uid: return None
    con=db(); u=con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone(); con.close(); return u

def login_required(f):
    @wraps(f)
    def w(*a,**kw):
        if not current_user():
            return redirect(url_for("login"))
        return f(*a,**kw)
    return w

def consultant_required(f):
    @wraps(f)
    def w(*a,**kw):
        u=current_user()
        if not u or u["role"]!="consultant": abort(403)
        return f(*a,**kw)
    return w

def recommend(destination, purpose):
    if purpose.startswith("Visitor"): return "Visitor Visa / Visitor Permission"
    if purpose=="Student": return "Student Visa / Study Permit"
    if purpose=="Work": return "Work Visa / Work Permit"
    if purpose=="Business": return "Business Visitor / Business Visa"
    if purpose=="Family": return "Family / Dependant Route"
    if purpose=="Transit": return "Transit Visa / Transit Permission"
    return f"Relevant {destination} visa category — human review recommended"

def score_case(previous_refusal, purpose, travel_date):
    score=70
    if previous_refusal=="Yes": score-=15
    if purpose=="Other": score-=5
    if not travel_date: score-=5
    return max(0,min(100,score))

@app.context_processor
def inject():
    return {"user":current_user(),"currencies":CURRENCIES,"countries":COUNTRIES,"destinations":DESTINATIONS,"purposes":PURPOSES}

@app.route("/")
def home(): return render_template("home.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower(); pw=request.form["password"]
        if len(pw)<8: flash("Password must be at least 8 characters."); return redirect(url_for("register"))
        con=db()
        try:
            cur=con.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                            (name,email,hashpw(pw),"client",datetime.utcnow().isoformat()))
            con.commit(); session["uid"]=cur.lastrowid; return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.")
        finally: con.close()
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower(); pw=hashpw(request.form["password"])
        con=db(); u=con.execute("SELECT * FROM users WHERE email=? AND password=?", (email,pw)).fetchone(); con.close()
        if u: session["uid"]=u["id"]; return redirect(url_for("consultant_dashboard") if u["role"]=="consultant" else url_for("dashboard"))
        flash("Invalid email or password.")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/assessment", methods=["GET","POST"])
def assessment():
    if request.method=="POST":
        data={k:request.form.get(k,"").strip() for k in ["nationality","residence","destination","purpose","travel_date","previous_refusal"]}
        visa=recommend(data["destination"],data["purpose"]); score=score_case(data["previous_refusal"],data["purpose"],data["travel_date"])
        session["free_result"]={**data,"visa_category":visa,"score":score}
        return redirect(url_for("assessment_result"))
    return render_template("assessment.html")

@app.route("/assessment/result")
def assessment_result():
    r=session.get("free_result")
    if not r: return redirect(url_for("assessment"))
    return render_template("assessment_result.html", r=r)

@app.route("/checkout/<package>", methods=["GET","POST"])
@login_required
def checkout(package):
    if package not in PACKAGES: abort(404)
    if request.method=="POST":
        r=session.get("free_result")
        if not r: flash("Please complete the free assessment first."); return redirect(url_for("assessment"))
        now=datetime.utcnow().isoformat(); con=db()
        cur=con.execute("""INSERT INTO assessments(user_id,nationality,residence,destination,purpose,travel_date,
          previous_refusal,visa_category,score,status,package,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?, ?,?)""",
          (current_user()["id"],r["nationality"],r["residence"],r["destination"],r["purpose"],r["travel_date"],
           r["previous_refusal"],r["visa_category"],r["score"],"paid",package,now,now))
        con.commit(); aid=cur.lastrowid; con.close()
        session.pop("free_result",None)
        flash("Payment demo successful. In production this button will call M-Pesa/card checkout and only unlock after verified payment.")
        return redirect(url_for("case",aid=aid))
    return render_template("checkout.html", package=package, details=PACKAGES[package])

@app.route("/dashboard")
@login_required
def dashboard():
    u=current_user(); con=db(); rows=con.execute("SELECT * FROM assessments WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall(); con.close()
    return render_template("dashboard.html", assessments=rows)

@app.route("/case/<int:aid>", methods=["GET","POST"])
@login_required
def case(aid):
    u=current_user(); con=db(); a=con.execute("SELECT * FROM assessments WHERE id=? AND user_id=?",(aid,u["id"])).fetchone()
    if not a: abort(404)
    docs=con.execute("SELECT * FROM documents WHERE assessment_id=? ORDER BY id DESC",(aid,)).fetchall()
    msgs=con.execute("SELECT * FROM messages WHERE assessment_id=? ORDER BY id",(aid,)).fetchall()
    if request.method=="POST":
        body=request.form.get("body","").strip()
        if body:
            con.execute("INSERT INTO messages(assessment_id,sender_role,body,created_at) VALUES(?,?,?,?)",(aid,"client",body,datetime.utcnow().isoformat()))
            con.commit(); con.close(); return redirect(url_for("case",aid=aid))
    con.close()
    findings=[]
    for d in docs:
        findings.append(d["finding"] or f"{d['filename']}: uploaded; detailed AI review can be connected in production.")
    return render_template("case.html", a=a, docs=docs, msgs=msgs, findings=findings)

@app.route("/case/<int:aid>/upload", methods=["POST"])
@login_required
def upload(aid):
    u=current_user(); con=db(); a=con.execute("SELECT id FROM assessments WHERE id=? AND user_id=?",(aid,u["id"])).fetchone()
    if not a: abort(404)
    f=request.files.get("document")
    if not f or not f.filename: flash("Choose a document."); return redirect(url_for("case",aid=aid))
    ext=os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED: flash("Allowed: PDF, JPG, JPEG, PNG, DOC, DOCX."); return redirect(url_for("case",aid=aid))
    safe=re.sub(r"[^A-Za-z0-9_.-]","_",f.filename)[:120]
    stored=f"{aid}_{secrets.token_hex(10)}_{safe}"
    path=os.path.join(UPLOAD_DIR,stored); f.save(path)
    finding=analyze_document_stub(safe, a["id"])
    con.execute("INSERT INTO documents(assessment_id,filename,stored_name,size,status,finding,uploaded_at) VALUES(?,?,?,?,?,?,?)",
                (aid,safe,stored,os.path.getsize(path),"reviewed",finding,datetime.utcnow().isoformat()))
    con.commit(); con.close()
    flash("Document uploaded and queued for review.")
    return redirect(url_for("case",aid=aid))

def analyze_document_stub(filename, aid):
    n=filename.lower()
    if "passport" in n: return "Passport detected by filename. Production AI should verify readability, identity fields and expiry against the case."
    if "bank" in n or "statement" in n: return "Financial document detected. Production AI should compare dates, balances, transaction patterns and declared income."
    if "employment" in n or "employer" in n: return "Employment evidence detected. Production AI should compare employer, role, salary and dates with the client's answers."
    if "invitation" in n: return "Invitation/support document detected. Production AI should verify names, dates, relationship and destination-specific requirements."
    return "Document uploaded. Production AI should classify it, extract relevant fields, compare against requirements and flag inconsistencies."

@app.route("/consultant")
@consultant_required
def consultant_dashboard():
    con=db()
    cases=con.execute("""SELECT a.*,u.name,u.email FROM assessments a JOIN users u ON u.id=a.user_id
                         ORDER BY a.updated_at DESC""").fetchall()
    con.close(); return render_template("consultant.html", cases=cases)

@app.route("/consultant/case/<int:aid>", methods=["GET","POST"])
@consultant_required
def consultant_case(aid):
    con=db(); a=con.execute("""SELECT a.*,u.name,u.email FROM assessments a JOIN users u ON u.id=a.user_id
                              WHERE a.id=?""",(aid,)).fetchone()
    if not a: abort(404)
    if request.method=="POST":
        body=request.form.get("body","").strip()
        if body:
            con.execute("INSERT INTO messages(assessment_id,sender_role,body,created_at) VALUES(?,?,?,?)",(aid,"consultant",body,datetime.utcnow().isoformat()))
            con.commit()
        return redirect(url_for("consultant_case",aid=aid))
    docs=con.execute("SELECT * FROM documents WHERE assessment_id=? ORDER BY id DESC",(aid,)).fetchall()
    msgs=con.execute("SELECT * FROM messages WHERE assessment_id=? ORDER BY id",(aid,)).fetchall()
    con.close(); return render_template("consultant_case.html",a=a,docs=docs,msgs=msgs)

@app.route("/files/<path:name>")
@consultant_required
def private_file(name):
    # Production: use object storage + signed URLs and stronger authorization.
    return send_from_directory(UPLOAD_DIR,name,as_attachment=True)

@app.route("/pricing")
def pricing(): return render_template("pricing.html", packages=PACKAGES)

@app.route("/about")
def about(): return render_template("about.html")

@app.route("/health")
def health(): return {"status":"ok","service":"VisaPath"}

init_db()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
