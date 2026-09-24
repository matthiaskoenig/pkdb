"""Initial schema for fresh installations of the unified data model.

This is a frozen schema snapshot. Existing databases must be recreated and their
studies uploaded again; this revision does not upgrade historical schemas.
"""

from alembic import op

revision = "p001initial"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = r"""
CREATE SEQUENCE dataset_row_id_seq;

CREATE TABLE account_throttles (
    key VARCHAR(64) NOT NULL,
    attempts INTEGER NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_account_throttles PRIMARY KEY (key)
);

CREATE INDEX ix_account_throttles_expires_at ON account_throttles (expires_at);

CREATE TABLE "references" (
    sid VARCHAR(255) NOT NULL,
    name VARCHAR NOT NULL,
    pmid VARCHAR,
    doi VARCHAR,
    title VARCHAR,
    abstract VARCHAR,
    journal VARCHAR,
    date DATE,
    id SERIAL NOT NULL,
    CONSTRAINT pk_references PRIMARY KEY (id),
    CONSTRAINT uq_references_sid UNIQUE (sid)
);

CREATE INDEX ix_references_search ON "references" USING gin (to_tsvector('simple', (((((((coalesce(sid, '') || ' ') || coalesce(name, '')) || ' ') || coalesce(pmid, '')) || ' ') || coalesce(title, '')) || ' ') || coalesce(abstract, '')));

CREATE TABLE user_import_runs (
    digest VARCHAR(64) NOT NULL,
    provenance JSONB NOT NULL,
    report JSONB NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_user_import_runs PRIMARY KEY (id),
    CONSTRAINT uq_user_import_runs_digest UNIQUE (digest)
);

CREATE TABLE users (
    username VARCHAR(150) NOT NULL,
    email VARCHAR(320),
    role VARCHAR(16) DEFAULT 'user' NOT NULL,
    active BOOLEAN NOT NULL,
    suspended_at TIMESTAMP WITH TIME ZONE,
    first_name VARCHAR DEFAULT '' NOT NULL,
    last_name VARCHAR DEFAULT '' NOT NULL,
    pending_verification BOOLEAN DEFAULT 'false' NOT NULL,
    password_hash VARCHAR,
    display_name VARCHAR(200),
    affiliation VARCHAR(250),
    title VARCHAR(100),
    github VARCHAR(39),
    orcid VARCHAR(19),
    github_visible BOOLEAN DEFAULT 'true' NOT NULL,
    orcid_visible BOOLEAN DEFAULT 'true' NOT NULL,
    github_provenance VARCHAR(16),
    orcid_provenance VARCHAR(16),
    profile_edited_fields JSONB DEFAULT '[]' NOT NULL,
    avatar_key VARCHAR(32),
    avatar_initialized BOOLEAN DEFAULT 'false' NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT ck_users_role CHECK (role IN ('admin', 'curator', 'reviewer', 'user')),
    CONSTRAINT uq_users_username UNIQUE (username)
);

CREATE UNIQUE INDEX uq_users_sole_admin ON users (role) WHERE role = 'admin';

CREATE UNIQUE INDEX uq_users_username_lower ON users (lower(username));

CREATE TABLE vocabulary_nodes (
    sid VARCHAR(255) NOT NULL,
    name VARCHAR NOT NULL,
    kind VARCHAR(32) NOT NULL,
    definition JSONB NOT NULL,
    mass FLOAT,
    formula VARCHAR,
    charge INTEGER,
    CONSTRAINT pk_vocabulary_nodes PRIMARY KEY (sid),
    CONSTRAINT ck_vocabulary_nodes_positive_mass CHECK (mass IS NULL OR mass > 0)
);

CREATE INDEX ix_vocabulary_nodes_kind ON vocabulary_nodes (kind);

CREATE INDEX ix_vocabulary_nodes_name ON vocabulary_nodes (name);

CREATE INDEX ix_vocabulary_nodes_search ON vocabulary_nodes USING gin (to_tsvector('simple', (coalesce(sid, '') || ' ') || coalesce(name, '')));

CREATE TABLE vocabulary_version (
    id INTEGER NOT NULL,
    version VARCHAR NOT NULL,
    CONSTRAINT pk_vocabulary_version PRIMARY KEY (id),
    CONSTRAINT ck_vocabulary_version_singleton CHECK (id = 1)
);

CREATE TABLE work_leases (
    request_id VARCHAR(32) NOT NULL,
    bucket VARCHAR(100) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_work_leases PRIMARY KEY (request_id, bucket)
);

CREATE INDEX ix_work_leases_expires_at ON work_leases (expires_at);

CREATE TABLE api_keys (
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    prefix VARCHAR(24) NOT NULL,
    digest VARCHAR(64) NOT NULL,
    scopes JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    rotated_from_id INTEGER,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_api_keys PRIMARY KEY (id),
    CONSTRAINT fk_api_keys_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_api_keys_digest UNIQUE (digest),
    CONSTRAINT fk_api_keys_rotated_from_id_api_keys FOREIGN KEY(rotated_from_id) REFERENCES api_keys (id) ON DELETE SET NULL
);

CREATE INDEX ix_api_keys_user_id ON api_keys (user_id);

CREATE TABLE audit_events (
    actor_id INTEGER,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(200) NOT NULL,
    details JSONB NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_audit_events PRIMARY KEY (id),
    CONSTRAINT fk_audit_events_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE avatar_assets (
    key VARCHAR(32) NOT NULL,
    user_id INTEGER NOT NULL,
    media_type VARCHAR(32) NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    source_kind VARCHAR(32) NOT NULL,
    provenance JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_avatar_assets PRIMARY KEY (key),
    CONSTRAINT fk_avatar_assets_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_avatar_assets_user_id ON avatar_assets (user_id);

CREATE TABLE browser_sessions (
    user_id INTEGER NOT NULL,
    digest VARCHAR(64) NOT NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    authenticated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    device VARCHAR(200) NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_browser_sessions PRIMARY KEY (id),
    CONSTRAINT fk_browser_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_browser_sessions_digest UNIQUE (digest)
);

CREATE INDEX ix_browser_sessions_user_id ON browser_sessions (user_id);

CREATE TABLE email_addresses (
    user_id INTEGER NOT NULL,
    email VARCHAR(320) NOT NULL,
    is_primary BOOLEAN NOT NULL,
    is_verified BOOLEAN NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_email_addresses PRIMARY KEY (id),
    CONSTRAINT fk_email_addresses_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_email_addresses_email UNIQUE (email)
);

CREATE INDEX ix_email_addresses_user_id ON email_addresses (user_id);

CREATE UNIQUE INDEX uq_email_addresses_primary_user ON email_addresses (user_id) WHERE is_primary;

CREATE TABLE files (
    id UUID NOT NULL,
    owner_id INTEGER NOT NULL,
    digest VARCHAR(64) NOT NULL,
    storage_key VARCHAR NOT NULL,
    size BIGINT NOT NULL,
    original_name VARCHAR NOT NULL,
    ready BOOLEAN NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    lease_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_files PRIMARY KEY (id),
    CONSTRAINT ck_files_size CHECK (size >= 0),
    CONSTRAINT fk_files_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id),
    CONSTRAINT uq_files_storage_key UNIQUE (storage_key)
);

CREATE INDEX ix_files_expires_at ON files (expires_at);

CREATE INDEX ix_files_owner_id ON files (owner_id);

CREATE TABLE reference_authors (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY,
    reference_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    CONSTRAINT pk_reference_authors PRIMARY KEY (reference_id, position),
    CONSTRAINT ck_reference_authors_position CHECK (position >= 0),
    CONSTRAINT uq_reference_authors_id UNIQUE (id),
    CONSTRAINT fk_reference_authors_reference_id_references FOREIGN KEY(reference_id) REFERENCES "references" (id) ON DELETE CASCADE
);

CREATE TABLE reference_drafts (
    owner_id INTEGER NOT NULL,
    sid VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_reference_drafts PRIMARY KEY (owner_id, sid),
    CONSTRAINT fk_reference_drafts_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_reference_drafts_expires_at ON reference_drafts (expires_at);

CREATE TABLE role_requests (
    user_id INTEGER NOT NULL,
    reason VARCHAR(2000) NOT NULL,
    status VARCHAR(16) NOT NULL,
    decided_by INTEGER,
    decided_at TIMESTAMP WITH TIME ZONE,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_role_requests PRIMARY KEY (id),
    CONSTRAINT fk_role_requests_user_id_users FOREIGN KEY(user_id) REFERENCES users (id),
    CONSTRAINT fk_role_requests_decided_by_users FOREIGN KEY(decided_by) REFERENCES users (id)
);

CREATE INDEX ix_role_requests_user_id ON role_requests (user_id);

CREATE UNIQUE INDEX uq_role_requests_pending ON role_requests (user_id) WHERE status = 'pending';

CREATE TABLE saved_queries (
    id UUID NOT NULL,
    owner_id INTEGER,
    criteria JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_saved_queries PRIMARY KEY (id),
    CONSTRAINT fk_saved_queries_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_saved_queries_expires_at ON saved_queries (expires_at);

CREATE INDEX ix_saved_queries_owner_id ON saved_queries (owner_id);

CREATE TABLE security_configuration (
    id INTEGER NOT NULL,
    designated_administrator_id INTEGER,
    legacy_token_cutoff TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_security_configuration PRIMARY KEY (id),
    CONSTRAINT ck_security_configuration_singleton CHECK (id = 1),
    CONSTRAINT fk_security_configuration_designated_administrator_id_users FOREIGN KEY(designated_administrator_id) REFERENCES users (id)
);

CREATE TABLE studies (
    sid VARCHAR(255) NOT NULL,
    name VARCHAR NOT NULL,
    date DATE,
    access VARCHAR(16) NOT NULL,
    licence VARCHAR(16) NOT NULL,
    creator_id INTEGER,
    reference_id INTEGER,
    source_digest VARCHAR(64),
    vocabulary_version VARCHAR,
    processing_version VARCHAR,
    validation_report JSONB NOT NULL,
    source_manifest JSONB NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_studies PRIMARY KEY (id),
    CONSTRAINT ck_studies_access CHECK (access IN ('public', 'private')),
    CONSTRAINT ck_studies_licence CHECK (licence IN ('open', 'closed')),
    CONSTRAINT ck_studies_sid CHECK (length(sid) > 0),
    CONSTRAINT uq_studies_sid UNIQUE (sid),
    CONSTRAINT fk_studies_creator_id_users FOREIGN KEY(creator_id) REFERENCES users (id),
    CONSTRAINT uq_studies_reference_id UNIQUE (reference_id),
    CONSTRAINT fk_studies_reference_id_references FOREIGN KEY(reference_id) REFERENCES "references" (id)
);

CREATE INDEX ix_studies_creator_id ON studies (creator_id);

CREATE INDEX ix_studies_name ON studies (name);

CREATE INDEX ix_studies_search ON studies USING gin (to_tsvector('simple', (coalesce(sid, '') || ' ') || coalesce(name, '')));

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

CREATE INDEX ix_study_drafts_expires_at ON study_drafts (expires_at);

CREATE TABLE vocabulary_edges (
    child VARCHAR(255) NOT NULL,
    parent VARCHAR(255) NOT NULL,
    CONSTRAINT pk_vocabulary_edges PRIMARY KEY (child, parent),
    CONSTRAINT ck_vocabulary_edges_not_self CHECK (child <> parent),
    CONSTRAINT fk_vocabulary_edges_child_vocabulary_nodes FOREIGN KEY(child) REFERENCES vocabulary_nodes (sid) ON DELETE CASCADE,
    CONSTRAINT fk_vocabulary_edges_parent_vocabulary_nodes FOREIGN KEY(parent) REFERENCES vocabulary_nodes (sid)
);

CREATE TABLE vocabulary_terms (
    node_sid VARCHAR(255) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    value VARCHAR NOT NULL,
    CONSTRAINT pk_vocabulary_terms PRIMARY KEY (node_sid, kind, value),
    CONSTRAINT fk_vocabulary_terms_node_sid_vocabulary_nodes FOREIGN KEY(node_sid) REFERENCES vocabulary_nodes (sid) ON DELETE CASCADE
);

CREATE INDEX ix_vocabulary_terms_search ON vocabulary_terms USING gin (to_tsvector('simple', coalesce(value, '')));

CREATE TABLE datasets (
    kind VARCHAR NOT NULL,
    parent_id INTEGER,
    name VARCHAR,
    data_type VARCHAR,
    image VARCHAR,
    position INTEGER,
    measurement_ids BIGINT[] DEFAULT '{}' NOT NULL,
    point_ids BIGINT[] DEFAULT '{}' NOT NULL,
    shared_fields JSONB DEFAULT '[]' NOT NULL,
    row_metadata JSONB DEFAULT '[]' NOT NULL,
    dimension_labels JSONB DEFAULT '[]' NOT NULL,
    study_id INTEGER NOT NULL,
    key VARCHAR(512) NOT NULL,
    source JSONB,
    id SERIAL NOT NULL,
    CONSTRAINT pk_datasets PRIMARY KEY (id),
    CONSTRAINT uq_datasets_study_id_id UNIQUE (study_id, id),
    CONSTRAINT uq_datasets_study_id_kind_key UNIQUE (study_id, kind, key),
    CONSTRAINT uq_datasets_parent_id_position UNIQUE (parent_id, position),
    CONSTRAINT fk_datasets_study_id_parent_id_datasets FOREIGN KEY(study_id, parent_id) REFERENCES datasets (study_id, id) ON DELETE CASCADE,
    CONSTRAINT ck_datasets_kind CHECK (kind IN ('course', 'dataset', 'series')),
    CONSTRAINT ck_datasets_position CHECK (position IS NULL OR position >= 0),
    CONSTRAINT ck_datasets_parent_kind CHECK ((kind = 'series') = (parent_id IS NOT NULL)),
    CONSTRAINT fk_datasets_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE
);

CREATE INDEX ix_datasets_measurement_ids ON datasets USING gin (measurement_ids);

CREATE INDEX ix_datasets_parent_id ON datasets (parent_id);

CREATE INDEX ix_datasets_study_id ON datasets (study_id);

CREATE TABLE interventions (
    image VARCHAR,
    name VARCHAR NOT NULL,
    time FLOAT,
    time_text VARCHAR,
    time_end FLOAT,
    time_unit VARCHAR,
    route VARCHAR(255),
    application VARCHAR(255),
    form VARCHAR(255),
    derived_from_id INTEGER,
    study_id INTEGER NOT NULL,
    key VARCHAR(512) NOT NULL,
    source JSONB,
    id SERIAL NOT NULL,
    measurement_type VARCHAR(255) NOT NULL,
    substance VARCHAR(255),
    calculation_type VARCHAR(255),
    choice VARCHAR,
    unit VARCHAR,
    value FLOAT,
    mean FLOAT,
    median FLOAT,
    minimum FLOAT,
    maximum FLOAT,
    sd FLOAT,
    se FLOAT,
    cv FLOAT,
    count INTEGER,
    calculated BOOLEAN DEFAULT 'false' NOT NULL,
    origin VARCHAR(16) NOT NULL,
    CONSTRAINT pk_interventions PRIMARY KEY (id),
    CONSTRAINT uq_interventions_study_id_id UNIQUE (study_id, id),
    CONSTRAINT uq_interventions_study_id_key UNIQUE (study_id, key),
    CONSTRAINT uq_interventions_study_id_name_origin UNIQUE (study_id, name, origin),
    CONSTRAINT fk_interventions_study_id_derived_from_id_interventions FOREIGN KEY(study_id, derived_from_id) REFERENCES interventions (study_id, id) ON DELETE CASCADE,
    CONSTRAINT ck_interventions_origin CHECK (origin IN ('reported', 'normalized', 'calculated')),
    CONSTRAINT ck_interventions_count CHECK (count IS NULL OR count >= 0),
    CONSTRAINT fk_interventions_route_vocabulary_nodes FOREIGN KEY(route) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_interventions_application_vocabulary_nodes FOREIGN KEY(application) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_interventions_form_vocabulary_nodes FOREIGN KEY(form) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_interventions_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE,
    CONSTRAINT fk_interventions_measurement_type_vocabulary_nodes FOREIGN KEY(measurement_type) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_interventions_substance_vocabulary_nodes FOREIGN KEY(substance) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_interventions_calculation_type_vocabulary_nodes FOREIGN KEY(calculation_type) REFERENCES vocabulary_nodes (sid)
);

CREATE INDEX ix_interventions_measurement_type ON interventions (measurement_type);

CREATE INDEX ix_interventions_study_id ON interventions (study_id);

CREATE INDEX ix_interventions_substance ON interventions (substance);

CREATE TABLE legacy_file_handles (
    file_id UUID NOT NULL,
    id SERIAL NOT NULL,
    CONSTRAINT pk_legacy_file_handles PRIMARY KEY (id),
    CONSTRAINT uq_legacy_file_handles_file_id UNIQUE (file_id),
    CONSTRAINT fk_legacy_file_handles_file_id_files FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE CASCADE
);

CREATE TABLE measurement_sources (
    study_id INTEGER NOT NULL,
    key VARCHAR(512) NOT NULL,
    source JSONB,
    id SERIAL NOT NULL,
    CONSTRAINT pk_measurement_sources PRIMARY KEY (id),
    CONSTRAINT uq_measurement_sources_study_id_id UNIQUE (study_id, id),
    CONSTRAINT uq_measurement_sources_study_id_key UNIQUE (study_id, key),
    CONSTRAINT fk_measurement_sources_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE
);

CREATE INDEX ix_measurement_sources_study_id ON measurement_sources (study_id);

CREATE TABLE notes (
    study_id INTEGER NOT NULL,
    record_key VARCHAR NOT NULL,
    kind VARCHAR(16) NOT NULL,
    position INTEGER NOT NULL,
    text VARCHAR NOT NULL,
    user_id INTEGER,
    id SERIAL NOT NULL,
    CONSTRAINT pk_notes PRIMARY KEY (id),
    CONSTRAINT fk_notes_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE,
    CONSTRAINT fk_notes_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_notes_study_id ON notes (study_id);

CREATE TABLE study_attachments (
    study_id INTEGER NOT NULL,
    file_id UUID NOT NULL,
    name VARCHAR NOT NULL,
    CONSTRAINT pk_study_attachments PRIMARY KEY (study_id, file_id),
    CONSTRAINT uq_study_attachments_study_id_name UNIQUE (study_id, name),
    CONSTRAINT fk_study_attachments_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE,
    CONSTRAINT fk_study_attachments_file_id_files FOREIGN KEY(file_id) REFERENCES files (id)
);

CREATE TABLE study_grants (
    study_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(16) NOT NULL,
    CONSTRAINT pk_study_grants PRIMARY KEY (study_id, user_id, role),
    CONSTRAINT ck_study_grants_role CHECK (role IN ('curator', 'collaborator')),
    CONSTRAINT fk_study_grants_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE,
    CONSTRAINT fk_study_grants_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE study_users (
    study_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(16) NOT NULL,
    rating FLOAT,
    CONSTRAINT pk_study_users PRIMARY KEY (study_id, user_id, role),
    CONSTRAINT ck_study_users_role CHECK (role IN ('curator', 'collaborator')),
    CONSTRAINT ck_study_users_rating CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    CONSTRAINT fk_study_users_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE,
    CONSTRAINT fk_study_users_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE subjects (
    kind VARCHAR NOT NULL,
    image VARCHAR,
    name VARCHAR NOT NULL,
    count INTEGER NOT NULL,
    parent_id INTEGER,
    study_id INTEGER NOT NULL,
    key VARCHAR(512) NOT NULL,
    source JSONB,
    id SERIAL NOT NULL,
    CONSTRAINT pk_subjects PRIMARY KEY (id),
    CONSTRAINT uq_subjects_study_id_id UNIQUE (study_id, id),
    CONSTRAINT uq_subjects_study_id_kind_key UNIQUE (study_id, kind, key),
    CONSTRAINT uq_subjects_study_id_kind_name UNIQUE (study_id, kind, name),
    CONSTRAINT fk_subjects_study_id_parent_id_subjects FOREIGN KEY(study_id, parent_id) REFERENCES subjects (study_id, id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT ck_subjects_kind CHECK (kind IN ('group', 'individual')),
    CONSTRAINT ck_subjects_count CHECK (count >= 0),
    CONSTRAINT ck_subjects_individual_count CHECK (kind <> 'individual' OR count = 1),
    CONSTRAINT ck_subjects_not_self CHECK (parent_id IS NULL OR parent_id <> id),
    CONSTRAINT fk_subjects_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE
);

CREATE INDEX ix_subjects_parent_id ON subjects (parent_id);

CREATE INDEX ix_subjects_study_id ON subjects (study_id);

CREATE TABLE tokens (
    user_id INTEGER NOT NULL,
    digest VARCHAR(64) NOT NULL,
    email_id INTEGER,
    purpose VARCHAR(32) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_tokens PRIMARY KEY (id),
    CONSTRAINT fk_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_tokens_digest UNIQUE (digest),
    CONSTRAINT fk_tokens_email_id_email_addresses FOREIGN KEY(email_id) REFERENCES email_addresses (id) ON DELETE CASCADE
);

CREATE INDEX ix_tokens_user_id ON tokens (user_id);

CREATE TABLE observations (
    kind VARCHAR NOT NULL,
    subject_id INTEGER NOT NULL,
    source_id INTEGER,
    measurement_type VARCHAR(255) NOT NULL,
    substance VARCHAR(255),
    calculation_type VARCHAR(255),
    choice VARCHAR,
    calculated BOOLEAN DEFAULT 'false' NOT NULL,
    series_key VARCHAR,
    label VARCHAR,
    output_type VARCHAR DEFAULT 'output' NOT NULL,
    time FLOAT,
    time_unit VARCHAR,
    time_not_reported BOOLEAN DEFAULT 'false' NOT NULL,
    time_unit_not_reported BOOLEAN DEFAULT 'false' NOT NULL,
    tissue VARCHAR(255),
    method VARCHAR(255),
    image VARCHAR,
    study_id INTEGER NOT NULL,
    key VARCHAR(512) NOT NULL,
    source JSONB,
    id SERIAL NOT NULL,
    CONSTRAINT pk_observations PRIMARY KEY (id),
    CONSTRAINT uq_observations_study_id_id UNIQUE (study_id, id),
    CONSTRAINT uq_observations_study_id_kind_key UNIQUE (study_id, kind, key),
    CONSTRAINT fk_observations_study_id_subject_id_subjects FOREIGN KEY(study_id, subject_id) REFERENCES subjects (study_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_observations_study_id_source_id_measurement_sources FOREIGN KEY(study_id, source_id) REFERENCES measurement_sources (study_id, id),
    CONSTRAINT ck_observations_kind CHECK (kind IN ('characteristic', 'output')),
    CONSTRAINT ck_observations_output_type CHECK (output_type IN ('output', 'timecourse', 'array')),
    CONSTRAINT fk_observations_measurement_type_vocabulary_nodes FOREIGN KEY(measurement_type) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_observations_substance_vocabulary_nodes FOREIGN KEY(substance) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_observations_calculation_type_vocabulary_nodes FOREIGN KEY(calculation_type) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_observations_tissue_vocabulary_nodes FOREIGN KEY(tissue) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_observations_method_vocabulary_nodes FOREIGN KEY(method) REFERENCES vocabulary_nodes (sid),
    CONSTRAINT fk_observations_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE
);

CREATE INDEX ix_observations_measurement_type ON observations (measurement_type);

CREATE INDEX ix_observations_study_id ON observations (study_id);

CREATE INDEX ix_observations_subject_id ON observations (subject_id);

CREATE INDEX ix_observations_substance ON observations (substance);

CREATE TABLE observation_interventions (
    study_id INTEGER NOT NULL,
    observation_id INTEGER NOT NULL,
    intervention_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    CONSTRAINT pk_observation_interventions PRIMARY KEY (study_id, observation_id, intervention_id),
    CONSTRAINT fk_observation_interventions_study_id_observation_id_ob_44f9 FOREIGN KEY(study_id, observation_id) REFERENCES observations (study_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_observation_interventions_study_id_intervention_id_i_bf8f FOREIGN KEY(study_id, intervention_id) REFERENCES interventions (study_id, id) ON DELETE CASCADE,
    CONSTRAINT uq_observation_interventions_observation_id_position UNIQUE (observation_id, position)
);

CREATE TABLE observation_values (
    observation_id INTEGER NOT NULL,
    representation VARCHAR NOT NULL,
    unit VARCHAR,
    value FLOAT,
    mean FLOAT,
    median FLOAT,
    minimum FLOAT,
    maximum FLOAT,
    sd FLOAT,
    se FLOAT,
    cv FLOAT,
    count INTEGER,
    derived_from_id INTEGER,
    derived_from_course_id INTEGER,
    study_id INTEGER NOT NULL,
    key VARCHAR(512) NOT NULL,
    source JSONB,
    id SERIAL NOT NULL,
    CONSTRAINT pk_observation_values PRIMARY KEY (id),
    CONSTRAINT uq_observation_values_study_id_id UNIQUE (study_id, id),
    CONSTRAINT uq_observation_values_observation_id_representation UNIQUE (observation_id, representation),
    CONSTRAINT fk_observation_values_study_id_observation_id_observations FOREIGN KEY(study_id, observation_id) REFERENCES observations (study_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_observation_values_study_id_derived_from_id_observat_e7de FOREIGN KEY(study_id, derived_from_id) REFERENCES observation_values (study_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_observation_values_study_id_derived_from_course_id_datasets FOREIGN KEY(study_id, derived_from_course_id) REFERENCES datasets (study_id, id) ON DELETE CASCADE,
    CONSTRAINT ck_observation_values_representation CHECK (representation IN ('reported', 'normalized', 'calculated')),
    CONSTRAINT ck_observation_values_count CHECK (count IS NULL OR count >= 0),
    CONSTRAINT fk_observation_values_study_id_studies FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE CASCADE
);

CREATE INDEX ix_observation_values_observation_id ON observation_values (observation_id);

CREATE INDEX ix_observation_values_study_id ON observation_values (study_id);

INSERT INTO security_configuration (id, legacy_token_cutoff) VALUES (1, CURRENT_TIMESTAMP + INTERVAL '30 days');
"""

