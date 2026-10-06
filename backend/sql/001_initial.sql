-- Initial private application schema. Applied transactionally by backend.migrations.

CREATE TABLE smartsauda.catalog (
	id SERIAL NOT NULL, 
	vehicle_type VARCHAR(10) NOT NULL, 
	brand VARCHAR(160) NOT NULL, 
	model VARCHAR(160) NOT NULL, 
	model_version VARCHAR(40) NOT NULL, 
	training_rows INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT catalog_identity UNIQUE (vehicle_type, brand, model, model_version)
);

CREATE TABLE smartsauda.image_cache (
	key VARCHAR(64) NOT NULL, 
	value JSONB NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
);

CREATE INDEX ix_smartsauda_image_cache_expires_at ON smartsauda.image_cache (expires_at);

CREATE TABLE smartsauda.rate_buckets (
	key VARCHAR(64) NOT NULL, 
	count INTEGER NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
);

CREATE INDEX ix_smartsauda_rate_buckets_expires_at ON smartsauda.rate_buckets (expires_at);

CREATE TABLE smartsauda.users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	display_name VARCHAR(80) NOT NULL, 
	password_hash VARCHAR(512) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT user_role CHECK (role IN ('User', 'Admin')), 
	UNIQUE (email)
);

CREATE TABLE smartsauda.predictions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	vehicle_type VARCHAR(10) NOT NULL, 
	brand VARCHAR(160) NOT NULL, 
	model VARCHAR(160) NOT NULL, 
	model_version VARCHAR(40) NOT NULL, 
	price NUMERIC(24, 2) NOT NULL, 
	specifications JSONB NOT NULL, 
	result JSONB NOT NULL, 
	image JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT positive_price CHECK (price > 0), 
	FOREIGN KEY(user_id) REFERENCES smartsauda.users (id)
);

CREATE INDEX ix_prediction_owner_time ON smartsauda.predictions (user_id, created_at);

CREATE TABLE smartsauda.sessions (
	token_digest VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (token_digest), 
	FOREIGN KEY(user_id) REFERENCES smartsauda.users (id) ON DELETE CASCADE
);

CREATE INDEX ix_smartsauda_sessions_expires_at ON smartsauda.sessions (expires_at);

CREATE INDEX ix_smartsauda_sessions_user_id ON smartsauda.sessions (user_id);

REVOKE ALL ON ALL TABLES IN SCHEMA smartsauda FROM PUBLIC;

REVOKE ALL ON ALL SEQUENCES IN SCHEMA smartsauda FROM PUBLIC;

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON SCHEMA smartsauda FROM anon;
        REVOKE ALL ON ALL TABLES IN SCHEMA smartsauda FROM anon;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA smartsauda FROM anon;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON SCHEMA smartsauda FROM authenticated;
        REVOKE ALL ON ALL TABLES IN SCHEMA smartsauda FROM authenticated;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA smartsauda FROM authenticated;
    END IF;
END $$;
