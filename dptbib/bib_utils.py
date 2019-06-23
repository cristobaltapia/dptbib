#!/usr/bin/env python
# -*- coding: utf-8 -*-
import configparser
import os.path
import re
import unicodedata
from os.path import expanduser
from pathlib import Path, PurePath

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


class DPTBibSync(object):

    """
    Class to syncronize the documents listed in a *bib-file with the DPT-RP1

    Parameters
    ----------
    dpt : `obj`:DigitalPaper
    bibname: str
        ID of the used bibliography file
    config : `obj`:
        Configuration file

    """

    def __init__(self, dpt, bibname, config):
        self._dpt = dpt
        self._bibname = bibname
        self._bibfile = config["Bibfiles"][bibname]
        self._config = config
        self._bib_path = None
        self._bib_db = self._open_bib_db(self._bibfile)
        self._sync_path = PurePath(config["Notes"]["folder"])

    def push_file_to_dpt(self, bibkey):
        """Push file given a bibkey"""
        bib_db = self._bib_db
        bib_name = self._bibname

        d_path = self._get_doc_from_bibkey(bibkey)

        p_bib = self._bib_path
        d_path = p_bib / d_path

        target_folder = self._get_target_folder(bibkey)
        name_file = self._gen_file_name(bibkey)
        remote_path = target_folder / name_file

        self._dpt.new_folder(target_folder)

        with open(d_path, "rb") as fh:
            self._dpt.upload(fh, remote_path)

    def sync_notes(self):
        """Sync the notes from the DPT-RP1 to the computer"""
        ensure_dir(self._sync_path)

        all_notes = self._get_modified_notes(which="notes")

        for doc in all_notes:
            year = dateparser.parse(doc["created_date"]).year
            f_name = doc["entry_name"]
            ensure_dir(self._sync_path / str(year))
            local_path = self._sync_path / str(year) / f_name
            data = self._dpt.download(doc["entry_path"])
            with open(local_path, "wb") as f:
                f.write(data)

    def sync_annotated_docs(self, with_notes=True):
        """Sync annotated documents with their respective notes (if existent)

        Parameters
        ----------
        with_notes : bool, optional

        """
        pass

    def _open_bib_db(self, bibfile):
        """Open the bibtex database"""
        self._bib_path = os.path.dirname(bibfile)

        parser = BibTexParser()
        parser.ignore_nonstandard_types = False

        with open(bibfile) as bib_:
            bib_db = bibtexparser.load(bib_, parser)

        return bib_db

    def _get_target_folder(self, bibkey):
        """Get the forlder where to save the document

        Parameters
        ----------
        bibkey : TODO

        Returns
        -------
        TODO

        """
        d_type = self._get_type_from_bibkey(bibkey)

        # Define name of the target folder
        if self._bibname in [None, "default"]:
            t_folder = "Document/" + OUT_DEF[d_type]["out_folder"]
        else:
            t_folder = "Document/" + self._bibname.capitalize()

        return PurePath(t_folder)

    def _gen_file_name(self, bibkey):
        """TODO: Docstring for gen_file_name.

        Parameters
        ----------
        bibkey : TODO

        Returns
        -------
        TODO

        """
        d_type = self._get_type_from_bibkey(bibkey)

        # Define name of the target file
        name_format = OUT_DEF[d_type]["out_name"]

        entry = self._bib_db.entries_dict[bibkey]

        # Define out folder
        for struct in name_format:
            try:
                out_name = "".join(slugify(entry[ix]) + "_" for ix in struct)
                break
            except:
                pass

        return PurePath(out_name + ".pdf")

    def _get_doc_from_bibkey(self, bibkey):
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
        entry = self._bib_db.entries_dict[bibkey]
        file_entry = entry["file"]
        # Get only the path
        match = re.search("(?<=:).*(?=:)", file_entry)
        file_path = file_entry[match.start() : match.end()]

        return PurePath(file_path)

    def _get_type_from_bibkey(self, bibkey):
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
        entry = self._bib_db.entries_dict[bibkey]
        e_type = entry["ENTRYTYPE"]

        return e_type

    def _get_modified_notes(self, which):
        all_docs = self._dpt.list_documents()
        notes_ = [d for d in all_docs if d["document_type"] == "note"]

        notes = [n for n in notes_ if self._is_modified_note(n)]

        if which == "notes":
            notes = self._get_standalone_notes()
        elif which == "docs":
            notes = self._get_documents_notes()

        return notes

    def _get_annotated_docs(self):
        all_docs = self._dpt.list_documents()
        docs_ = [d for d in all_docs if d["document_type"] == "normal"]

        docs = [d for d in docs_ if self._is_annotated_doc(d)]

        return docs

    def _get_documents(self):
        all_docs = self._dpt.list_documents()
        notes = [d for d in all_docs if d["document_type"] == "normal"]

        return notes

    def _is_modified_note(self, doc):
        year = dateparser.parse(doc["created_date"]).year

        if doc["document_type"] == "note":
            local_path = (
                self._sync_path / str(year) / os.path.basename(doc["entry_path"])
            )
            if not os.path.exists(local_path):
                return True
            else:
                return (
                    os.path.getmtime(local_path)
                    < dateparser.parse(doc["modified_date"]).timestamp()
                )

    def _is_annotated_doc(self, doc):
        created = dateparser.parse(doc["created_date"])
        modified = dateparser.parse(doc["modified_date"])

        if created < modified:
            return True
        else:
            return False

    def _get_standalone_notes(self, docs=None):
        if docs == None:
            all_docs = self._dpt.list_documents()
            docs = [d for d in all_docs if d["document_type"] == "note"]

        notes = [n for n in docs if os.path.dirname(n["entry_path"]) == "Document/Note"]

        return notes

    def _get_documents_notes(self, docs=None):
        if docs == None:
            all_docs = self._dpt.list_documents()
            docs = [d for d in all_docs if d["document_type"] == "note"]

        notes = [n for n in docs if os.path.dirname(n["entry_path"]) != "Document/Note"]

        return notes


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
    config["Notes"] = {"folder": ""}

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