ARRAY_INTEGRITY = r"""
CREATE FUNCTION immutable_scientific_kind() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.kind IS DISTINCT FROM NEW.kind THEN
        RAISE EXCEPTION 'Scientific identity kind is immutable; replace the record instead' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER subject_kind_immutable BEFORE UPDATE ON subjects
FOR EACH ROW EXECUTE FUNCTION immutable_scientific_kind();
CREATE TRIGGER observation_kind_immutable BEFORE UPDATE ON observations
FOR EACH ROW EXECUTE FUNCTION immutable_scientific_kind();
CREATE TRIGGER dataset_kind_immutable BEFORE UPDATE ON datasets
FOR EACH ROW EXECUTE FUNCTION immutable_scientific_kind();
CREATE FUNCTION immutable_observation_context() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.observation_id IS DISTINCT FROM NEW.observation_id THEN
        RAISE EXCEPTION 'A numerical representation cannot change observation identity' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER observation_context_immutable BEFORE UPDATE ON observation_values
FOR EACH ROW EXECUTE FUNCTION immutable_observation_context();
CREATE FUNCTION check_dataset_membership() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE dataset_record record;
        width integer;
BEGIN
    IF TG_TABLE_NAME = 'observation_values' AND TG_OP = 'UPDATE'
       AND OLD.id = NEW.id AND OLD.study_id = NEW.study_id THEN RETURN NULL; END IF;
    -- Unlike PostgreSQL's internal FK implementation, a SQL trigger cannot
    -- cross-check a transaction's historical REPEATABLE READ snapshot. Keep
    -- scientific membership writes on the application's READ COMMITTED level.
    -- Read-only repeatable-read snapshots remain supported.
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'Dataset membership writes and observation deletions require READ COMMITTED isolation'
            USING ERRCODE = '25000';
    END IF;
    FOR dataset_record IN
        SELECT d.* FROM datasets d
        WHERE (TG_TABLE_NAME = 'datasets' AND (d.id = NEW.id OR d.parent_id = NEW.id))
           OR (TG_TABLE_NAME = 'observation_values' AND d.measurement_ids @> ARRAY[OLD.id::bigint])
    LOOP
        IF COALESCE(array_ndims(dataset_record.measurement_ids), 1) <> 1
           OR COALESCE(array_ndims(dataset_record.point_ids), 1) <> 1
           OR (cardinality(dataset_record.measurement_ids) > 0 AND array_lower(dataset_record.measurement_ids, 1) <> 1)
           OR (cardinality(dataset_record.point_ids) > 0 AND array_lower(dataset_record.point_ids, 1) <> 1) THEN
            RAISE EXCEPTION 'Dataset membership must use one-dimensional arrays starting at one' USING ERRCODE = '23514';
        END IF;
        IF array_position(dataset_record.point_ids, NULL) IS NOT NULL THEN
            RAISE EXCEPTION 'Dataset row IDs must not be null' USING ERRCODE = '23514';
        END IF;
        IF dataset_record.kind = 'series' THEN
            width := jsonb_array_length(dataset_record.dimension_labels);
            IF (cardinality(dataset_record.measurement_ids) > 0 AND width = 0)
               OR (width > 0 AND cardinality(dataset_record.measurement_ids) % width <> 0)
               OR cardinality(dataset_record.point_ids) * width <> cardinality(dataset_record.measurement_ids)
               OR (width = 0 AND cardinality(dataset_record.point_ids) > 0)
               OR (jsonb_array_length(dataset_record.row_metadata) > 0 AND jsonb_array_length(dataset_record.row_metadata) <> cardinality(dataset_record.point_ids)) THEN
                RAISE EXCEPTION 'Dataset arrays must contain a complete rectangular series and matching row IDs' USING ERRCODE = '23514';
            END IF;
        END IF;
        IF dataset_record.kind = 'series' AND NOT EXISTS (
            SELECT 1 FROM datasets parent WHERE parent.id = dataset_record.parent_id AND parent.kind = 'dataset'
        ) THEN
            RAISE EXCEPTION 'A series requires a dataset parent' USING ERRCODE = '23514';
        END IF;
        -- Match native FK locks: concurrent deletion cannot pass its final
        -- membership check while another transaction publishes these members.
        PERFORM v.id FROM observation_values v
        WHERE v.id = ANY(dataset_record.measurement_ids)
        ORDER BY v.id FOR KEY SHARE;
        IF EXISTS (
            SELECT 1 FROM unnest(dataset_record.measurement_ids) AS member(id)
            LEFT JOIN observation_values v ON v.id = member.id AND v.study_id = dataset_record.study_id
            WHERE v.id IS NULL OR NOT EXISTS (SELECT 1 FROM observations o WHERE o.id = v.observation_id AND o.kind = 'output')
        ) THEN
            RAISE EXCEPTION 'Dataset contains missing or cross-study observations' USING ERRCODE = '23503';
        END IF;
        IF dataset_record.kind = 'course' AND cardinality(dataset_record.measurement_ids) <>
           (SELECT count(DISTINCT member) FROM unnest(dataset_record.measurement_ids) AS member) THEN
            RAISE EXCEPTION 'Duplicate course observation' USING ERRCODE = '23505';
        END IF;
    END LOOP;
    RETURN NULL;
END $$;
CREATE FUNCTION check_observation_course_kind() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    -- Most representations have no course derivation. Avoid a joined lookup
    -- for every scalar insert/update; membership kinds are immutable.
    IF NEW.derived_from_course_id IS NULL THEN RETURN NULL; END IF;
    IF EXISTS (SELECT 1 FROM observation_values v JOIN datasets d ON d.id = v.derived_from_course_id
               WHERE v.id = NEW.id AND d.kind <> 'course') THEN
        RAISE EXCEPTION 'Calculated observations require a course reference' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER observation_course_kind_valid
AFTER INSERT OR UPDATE ON observation_values DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION check_observation_course_kind();
CREATE FUNCTION check_subject_parent_kind() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM subjects child JOIN subjects parent ON parent.id = child.parent_id
               WHERE (child.id = NEW.id OR parent.id = NEW.id) AND parent.kind <> 'group') THEN
        RAISE EXCEPTION 'A subject parent must be a group' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER subject_parent_kind_valid
AFTER INSERT OR UPDATE ON subjects DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION check_subject_parent_kind();
CREATE CONSTRAINT TRIGGER dataset_membership_valid
AFTER INSERT OR UPDATE ON datasets DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION check_dataset_membership();
CREATE CONSTRAINT TRIGGER dataset_member_delete_valid
AFTER DELETE OR UPDATE ON observation_values DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION check_dataset_membership();

"""


