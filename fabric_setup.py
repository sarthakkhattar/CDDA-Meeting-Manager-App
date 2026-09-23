# Fabric notebook source

# COMMAND ----------

# ============================================================
# CDDA Meeting Manager — Fabric Lakehouse Setup
# ============================================================
# Run this notebook in Microsoft Fabric to create/reset all
# Delta tables for the CDDA Meeting Manager app.
#
# Safe to re-run: uses mode="overwrite" with overwriteSchema.
# ============================================================

WORKSPACE_ID = "5ae09992-0e1e-4e48-9def-afea97d3bbdf"
LAKEHOUSE_ID = "ad02f13b-9478-454d-b9c2-a0f4e9afae9c"

print(f"Workspace: {WORKSPACE_ID}")
print(f"Lakehouse: {LAKEHOUSE_ID}")
print(f"Tables path: abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/dbo/")

# COMMAND ----------

# ============================================================
# Cell 2 — Create all 5 tables with seed data
# ============================================================

from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, BooleanType
)
from datetime import date, timedelta

# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

meetings_schema = StructType([
    StructField("id",          StringType(),  False),
    StructField("title",       StringType(),  False),
    StructField("description", StringType(),  True),
    StructField("forum",       StringType(),  False),
    StructField("duration",    IntegerType(), False),
    StructField("created_at",  StringType(),  False),
])

instances_schema = StructType([
    StructField("id",           StringType(),  False),
    StructField("meeting_id",   StringType(),  False),
    StructField("date",         StringType(),  False),
    StructField("display_text", StringType(),  False),
    StructField("is_available", BooleanType(), False),
])

agenda_schema = StructType([
    StructField("id",          StringType(),  False),
    StructField("meeting_id",  StringType(),  False),
    StructField("instance_id", StringType(),  False),
    StructField("title",       StringType(),  False),
    StructField("topic",       StringType(),  True),
    StructField("duration",    IntegerType(), False),
    StructField("presenter",   StringType(),  True),
    StructField("status",      StringType(),  False),
    StructField("item_order",  IntegerType(), False),
    StructField("created_at",  StringType(),  False),
])

documents_schema = StructType([
    StructField("id",          StringType(),  False),
    StructField("item_id",     StringType(),  False),
    StructField("filename",    StringType(),  False),
    StructField("doc_type",    StringType(),  True),
    StructField("file_size",   IntegerType(), True),
    StructField("uploaded_at", StringType(),  False),
])

approvals_schema = StructType([
    StructField("id",          StringType(),  False),
    StructField("item_id",     StringType(),  False),
    StructField("approver",    StringType(),  False),
    StructField("approved",    BooleanType(), False),
    StructField("approved_at", StringType(),  True),
])

# ------------------------------------------------------------------
# 1. cdda_meetings  (2 seed rows)
# ------------------------------------------------------------------

meetings_data = [
    (
        "mtg_1",
        "CDDA Open Office Hours",
        (
            "Open forum for CDDA knowledge sharing, Q&A, and cross-functional "
            "collaboration. Topics include statistical methodology updates, "
            "tool demonstrations, process improvements, and best practice discussions."
        ),
        "ooh",
        60,
        "2026-09-15T10:00:00",
    ),
    (
        "mtg_2",
        "Clinical Design & Statistics Review (CDSR)",
        (
            "Formal review of clinical study designs, statistical analysis plans, "
            "and data strategy. Ensures alignment with regulatory standards, "
            "scientific rigor, and cross-therapeutic consistency."
        ),
        "cdsr",
        90,
        "2026-09-15T10:00:00",
    ),
]

df_meetings = spark.createDataFrame(meetings_data, schema=meetings_schema)
df_meetings.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("cdda_meetings")
print("cdda_meetings ......... OK")

# ------------------------------------------------------------------
# 2. meeting_instances  (generated programmatically)
# ------------------------------------------------------------------

# OOH — every Monday, Oct 6 2026 → Dec 28 2026
ooh_start = date(2026, 10, 6)   # Monday
ooh_end   = date(2026, 12, 28)

ooh_dates = []
d = ooh_start
while d <= ooh_end:
    ooh_dates.append(d)
    d += timedelta(days=7)

# CDSR — every other Friday, Oct 3 2026 → Dec 26 2026
cdsr_start = date(2026, 10, 3)  # Friday
cdsr_end   = date(2026, 12, 26)

cdsr_dates = []
d = cdsr_start
while d <= cdsr_end:
    cdsr_dates.append(d)
    d += timedelta(days=14)

# Build instance rows with sequential IDs
instances_data = []
idx = 1

