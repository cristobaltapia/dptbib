#!/usr/bin/env python
# -*- coding: utf-8 -*-
import configparser
import os.path
import re
import unicodedata
from os.path import expanduser
from pathlib import Path

import bibtexparser
import dateparser
from bibtexparser.bparser import BibTexParser
from dptrp1.dptrp1 import DigitalPaper

HOME = Path.home()
CONF_DIR = HOME / ".config/dptbib"
CONFIG_FILE = HOME / ".config/dptbib/dptbib.conf"

# Define folder structure for each type of document
OUT_DEF = {
    "article": {
        "out_folder": "Articles",
        "out_name": [["year", "title", "subtitle"], ["year", "title"]],
    },
    "report": {"out_folder": "Reports", "out_name": [["year", "title"]]},
    "techreport": {"out_folder": "Reports", "out_name": [["year", "title"]]},
    "inproceedings": {"out_folder": "Proceedings", "out_name": [["year", "title"]]},
    "book": {"out_folder": "Books", "out_name": [["year", "title"]]},
    "inbook": {
        "out_folder": "Articles",
        "out_name": [["year", "title", "subtitle"], ["year", "title"]],
    },
    "conference": {"out_folder": "Proceedings", "out_name": [["year", "title"]]},
    "standard": {"out_folder": "Standards", "out_name": [["year", "key", "title"]]},
    "phdthesis": {"out_folder": "Thesis", "out_name": [["year", "author", "title"]]},
    "mastersthesis": {
        "out_folder": "Thesis",
        "out_name": [["year", "author", "title"]],
    },
}


def get_config_file(config=CONFIG_FILE):
    """Get configuration information"""
    check_config_file()

    conf = configparser.ConfigParser()
    conf.read(config)

    return conf


def check_config_file():
    """Check the exitence of config file"""
    if not os.path.isfile(CONFIG_FILE):
        init_config_file()

    return 1


def init_config_file():
    """Initialize a configuration file"""
    ensure_dir(CONF_DIR)
    config = configparser.ConfigParser()
    config["Device"] = {
        "address": "",
        "id": HOME / ".dpapp/deviceid.dat",
        "key": HOME / ".dpapp/privatekey.dat",
    }
    config["Bibfiles"] = {"default": ""}

    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def connect_to_dpt(addr, dev_id, dev_key):
    """
    Loads the key and client ID to authenticate with the DPT-RP1
    """
    with open(dev_id) as f:
        client_id = f.readline().strip()

    with open(dev_key) as f:
        key = f.read()

    dpt = DigitalPaper(addr)
    dpt.authenticate(client_id, key)

    return dpt


def open_bib_db(bib_file):
    """Open the bibtex database"""
    parser = BibTexParser()
    parser.ignore_nonstandard_types = False

    with open(bib_file) as bib_:
        bib_db = bibtexparser.load(bib_, parser)

    return bib_db


def get_doc_from_bibkey(bib_db, key):
    """Get the location of the pdf file, given the bibkey

    Parameters
    ----------
    bib_db : `obj`:BibTexParser
        BibTexParser object
    key : str
        Bibkey

    Returns
    -------
    str :
        File path

    """
    entry = bib_db.entries_dict[key]
    file_entry = entry["file"]
    # Get only the path
    match = re.search("(?<=:).*(?=:)", file_entry)
    file_path = file_entry[match.start() : match.end()]

    return file_path


def get_type_from_bibkey(bib_db, key):
    """Get the reference type associated to the bibkey

    Parameters
    ----------
    bib_db : `obj`:BibTexParser
    key : str
        Bibkey

    Returns
    -------
    str :
        File path

    """
    entry = bib_db.entries_dict[key]
    e_type = entry["ENTRYTYPE"]

    return e_type


def gen_file_name(bib_db, key, out_style):
    """TODO: Docstring for gen_file_name.

    Parameters
    ----------
    key : TODO
    bib_db : TODO
    out_style : TODO

    Returns
    -------
    TODO

    """
    entry = bib_db.entries_dict[key]

    # Define out folder
    for struct in out_style:
        try:
            out_name = "".join(slugify(entry[ix]) + "_" for ix in struct)
            break
        except:
            pass

    return out_name + ".pdf"


def ensure_dir(f):
    """look up for the directory 'f' and creates it if it doesn't exist."""
    if not os.path.exists(f):
        os.makedirs(f)


def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def push_file_to_dpt(d, bibfile, bibkey, bib_name=None):
    """Push file given a bibkey"""
    bib_db = open_bib_db(bibfile)

    d_path = get_doc_from_bibkey(bib_db, bibkey)
    d_type = get_type_from_bibkey(bib_db, bibkey)

    f_bib = os.path.dirname(bibfile)
    d_path = f_bib + "/" + d_path

    # Define name of the target folder
    if bib_name in [None, "default"]:
        t_folder = "Document/" + OUT_DEF[d_type]["out_folder"]
    else:
        t_folder = (
            "Document/" + bib_name.capitalize()
        )

    # Define name of the target file
    t_file = OUT_DEF[d_type]["out_name"]

    name_file = gen_file_name(bib_db, bibkey, t_file)
    remote_path = t_folder + "/" + name_file

    print(t_folder)
    d.new_folder(t_folder)

    with open(d_path, "rb") as fh:
        d.upload(fh, remote_path)
