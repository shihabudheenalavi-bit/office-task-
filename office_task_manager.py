import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import io

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Office Task Manager",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f0f2f6; }

[data-testid="stSidebar"] { background: #1a1f2e !important; }
[data-testid="stSidebar"] * { color: #c9d1e0 !important; }

.metric-card {
    background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-left: 4px solid #4361ee;
    margin-bottom: 8px;
}
.metric-card.orange { border-left-color: #f97316; }
.metric-card.green  { border-left-color: #22c55e; }
.metric-card.red    { border-left-color: #ef4444; }
.metric-card.purple { border-left-color: #a855f7; }
.metric-card.blue   { border-left-color: #3b82f6; }
.metric-card.teal   { border-left-color: #14b8a6; }
.metric-num { font-size: 2rem; font-weight: 700; color: #1a1f2e; line-height: 1; }
.metric-lbl { font-size: 0.78rem; color: #6b7280; margin-top: 4px; font-weight: 500;
              letter-spacing: 0.04em; text-transform: uppercase; }

div.stButton > button {
    border-radius: 8px; font-weight: 600;
    font-family: 'DM Sans', sans-serif; transition: all 0.2s;
}

.page-title { font-size: 1.8rem; font-weight: 700; color: #1a1f2e; margin-bottom: 4px; }
.page-subtitle { font-size: 0.9rem; color: #6b7280; margin-bottom: 20px; }
.section-header {
    font-size: 1.1rem; font-weight: 700; color: #1a1f2e;
    margin-bottom: 10px; padding-bottom: 6px; border-bottom: 2px solid #e5e7eb;
}
</style>
""", unsafe_allow_html=True)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
DB_FILE = "office_tasks.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT NOT NULL,
            description    TEXT,
            department     TEXT,
            assigned_to    TEXT,
            priority       TEXT DEFAULT 'Medium',
            start_date     TEXT,
            due_date       TEXT,
            follow_up_date TEXT,
            status         TEXT DEFAULT 'Not Started',
            remarks        TEXT,
            created_at     TEXT DEFAULT (datetime('now','localtime')),
            updated_at     TEXT DEFAULT (datetime('now','localtime'))
        )""")
        conn.commit()

init_db()

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
DEPARTMENTS = [
    "Accounts", "HR", "Purchase", "Sales", "Supplier Follow-up",
    "Customer Follow-up", "VAT / Tax", "Cheque / Payment", "Insurance",
    "License / Renewal", "Management Approval", "General Office Work"
]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
STATUSES   = ["Not Started", "In Progress", "Pending", "Completed", "Cancelled"]

PRI_EMOJI  = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Urgent": "🔴"}
STA_EMOJI  = {"Not Started": "⬜", "In Progress": "🔵", "Pending": "🟡",
              "Completed": "✅", "Cancelled": "❌"}
PRI_COLOR  = {"Low": "#22c55e", "Medium": "#eab308", "High": "#f97316", "Urgent": "#ef4444"}
CARD_BG    = {"Low": "#f0fdf4", "Medium": "#fefce8", "High": "#fff7ed", "Urgent": "#fff1f2"}

# ─── DB HELPERS ───────────────────────────────────────────────────────────────
def load_tasks(filters=None):
    q = "SELECT * FROM tasks WHERE 1=1"
    p = []
    if filters:
        if filters.get("status") and filters["status"] != "All":
            q += " AND status=?"; p.append(filters["status"])
        if filters.get("priority") and filters["priority"] != "All":
            q += " AND priority=?"; p.append(filters["priority"])
        if filters.get("department") and filters["department"] != "All":
            q += " AND department=?"; p.append(filters["department"])
        if filters.get("assigned_to") and filters["assigned_to"] != "All":
            q += " AND assigned_to=?"; p.append(filters["assigned_to"])
        if filters.get("due_date"):
            q += " AND due_date=?"; p.append(filters["due_date"])
        if filters.get("overdue"):
            q += " AND due_date < ? AND status NOT IN ('Completed','Cancelled')"
            p.append(date.today().isoformat())
        if filters.get("follow_up_today"):
            q += " AND follow_up_date=?"; p.append(date.today().isoformat())
        if filters.get("due_this_week"):
            q += " AND due_date BETWEEN ? AND ?"
            p += [date.today().isoformat(), (date.today()+timedelta(days=7)).isoformat()]
        if filters.get("search"):
            s = f"%{filters['search']}%"
            q += " AND (title LIKE ? OR description LIKE ? OR assigned_to LIKE ?)"
            p += [s, s, s]
    q += " ORDER BY CASE priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, due_date ASC NULLS LAST"
    with get_conn() as conn:
        return pd.read_sql_query(q, conn, params=p)

def insert_task(data):
    with get_conn() as conn:
        conn.execute("""INSERT INTO tasks
            (title,description,department,assigned_to,priority,start_date,due_date,follow_up_date,status,remarks)
            VALUES (:title,:description,:department,:assigned_to,:priority,:start_date,:due_date,:follow_up_date,:status,:remarks)
        """, data); conn.commit()

def update_task(tid, data):
    data["id"] = tid
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute("""UPDATE tasks SET
            title=:title, description=:description, department=:department,
            assigned_to=:assigned_to, priority=:priority, start_date=:start_date,
            due_date=:due_date, follow_up_date=:follow_up_date, status=:status,
            remarks=:remarks, updated_at=:updated_at WHERE id=:id
        """, data); conn.commit()

def delete_task(tid):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (tid,)); conn.commit()

def mark_complete(tid):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET status='Completed',updated_at=datetime('now','localtime') WHERE id=?", (tid,))
        conn.commit()

def get_unique_employees():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT assigned_to FROM tasks WHERE assigned_to IS NOT NULL AND assigned_to!='' ORDER BY assigned_to"
        ).fetchall()
    return ["All"] + [r[0] for r in rows]

def dashboard_stats():
    today    = date.today().isoformat()
    week_end = (date.today()+timedelta(days=7)).isoformat()
    with get_conn() as conn:
        def q(sql, p=()):
            return conn.execute(sql, p).fetchone()[0]
        return {
            "total":         q("SELECT COUNT(*) FROM tasks"),
            "pending":       q("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('Completed','Cancelled')"),
            "completed":     q("SELECT COUNT(*) FROM tasks WHERE status='Completed'"),
            "overdue":       q("SELECT COUNT(*) FROM tasks WHERE due_date<? AND status NOT IN ('Completed','Cancelled')",(today,)),
            "high_pri":      q("SELECT COUNT(*) FROM tasks WHERE priority IN ('High','Urgent') AND status NOT IN ('Completed','Cancelled')"),
            "due_today":     q("SELECT COUNT(*) FROM tasks WHERE due_date=? AND status NOT IN ('Completed','Cancelled')",(today,)),
            "due_week":      q("SELECT COUNT(*) FROM tasks WHERE due_date BETWEEN ? AND ? AND status NOT IN ('Completed','Cancelled')",(today,week_end)),
            "follow_today":  q("SELECT COUNT(*) FROM tasks WHERE follow_up_date=? AND status NOT IN ('Completed','Cancelled')",(today,)),
        }

def export_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Tasks")
        ws = w.sheets["Tasks"]
        for col in ws.columns:
            ml = max(len(str(c.value or "")) for c in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(ml, 40)
    return out.getvalue()

def is_overdue(row):
    try:
        if row.get("due_date") and row.get("status") not in ("Completed","Cancelled"):
            return date.fromisoformat(row["due_date"]) < date.today()
    except:
        pass
    return False

# ─── COMPACT TASK ROW ────────────────────────────────────────────────────────
def render_task_card(row, show_complete_btn=True, show_edit_btn=True, show_delete_btn=True, key_prefix="tc"):
    overdue = is_overdue(row)
    pri     = row["priority"]
    sta     = row["status"]
    border  = "#ef4444" if overdue else PRI_COLOR.get(pri, "#e5e7eb")
    bg      = "#fff5f5" if overdue else CARD_BG.get(pri, "#ffffff")

    overdue_tag = " 🚨" if overdue else ""
    due_str = row["due_date"] or "—"
    emp_str = row["assigned_to"] or "—"
    dep_str = row["department"] or "—"
    bk      = f"{key_prefix}_{row['id']}"

    # Compact single-line layout: colored strip | title+meta | badges | buttons
    st.markdown(
        f"""<div style="
            display:flex; align-items:center; gap:10px;
            background:{bg}; border-left:4px solid {border};
            border-radius:8px; padding:7px 12px; margin-bottom:4px;
            font-size:0.85rem; line-height:1.3;
        ">
            <span style="font-weight:600;min-width:0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                <span style="color:#6b7280;">#{row['id']}</span> {row['title']}{overdue_tag}
            </span>
            <span style="white-space:nowrap;color:#6b7280;font-size:0.78rem;">
                👤{emp_str} &nbsp;🏢{dep_str} &nbsp;📅{due_str}
            </span>
            <span style="white-space:nowrap;font-size:0.78rem;">
                {PRI_EMOJI.get(pri,'⚪')}&nbsp;<code style="font-size:0.72rem;">{pri}</code>
                &nbsp;{STA_EMOJI.get(sta,'⬜')}&nbsp;<code style="font-size:0.72rem;">{sta}</code>
            </span>
        </div>""",
        unsafe_allow_html=True,
    )

    # Action buttons on same visual row using st.columns
    if show_complete_btn or show_edit_btn or show_delete_btn:
        b1, b2, b3, _ = st.columns([0.7, 0.7, 0.7, 6])
        if show_edit_btn:
            with b1:
                if st.button("✏️", key=f"edit_{bk}", help="Edit"):
                    st.session_state.edit_id = int(row["id"])
                    st.rerun()
        if show_complete_btn and sta != "Completed":
            with b2:
                if st.button("✅", key=f"done_{bk}", help="Mark Done → moves to Completed"):
                    mark_complete(int(row["id"]))
                    st.toast(f"✅ Task #{row['id']} moved to Completed!", icon="✅")
                    st.rerun()
        if show_delete_btn:
            with b3:
                if st.button("🗑️", key=f"del_{bk}", help="Delete"):
                    delete_task(int(row["id"]))
                    st.rerun()


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px 0;">
        <div style="font-size:1.3rem;font-weight:700;color:#fff;">📋 Task Manager</div>
        <div style="font-size:0.75rem;color:#6b7caa;margin-top:2px;">Office Workflow System</div>
    </div>
    <hr style="margin:8px 0 16px 0;border-color:#2d3348;">
    """, unsafe_allow_html=True)

    page = st.radio("Navigation", [
        "🏠  Dashboard",
        "➕  Add New Task",
        "📋  Task List",
        "🔔  Follow-up Tasks",
        "📊  Reports & Export",
    ], label_visibility="collapsed")

    st.markdown(f"""
    <hr style="margin:16px 0 12px 0;border-color:#2d3348;">
    <div style="font-size:0.75rem;color:#6b7caa;text-align:center;">
        {date.today().strftime("%A, %d %b %Y")}
    </div>
    """, unsafe_allow_html=True)

page_key = page.split("  ")[1]

# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
if page_key == "Dashboard":
    st.markdown('<div class="page-title">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Live overview of all office tasks</div>', unsafe_allow_html=True)

    s = dashboard_stats()

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><div class="metric-num">{s["total"]}</div><div class="metric-lbl">Total Tasks</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card orange"><div class="metric-num">{s["pending"]}</div><div class="metric-lbl">Active / Pending</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card green"><div class="metric-num">{s["completed"]}</div><div class="metric-lbl">Completed</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card red"><div class="metric-num">{s["overdue"]}</div><div class="metric-lbl">Overdue</div></div>', unsafe_allow_html=True)

    c5,c6,c7,c8 = st.columns(4)
    with c5: st.markdown(f'<div class="metric-card purple"><div class="metric-num">{s["high_pri"]}</div><div class="metric-lbl">High Priority</div></div>', unsafe_allow_html=True)
    with c6: st.markdown(f'<div class="metric-card blue"><div class="metric-num">{s["due_today"]}</div><div class="metric-lbl">Due Today</div></div>', unsafe_allow_html=True)
    with c7: st.markdown(f'<div class="metric-card teal"><div class="metric-num">{s["due_week"]}</div><div class="metric-lbl">Due This Week</div></div>', unsafe_allow_html=True)
    with c8: st.markdown(f'<div class="metric-card orange"><div class="metric-num">{s["follow_today"]}</div><div class="metric-lbl">Follow-up Today</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-header">⚠️ Overdue Tasks</div>', unsafe_allow_html=True)
        ov = load_tasks({"overdue": True})
        if ov.empty:
            st.success("✅ No overdue tasks!")
        else:
            for _, row in ov.head(5).iterrows():
                days_late = (date.today() - date.fromisoformat(row["due_date"])).days
                st.error(f"🔴 **#{row['id']} — {row['title']}** | {days_late}d late | 👤 {row['assigned_to'] or '—'} | 🏢 {row['department'] or '—'}")

    with col_b:
        st.markdown('<div class="section-header">📅 Due Today</div>', unsafe_allow_html=True)
        td = load_tasks({"due_date": date.today().isoformat()})
        if td.empty:
            st.info("No tasks due today.")
        else:
            for _, row in td.head(5).iterrows():
                pri_e = PRI_EMOJI.get(row["priority"], "⚪")
                sta_e = STA_EMOJI.get(row["status"], "⬜")
                st.warning(f"{pri_e} **#{row['id']} — {row['title']}** {sta_e} `{row['status']}` | 👤 {row['assigned_to'] or '—'}")

    st.markdown("---")
    st.markdown('<div class="section-header">🏢 Active Tasks by Department</div>', unsafe_allow_html=True)
    all_df = load_tasks()
    if not all_df.empty:
        dept_df = (all_df[all_df["status"].isin(["Not Started","In Progress","Pending"])]
                   .groupby("department").size().reset_index(name="Active Tasks")
                   .sort_values("Active Tasks", ascending=False))
        if not dept_df.empty:
            st.bar_chart(dept_df.set_index("department"), height=240)
        else:
            st.info("No active tasks.")

# ═══════════════════════════════════════════════════════════════════════════
# ADD NEW TASK
# ═══════════════════════════════════════════════════════════════════════════
elif page_key == "Add New Task":
    st.markdown('<div class="page-title">➕ Add New Task</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Create a new office task or work item</div>', unsafe_allow_html=True)

    with st.form("add_task_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            title      = st.text_input("Task Title *", placeholder="e.g. Follow up with supplier ABC")
            department = st.selectbox("Department / Category *", DEPARTMENTS)
            priority   = st.selectbox("Priority", PRIORITIES, index=1)
            start_date = st.date_input("Start Date", value=date.today())
        with c2:
            assigned_to    = st.text_input("Assigned To *", placeholder="Employee name")
            status         = st.selectbox("Status", STATUSES)
            due_date       = st.date_input("Due Date", value=date.today())
            follow_up_date = st.date_input("Follow-up Date", value=None)

        description = st.text_area("Task Description", placeholder="Describe the task in detail...", height=100)
        remarks     = st.text_area("Remarks / Notes", placeholder="Any additional notes or instructions...", height=80)

        submitted = st.form_submit_button("💾 Save Task", use_container_width=True, type="primary")

    if submitted:
        if not title.strip():
            st.error("❌ Task Title is required.")
        elif not assigned_to.strip():
            st.error("❌ Assigned To is required.")
        else:
            insert_task({
                "title": title.strip(), "description": description.strip(),
                "department": department, "assigned_to": assigned_to.strip(),
                "priority": priority,
                "start_date": start_date.isoformat(), "due_date": due_date.isoformat(),
                "follow_up_date": follow_up_date.isoformat() if follow_up_date else None,
                "status": status, "remarks": remarks.strip(),
            })
            st.success(f"✅ Task **'{title}'** saved successfully!")
            st.balloons()

# ═══════════════════════════════════════════════════════════════════════════
# TASK LIST
# ═══════════════════════════════════════════════════════════════════════════
elif page_key == "Task List":
    st.markdown('<div class="page-title">📋 Task List</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">View, filter, edit and manage all tasks</div>', unsafe_allow_html=True)

    if "edit_id" not in st.session_state:
        st.session_state.edit_id = None

    # ── Edit panel (shown at top when editing) ──
    if st.session_state.edit_id:
        eid = st.session_state.edit_id
        with get_conn() as conn:
            r = conn.execute("SELECT * FROM tasks WHERE id=?", (eid,)).fetchone()
        if r:
            t = dict(r)
            st.info(f"✏️ Editing Task **#{eid}: {t['title']}**")
            with st.form("edit_form"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_title = st.text_input("Title", value=t["title"])
                    e_dept  = st.selectbox("Department", DEPARTMENTS,
                                index=DEPARTMENTS.index(t["department"]) if t["department"] in DEPARTMENTS else 0)
                    e_pri   = st.selectbox("Priority", PRIORITIES,
                                index=PRIORITIES.index(t["priority"]) if t["priority"] in PRIORITIES else 1)
                    e_start = st.date_input("Start Date",
                                value=date.fromisoformat(t["start_date"]) if t["start_date"] else date.today())
                with ec2:
                    e_assigned = st.text_input("Assigned To", value=t["assigned_to"] or "")
                    e_status   = st.selectbox("Status", STATUSES,
                                index=STATUSES.index(t["status"]) if t["status"] in STATUSES else 0)
                    e_due  = st.date_input("Due Date",
                                value=date.fromisoformat(t["due_date"]) if t["due_date"] else date.today())
                    e_fup  = st.date_input("Follow-up Date",
                                value=date.fromisoformat(t["follow_up_date"]) if t["follow_up_date"] else None)
                e_desc    = st.text_area("Description", value=t["description"] or "", height=80)
                e_remarks = st.text_area("Remarks", value=t["remarks"] or "", height=60)
                sc1, sc2 = st.columns(2)
                with sc1: save   = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
                with sc2: cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

            if save:
                update_task(eid, {
                    "title": e_title, "description": e_desc, "department": e_dept,
                    "assigned_to": e_assigned, "priority": e_pri,
                    "start_date": e_start.isoformat(), "due_date": e_due.isoformat(),
                    "follow_up_date": e_fup.isoformat() if e_fup else None,
                    "status": e_status, "remarks": e_remarks,
                })
                st.success("✅ Task updated!")
                st.session_state.edit_id = None
                st.rerun()
            if cancel:
                st.session_state.edit_id = None
                st.rerun()
        st.markdown("---")

    # ── Filters ──
    with st.expander("🔍 Search & Filters", expanded=True):
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1: f_search   = st.text_input("Search", placeholder="Title / Person…")
        with fc2: f_status   = st.selectbox("Status",     ["All"] + STATUSES)
        with fc3: f_priority = st.selectbox("Priority",   ["All"] + PRIORITIES)
        with fc4: f_dept     = st.selectbox("Department", ["All"] + DEPARTMENTS)
        with fc5: f_emp      = st.selectbox("Employee",   get_unique_employees())

        qc1, qc2, qc3 = st.columns(3)
        with qc1: today_only  = st.checkbox("📅 Due Today")
        with qc2: overdue_only = st.checkbox("⚠️ Overdue Only")
        with qc3: week_only   = st.checkbox("📆 Due This Week")

    filters = {
        "search": f_search or None,
        "status": f_status, "priority": f_priority,
        "department": f_dept, "assigned_to": f_emp,
    }
    if today_only:   filters["due_date"] = date.today().isoformat()
    if overdue_only: filters["overdue"] = True
    if week_only:    filters["due_this_week"] = True

    df = load_tasks(filters)

    # Split into active vs completed
    df_active    = df[df["status"] != "Completed"]
    df_completed = df[df["status"] == "Completed"]

    tab_active, tab_done = st.tabs([
        f"📋 Active Tasks ({len(df_active)})",
        f"✅ Completed Tasks ({len(df_completed)})",
    ])

    with tab_active:
        if df_active.empty:
            st.success("🎉 No active tasks match your filters!")
        else:
            for _, row in df_active.iterrows():
                render_task_card(row, key_prefix="tl")

    with tab_done:
        if df_completed.empty:
            st.info("No completed tasks match your filters.")
        else:
            st.markdown("<div style='font-size:0.82rem;color:#6b7280;margin-bottom:6px;'>Tasks marked ✅ Done appear here automatically.</div>", unsafe_allow_html=True)
            for _, row in df_completed.iterrows():
                render_task_card(row, show_complete_btn=False, key_prefix="tld")

# ═══════════════════════════════════════════════════════════════════════════
# FOLLOW-UP TASKS
# ═══════════════════════════════════════════════════════════════════════════
elif page_key == "Follow-up Tasks":
    st.markdown('<div class="page-title">🔔 Follow-up Tasks</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Tasks requiring follow-up action today or overdue</div>', unsafe_allow_html=True)

    if "edit_id" not in st.session_state:
        st.session_state.edit_id = None

    tab1, tab2, tab3 = st.tabs(["📅 Follow-up Today", "⚠️ Overdue Tasks", "⏳ Pending Approval"])

    with tab1:
        fup = load_tasks({"follow_up_today": True})
        if fup.empty:
            st.success("✅ No follow-up tasks scheduled for today!")
        else:
            st.info(f"📌 {len(fup)} task(s) need follow-up today")
            for _, row in fup.iterrows():
                render_task_card(row, key_prefix="fu")

    with tab2:
        overdue = load_tasks({"overdue": True})
        if overdue.empty:
            st.success("✅ No overdue tasks!")
        else:
            st.warning(f"⚠️ {len(overdue)} overdue task(s) require immediate attention")
            for _, row in overdue.iterrows():
                days_late = (date.today() - date.fromisoformat(row["due_date"])).days
                st.error(f"🔴 **#{row['id']} — {row['title']}** — {days_late} day(s) overdue | 👤 {row['assigned_to'] or '—'} | 🏢 {row['department'] or '—'} | Due: {row['due_date']}")

    with tab3:
        approvals = load_tasks({"department": "Management Approval"})
        active    = approvals[approvals["status"].isin(["Not Started","In Progress","Pending"])]
        if active.empty:
            st.success("✅ No pending approvals!")
        else:
            st.info(f"⏳ {len(active)} item(s) pending management approval")
            for _, row in active.iterrows():
                render_task_card(row, key_prefix="ap")

# ═══════════════════════════════════════════════════════════════════════════
# REPORTS & EXPORT
# ═══════════════════════════════════════════════════════════════════════════
elif page_key == "Reports & Export":
    st.markdown('<div class="page-title">📊 Reports & Export</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Generate reports and export task data to Excel</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📤 Export to Excel", "✅ Completed Tasks", "⏳ Pending Tasks"])

    with tab1:
        st.markdown("### Export Task Data")
        ec1, ec2, ec3 = st.columns(3)
        with ec1: exp_status = st.selectbox("Filter by Status",     ["All"] + STATUSES,     key="exp_s")
        with ec2: exp_dept   = st.selectbox("Filter by Department", ["All"] + DEPARTMENTS,  key="exp_d")
        with ec3: exp_pri    = st.selectbox("Filter by Priority",   ["All"] + PRIORITIES,   key="exp_p")

        exp_df = load_tasks({"status": exp_status, "priority": exp_pri, "department": exp_dept})
        st.markdown(f"**{len(exp_df)} task(s)** will be exported.")

        if not exp_df.empty:
            st.download_button(
                "📥 Download Excel File", data=export_excel(exp_df),
                file_name=f"office_tasks_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, type="primary",
            )
            st.dataframe(exp_df.drop(columns=["id"], errors="ignore"), use_container_width=True, height=300)

    with tab2:
        done = load_tasks({"status": "Completed"})
        st.markdown(f"### ✅ Completed Tasks ({len(done)})")
        if done.empty:
            st.info("No completed tasks yet.")
        else:
            st.download_button("📥 Export Completed Tasks", data=export_excel(done),
                file_name=f"completed_tasks_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.dataframe(done.drop(columns=["id"], errors="ignore"), use_container_width=True)

    with tab3:
        pend = load_tasks({"status": "Pending"})
        st.markdown(f"### ⏳ Pending Tasks ({len(pend)})")
        if pend.empty:
            st.info("No pending tasks.")
        else:
            st.download_button("📥 Export Pending Tasks", data=export_excel(pend),
                file_name=f"pending_tasks_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.dataframe(pend.drop(columns=["id"], errors="ignore"), use_container_width=True)
