"""
Migration 19.0.1.0.0 → 19.0.1.1.0

Context:
  agri.biological.batch was changed from models.Model to models.AbstractModel.
  agri.flock.batch is now a concrete model (own DB table: agri_flock_batch).

Problem:
  Existing data lives in agri_biological_batch (the old table).
  Gate tables (feed_log, mortality, egg_collection, etc.) have batch_id values
  pointing to rows in agri_biological_batch. After the refactor Odoo creates a
  new empty agri_flock_batch table and tries to add FK constraints — which fail
  because batch_id values don't exist in the new empty table.

Fix:
  Rename agri_biological_batch → agri_flock_batch BEFORE the ORM runs.
  Odoo's CREATE TABLE IF NOT EXISTS then finds the table already populated,
  alters columns as needed, and FK constraints pass immediately.
"""


def migrate(cr, version):
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'agri_biological_batch'
        )
    """)
    old_exists = cr.fetchone()[0]

    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'agri_flock_batch'
        )
    """)
    new_exists = cr.fetchone()[0]

    if old_exists and not new_exists:
        # Rename the data table
        cr.execute('ALTER TABLE agri_biological_batch RENAME TO agri_flock_batch')
        # Rename the primary key sequence (keeps nextval() working)
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.sequences
                WHERE sequence_schema = 'public'
                  AND sequence_name = 'agri_biological_batch_id_seq'
            )
        """)
        if cr.fetchone()[0]:
            cr.execute(
                'ALTER SEQUENCE agri_biological_batch_id_seq '
                'RENAME TO agri_flock_batch_id_seq'
            )
        # Rename the primary key constraint so pg doesn't complain
        cr.execute("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'agri_flock_batch'
              AND constraint_type = 'PRIMARY KEY'
        """)
        row = cr.fetchone()
        if row and row[0] == 'agri_biological_batch_pkey':
            cr.execute(
                'ALTER TABLE agri_flock_batch '
                'RENAME CONSTRAINT agri_biological_batch_pkey '
                'TO agri_flock_batch_pkey'
            )
