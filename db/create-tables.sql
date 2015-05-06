CREATE TABLE GRIDCELL (
    gridcell_pk serial NOT NULL,
    country_fk int NOT NULL,
    CONSTRAINT GRIDCELL_pk PRIMARY KEY(gridcell_pk)
);
SELECT AddGeometryColumn('gridcell', 'wkb_geometry', 3785, 'POLYGON', 2);

CREATE TABLE USERINFO (
    userinfo_pk bigserial  NOT NULL,
    name varchar(200)  NOT NULL,
    total_observations bigint,
    CONSTRAINT USERINFO_pk PRIMARY KEY (userinfo_pk)
);
ALTER TABLE userinfo ADD UNIQUE(name);

CREATE TABLE WEEKLY_REPORT (
    weekly_report_pk bigserial NOT NULL,
    week_of_year smallint  NOT NULL,
    year int  NOT NULL,
    observations int,
    discovery_cells int,
    discovery_observation int,
    userinfo_fk bigint  NOT NULL,
    gridcell_fk bigint  NOT NULL,
    CONSTRAINT WEEKLY_REPORT_pk PRIMARY KEY (weekly_report_pk)
);
CREATE UNIQUE INDEX WEEKLY_REPORT_UNIQUE ON WEEKLY_REPORT(week_of_year, year, userinfo_fk, gridcell_fk);
ALTER TABLE WEEKLY_REPORT ADD CONSTRAINT WEEKLY_REPORT_GRIDCELL
    FOREIGN KEY (gridcell_fk)
    REFERENCES GRIDCELL (gridcell_pk)
    NOT DEFERRABLE
    INITIALLY IMMEDIATE
;
ALTER TABLE WEEKLY_REPORT ADD CONSTRAINT WEEKLY_REPORT_USERINFO
    FOREIGN KEY (userinfo_fk)
    REFERENCES USERINFO (userinfo_pk)
    NOT DEFERRABLE
    INITIALLY IMMEDIATE
;
