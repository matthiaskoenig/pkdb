"""Retire legacy upload drafts and ineffective reader grants.

Downgrade restores the schema, not expired drafts or ineffective grants.
"""

from alembic import op

revision = "p002retirelegacy"
down_revision = "p001initial"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("legacy_file_handles")
    op.drop_table("study_drafts")
    op.drop_table("reference_drafts")
    op.execute("DELETE FROM study_grants WHERE role = 'collaborator'")
    op.drop_constraint(op.f("ck_study_grants_role"), "study_grants", type_="check")
    op.create_check_constraint(
        op.f("ck_study_grants_role"), "study_grants", "role = 'curator'"
    )


def downgrade():
    op.drop_constraint(op.f("ck_study_grants_role"), "study_grants", type_="check")
    op.create_check_constraint(
        op.f("ck_study_grants_role"),
        "study_grants",
        "role IN ('curator', 'collaborator')",
    )
    op.execute("""
CREATE TABLE reference_drafts (
    owner_id INTEGER NOT NULL,
    sid VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_reference_drafts PRIMARY KEY (owner_id, sid),
    CONSTRAINT fk_reference_drafts_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);
""")
    op.execute(
        "CREATE INDEX ix_reference_drafts_expires_at ON reference_drafts (expires_at);"
    )
    op.execute("""
CREATE TABLE study_drafts (
    id UUID NOT NULL,
    owner_id INTEGER NOT NULL,
    sid VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    reference JSONB NOT NULL,
    sealed BOOLEAN NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_study_drafts PRIMARY KEY (id),
    CONSTRAINT uq_study_drafts_owner_id_sid UNIQUE (owner_id, sid),
    CONSTRAINT fk_study_drafts_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);
""")
    op.execute("CREATE INDEX ix_study_drafts_expires_at ON study_drafts (expires_at);")
    op.execute("""
CREATE TABLE legacy_file_handles (
    file_id UUID NOT NULL,
    id SERIAL NOT NULL,
    CONSTRAINT pk_legacy_file_handles PRIMARY KEY (id),
    CONSTRAINT uq_legacy_file_handles_file_id UNIQUE (file_id),
    CONSTRAINT fk_legacy_file_handles_file_id_files FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE CASCADE
);
""")
