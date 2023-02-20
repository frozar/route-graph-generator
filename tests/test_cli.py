import argparse
import json
import os
from pathlib import Path

# 3rd party
import pytest
from unittest.mock import Mock, patch

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from r2gg import cli

import psycopg2 as psycopg

cur_dir = Path(os.path.normpath(os.path.dirname(__file__)))

# ############################################################################
# ########## Classes #############
# ################################
HOST = os.environ.get("POSTGRES_HOST", "172.17.0.1")
PORT = os.environ.get("PORT", 5555)
DBNAME = os.environ.get("POSTGRES_DB", "ign")
USER = os.environ.get("POSTGRES_USER", "ign")
PASS = os.environ.get("POSTGRES_PASSWORD", "ign")


@pytest.fixture
def init_database() -> None:
    """Init database for test."""

    con = psycopg.connect(host=HOST, dbname=DBNAME, user=USER, password=PASS, port=PORT)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    con.cursor().execute("CREATE DATABASE pivot")
    con.commit()
    con.close()

    # Insert test data
    con = psycopg.connect(host=HOST, dbname=DBNAME, user=USER, password=PASS, port=PORT)
    cur = con.cursor()
    with open(str(cur_dir / "dumps" / "troncon_route_marseille10.sql"), mode="r") as sql_script:
        cur.execute(sql_script.read())
    with open(str(cur_dir / "dumps" / "non_communication_marseille10.sql"), mode="r") as sql_script:
        cur.execute(sql_script.read())

    con.commit()
    con.close()

    # Add extensions to pivot
    con = psycopg.connect(host=HOST, dbname="pivot", user=USER, password=PASS, port=PORT)
    con.cursor().execute("CREATE EXTENSION IF NOT EXISTS postgres_fdw")
    con.cursor().execute("CREATE EXTENSION IF NOT EXISTS Postgis")
    con.commit()
    con.close()
    yield

    con = psycopg.connect(host=HOST, dbname=DBNAME, user=USER, password=PASS, port=PORT)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    con.cursor().execute("DROP DATABASE pivot")
    con.cursor().execute("DROP TABLE public.non_communication")
    con.cursor().execute("DROP TABLE public.troncon_de_route")
    con.commit()
    con.close()


def update_src_dir_json(file_path: Path, output_file_path: Path):
    """Update .json file to replace {src_dir} by current source directory

    Parameters
    ----------
    file_path (Path) database .json file path
    """
    with open(file_path, mode="r") as f:
        content = f.read().replace("{src_dir}", str(Path(cur_dir / "..").resolve()))

    with open(output_file_path, mode="w") as f:
        f.write(content)


def test_sql2pivot(init_database):
    """Test simple run of cli for pivot base creation."""

    # Update input json file to indicate current source directory
    update_src_dir_json(cur_dir / "config" / "sql2pivot.json", cur_dir / "config" / "updated_sql2pivot.json")

    # mock ArgumentParser for configuration file
    with patch("argparse.ArgumentParser.parse_args") as parse_arg_mock:
        parse_arg_mock.return_value = argparse.Namespace(
            config_file_path=str(cur_dir / "config" / "updated_sql2pivot.json"))
        # Run conversion
        cli.sql2pivot()
