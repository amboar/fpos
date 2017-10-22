from pystrgrp import Strgrp
import hashlib
import os
import sqlite3
import traceback
import xdg

salt = "382a55c995b1e53f3ad0a3ed1c5ae735b9c7adc0".encode("UTF-8")

def gen_id(description, salt):
    s = hashlib.sha1()
    s.update(str(description).encode("UTF-8"))
    s.update(salt)
    return s.hexdigest()

class GroupProtocol(object):
    def __enter__(self):
        raise NotImplementedError

    def __exit__(self):
        raise NotImplementedError

    def _request_match(self, description, haystack):
        index = None
        need = True

        print("Which description best matches the following?\n\t{}".format(description))
        print()
        for i, needle in enumerate(haystack):
            print("[{}]\t{}".format(i, needle.key()))
        print("[n]\tNone of the above")
        print()

        while need:
            result = input("Select [0]: ")
            if len(result) == 0:
                result = 0

            if result == "n":
                return None

            try:
                index = int(result)
                need = not (0 <= index < len(haystack))
                if need:
                    print("\nInvalid value: {}".format(index))
            except ValueError:
                print("\nNot a number: '{}'".format(result))
                need = True

        return haystack[index]

    def find_group(self, description):
        raise NotImplementedError

    def insert(self, description, value, group):
        raise NotImplementedError

class SqlGroupCollection(object):
    def __init__(self, data_dir=None):
        self.data_dir = data_dir if data_dir else str(xdg.BaseDirectory.save_data_path("fpos"))
        self.db = None
        path = self.get_db_path()
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            db = sqlite3.connect(path)
            self.init_db(db)
            db.commit()
            db.close()

    def get_db_path(self):
        return os.path.join(self.data_dir, "descriptions.db")

    def init_db(self, db):
        c = db.cursor()
        c.execute('''
        CREATE TABLE assoc (
            ddid        TEXT PRIMARY KEY,
            sdid        TEXT NOT NULL,
            FOREIGN KEY (sdid) REFERENCES nn(did)
        )''')
        c.execute('''
        CREATE INDEX idx_assoc_sdid on assoc (sdid)
        ''')

    def __enter__(self):
        self.db = sqlite3.connect(self.get_db_path())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.commit()
        self.db.close()

    def have_association(self, did):
        c = self.db.cursor()
        c.execute('SELECT COUNT(*) FROM assoc WHERE ddid=?', (did, ))
        return int(c.fetchone()[0]) > 0

    def get_canonical(self, did):
        c = self.db.cursor()
        c.execute('SELECT sdid FROM assoc WHERE ddid=?', (did, ))
        return c.fetchone()[0]

    def associate(self, cdid, adid):
        c = self.db.cursor()
        c.execute('INSERT INTO assoc (ddid, sdid) VALUES (?, ?)', (adid, cdid))

class DynamicGroups(GroupProtocol):
    def __init__(self, threshold=0.85, size=4, backend=None):
        if backend is None:
            backend = SqlGroupCollection()
        self.backend = backend
        self._strgrp = Strgrp(threshold=threshold, size=size)
        self.size = size
        self.threshold = threshold
        self.map = dict()

    def __iter__(self):
        return iter(self._strgrp)

    def __enter__(self):
        self.backend.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.backend.__exit__(exc_type, exc_value, traceback)

    def _split_heap(self, heap):
        i = None

        for i, grpbin in enumerate(heap):
            acceptable = grpbin.is_acceptible(self._strgrp)
            if not acceptable:
                r = (heap[:i], heap[i:])
                break
        else:
            r = (heap, [])

        return r

    def find_group(self, description):
        grpbin = self._strgrp.grp_exact(description)
        if grpbin is not None:
            return grpbin

        did = gen_id(description, salt)
        if self.backend.have_association(did):
            cid = self.backend.get_canonical(did)
            if cid in self.map:
                return self._strgrp.grp_exact(self.map[cid])
            return None

        heap = self._strgrp.grps_for(description)

        if self.size == 0:
            return heap[0] if len(heap) else None

        needles, haystack = self._split_heap(heap)
        if len(needles) == 0:
            return None

        dynamic = [n.is_dynamic(self._strgrp) for n in needles]
        if sum(dynamic) == 1:
            return needles[dynamic.index(True)]

        # Otherwise get user input
        return self._request_match(description, needles)

    def insert(self, description, value, group=None):
        did = gen_id(description, salt)
        if group:
            group.add(self._strgrp, description, value)
            gid = gen_id(group.key(), salt)
            cid = self.backend.get_canonical(gid);
            if not self.backend.have_association(did):
                self.backend.associate(cid, did)
        else:
            group = self._strgrp.add(description, value)
            if self.backend.have_association(did):
                cid = self.backend.get_canonical(did)
                self.map[cid] = description
            else:
                self.map[did] = description
                self.backend.associate(did, did)

        return group

    def add(self, description, value):
        return self.insert(description, value, self.find_group(description))