ooh_instance_ids = []
for dt in ooh_dates:
    inst_id = f"inst_{idx}"
    ooh_instance_ids.append(inst_id)
    instances_data.append((
        inst_id,
        "mtg_1",
        dt.strftime("%Y-%m-%d"),
        dt.strftime("%d %b %Y"),
        True,
    ))
    idx += 1

cdsr_instance_ids = []
for dt in cdsr_dates:
    inst_id = f"inst_{idx}"
    cdsr_instance_ids.append(inst_id)
    instances_data.append((
        inst_id,
        "mtg_2",
        dt.strftime("%Y-%m-%d"),
        dt.strftime("%d %b %Y"),
        True,
    ))
    idx += 1

print(f"  Generated {len(ooh_instance_ids)} OOH Mondays, {len(cdsr_instance_ids)} CDSR Fridays")

df_instances = spark.createDataFrame(instances_data, schema=instances_schema)
df_instances.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("meeting_instances")
print("meeting_instances ..... OK")

# ------------------------------------------------------------------
# 3. agenda_items  (6 seed rows)
# ------------------------------------------------------------------

first_ooh_id  = ooh_instance_ids[0]   # first OOH Monday
third_ooh_id  = ooh_instance_ids[2]   # third OOH Monday
first_cdsr_id = cdsr_instance_ids[0]  # first CDSR Friday

agenda_data = [
    # --- First OOH date: 3 items ---
    (
        "ag_1", "mtg_1", first_ooh_id,
        "Adaptive Design Framework Update",
        "Statistical Methodology",
        20, "Dr. Sarah Chen", "Pending", 1,
        "2026-09-15T10:30:00",
    ),
    (
        "ag_2", "mtg_1", first_ooh_id,
        "New CDDA Visualization Tool Demo",
        "Tool Demo",
        15, "James Rodriguez", "Pending", 2,
        "2026-09-16T14:30:00",
    ),
    (
        "ag_3", "mtg_1", first_ooh_id,
        "Q3 Metrics & Portfolio Review",
        "Metrics Review",
        25, "Emily Watson", "Pending", 3,
        "2026-09-17T09:00:00",
    ),
    # --- Third OOH date: 1 item ---
    (
        "ag_4", "mtg_1", third_ooh_id,
        "Bayesian Analysis Best Practices",
        "Statistical Methodology",
        30, "Dr. Michael Park", "Pending", 1,
        "2026-09-20T11:00:00",
    ),
    # --- First CDSR date: 2 items ---
    (
        "ag_5", "mtg_2", first_cdsr_id,
        "Phase III Oncology Study Design Review",
        "Study Design",
        45, "Dr. Lisa Thompson", "Pending", 1,
        "2026-09-18T08:30:00",
    ),
    (
        "ag_6", "mtg_2", first_cdsr_id,
        "Sample Size Re-estimation Strategy",
        "Statistical Analysis",
        30, "Dr. Robert Kim", "Pending", 2,
        "2026-09-19T13:00:00",
    ),
]

df_agenda = spark.createDataFrame(agenda_data, schema=agenda_schema)
df_agenda.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("agenda_items")
print("agenda_items .......... OK")

# ------------------------------------------------------------------
# 4. documents  (empty)
# ------------------------------------------------------------------

df_documents = spark.createDataFrame([], schema=documents_schema)
df_documents.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("documents")
print("documents ............. OK")

# ------------------------------------------------------------------
# 5. approvals  (empty)
# ------------------------------------------------------------------

df_approvals = spark.createDataFrame([], schema=approvals_schema)
df_approvals.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("approvals")
print("approvals ............. OK")

print("\nAll 5 tables created.")

# COMMAND ----------

# ============================================================
# Cell 3 — Verify all tables
# ============================================================

tables = ["cdda_meetings", "meeting_instances", "agenda_items", "documents", "approvals"]

print("Table summary:")
print("-" * 60)
for t in tables:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {t}").collect()[0]["cnt"]
    cols = spark.sql(f"DESCRIBE {t}").select("col_name").collect()
    col_names = [c["col_name"] for c in cols]
    print(f"  {t}: {count} rows, columns: {col_names}")

print("\nSample data:")
display(spark.sql("SELECT id, title, forum, duration FROM cdda_meetings"))
display(spark.sql("SELECT id, meeting_id, date, display_text FROM meeting_instances LIMIT 10"))
display(spark.sql("SELECT id, meeting_id, instance_id, title, status FROM agenda_items"))

# COMMAND ----------

# ============================================================
# Cell 4 — Connection test (optional, for debugging)
# ============================================================
# Run this to verify the abfss path works.
# Only needed for debugging — the app uses this path pattern.

path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/dbo/cdda_meetings"
df = spark.read.format("delta").load(path)
print(f"Connection OK — {df.count()} meetings via abfss:// path")