def upgrade():
    op.execute(SCHEMA)
    op.execute(ARRAY_INTEGRITY)


def downgrade():
    op.execute(r"""
DROP TABLE "observation_values";
DROP TABLE "observation_interventions";
DROP TABLE "observations";
DROP TABLE "tokens";
DROP TABLE "subjects";
DROP TABLE "study_users";
DROP TABLE "study_grants";
DROP TABLE "study_attachments";
DROP TABLE "notes";
DROP TABLE "measurement_sources";
DROP TABLE "legacy_file_handles";
DROP TABLE "interventions";
DROP TABLE "datasets";
DROP TABLE "vocabulary_terms";
DROP TABLE "vocabulary_edges";
DROP TABLE "study_drafts";
DROP TABLE "studies";
DROP TABLE "security_configuration";
DROP TABLE "saved_queries";
DROP TABLE "role_requests";
DROP TABLE "reference_drafts";
DROP TABLE "reference_authors";
DROP TABLE "files";
DROP TABLE "email_addresses";
DROP TABLE "browser_sessions";
DROP TABLE "avatar_assets";
DROP TABLE "audit_events";
DROP TABLE "api_keys";
DROP TABLE "work_leases";
DROP TABLE "vocabulary_version";
DROP TABLE "vocabulary_nodes";
DROP TABLE "users";
DROP TABLE "user_import_runs";
DROP TABLE "references";
DROP TABLE "account_throttles";
DROP FUNCTION immutable_scientific_kind();
DROP FUNCTION immutable_observation_context();
DROP FUNCTION check_dataset_membership();
DROP FUNCTION check_observation_course_kind();
DROP FUNCTION check_subject_parent_kind();
DROP SEQUENCE dataset_row_id_seq;
""")
