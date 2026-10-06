ALTER TABLE smartsauda.catalog
    ADD COLUMN min_year SMALLINT,
    ADD COLUMN max_year SMALLINT,
    ADD COLUMN constraints JSONB,
    ADD CONSTRAINT catalog_supported_years CHECK (
        (min_year IS NULL AND max_year IS NULL) OR
        (min_year IS NOT NULL AND max_year IS NOT NULL AND min_year >= 1900 AND max_year <= 2100 AND min_year <= max_year)
    );
