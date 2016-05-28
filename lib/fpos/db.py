#!/usr/bin/python3
#
#    Initialises an fpos CSV database
#    Copyright (C) 2015  Andrew Jeffery <andrew@aj.id.au>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from .annotate import annotate
from .combine import combine
from configparser import ConfigParser
from itertools import chain
from .transform import transform
from .window import window
from .visualise import visualise
from xdg import BaseDirectory as bd
import argparse
import csv
import os
import shutil
import sys
import tempfile
import toml

cmd_description = \
        """Manage fpos CSV databases"""

cmd_help = cmd_description

def find_config(config_dir=None):
    if not config_dir:
        config_dir = bd.save_config_path("fpos")
    return os.path.join(config_dir, "fpos")

def as_toml(path, mode="r"):
    with open(path, mode) as handle:
        try:
            return toml.load(handle)
        except:
            pass
    print("Upgrading '{}' from INI to TOML".format(path))
    try:
        config = ConfigParser()
        config.read(path)
        tf = tempfile.NamedTemporaryFile("w", delete=False)
        toml.dump(config._sections, tf)
        tf.close()
        print("Succesfully upgraded '{}' to TOML".format(path))
    except:
        print("Failed to upgrade '{}' to TOML".format(path))
        raise TypeError("Couldn't convert to TOML")
    else:
        shutil.move(tf.name, path)
        return as_toml(path)

def name():
    return __name__.split(".")[-1]

def db_init(args):
    config = {}
    config_file = find_config()
    if os.path.exists(config_file):
        config = as_toml(config_file)
    if args.nickname in config:
        fmt = "Database with nickname '{}' already exists"
        raise ValueError(fmt.format(args.nickname))
    db_file = os.path.realpath(args.path)
    config[args.nickname] = {}
    config[args.nickname]["path"] = db_file
    config[args.nickname]["version"] = "1"
    with open(config_file, "w") as config_fo:
        toml.dump(config, config_fo)
    if not os.path.exists(db_file):
        open(args.path, "w").close()

def db_update(args):
    config = as_toml(find_config())
    if args.nickname not in config:
        fmt = "Unknown database '{}'"
        raise ValueError(fmt.format(args.nickname))
    db_path = config[args.nickname]["path"]
    tf = tempfile.NamedTemporaryFile("w", delete=False)
    with open(db_path, "r") as db:
        irdocs = []
        for doc in args.updates:
            try:
                irdocs.append(transform("auto", csv.reader(doc)))
            except KeyError as e:
                print("Discovered unsupported type tuple {} in {}".format(str(e), doc.name))
                print()
                print("Failed to transform CSV in {}, cannot complete update".format(doc.name))
                sys.exit(1)
        csv.writer(tf).writerows(
                annotate(
                    combine(
                        chain(irdocs, [csv.reader(db)]))))
        tf.close()
    shutil.move(tf.name, db_path)

def db_show(args):
    config = as_toml(find_config())
    db_file = config[args.nickname]["path"]
    with open(db_file, "r") as db:
        visualise(list(window(csv.reader(db), relspan=12)), save=args.save)

def parse_args(subparser):
    sc_init = subparser.add_parser("init")
    sc_init.add_argument("nickname", metavar="STRING", help="Nickname for the database")
    sc_init.add_argument("path", metavar="FILE", help="Absolute path to the database")
    sc_init.set_defaults(db_func=db_init)
    sc_update = subparser.add_parser("update")
    sc_update.add_argument("nickname", metavar="STRING", help="Nickname for the database")
    sc_update.add_argument("updates", metavar="FILE", type=argparse.FileType('r'), nargs="+",
            help="Do everything")
    sc_update.set_defaults(db_func=db_update)
    sc_show = subparser.add_parser("show")
    sc_show.add_argument("nickname", metavar="STRING", help="Nickname for the database")
    sc_show.add_argument("--save", type=float, default=0)
    sc_show.set_defaults(db_func=db_show)
    return [ sc_init, sc_update, sc_show ]

def main(args):
    args.db_func(args)
