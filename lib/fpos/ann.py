import hashlib
import os
import pygenann
import xdg
from pystrgrp import Strgrp
import itertools
from random import shuffle
import sys
import traceback
from collections import namedtuple
import sqlite3

def to_input(string):
    return [float(ord(x)) for x in string]

salt = "382a55c995b1e53f3ad0a3ed1c5ae735b9c7adc0".encode("UTF-8")

class StatusLine(object):
    def __init__(self):
        self.line = ""
        pass

    def write(self, line, terminate=False):
        erase = '\b' * max(0, len(self.line) - len(line))
        print("{}\r{}".format(erase, line), end='', flush=True)
        self.line = line;
        if terminate:
            self.terminate()

    def terminate(self):
        print("", flush=True)
        self.line = ""

class PolarisationDetector(object):
    """ Undocumented state machine!"""

    def __init__(self, limit=5):
        self.S0, self.S1, self.S2, self.S3, self.S4, self.S5, self.S6, self.S7 = list(range(0, 8))
        self.s = self.S0
        self.polarised = { self.S6, self.S7 }
        self.count = 0
        self.limit = limit

    def enter(self, state):
        if state in self.polarised:
            self.count += 1

        self.s = state

    def accept(self, val):
        if self.s == self.S0:
            if val:
                self.enter(self.S1)
        elif self.s == self.S1:
            if not val:
                self.enter(self.S4)
        elif self.s == self.S2:
            if val:
                self.enter(self.S3)
        elif self.s == self.S3:
            if not val:
                self.enter(self.S2)
        elif self.s == self.S4:
            if val:
                self.enter(self.S1)
        elif self.s == self.S5:
            if val:
                self.s == self.S7
        elif self.s == self.S6:
            if val:
                self.enter(self.S3)
        else:
            assert self.s == self.S7
            if not val:
                self.enter(self.S0)

    def reject(self, val):
        if self.s == self.S0:
            if val:
                self.enter(self.S2)
        elif self.s == self.S1:
            if val:
                self.enter(self.S3)
        elif self.s == self.S2:
            if not val:
                self.enter(self.S5)
        elif self.s == self.S3:
            if not val:
                self.enter(self.S1)
        elif self.s == self.S4:
            if val:
                self.enter(self.S6)
        elif self.s == self.S5:
            if val:
                self.enter(self.S2)
        elif self.s == self.S6:
            if not val:
                self.enter(self.S0)
        else:
            assert self.s == self.S7
            if val:
                self.enter(self.S3)

    def is_polarised(self):
        r = (self.s in self.polarised and ((self.count % self.limit) == 0))
        return r

def gen_id(description, salt):
    s = hashlib.sha1()
    s.update(str(description).encode("UTF-8"))
    s.update(salt)
    return s.hexdigest()

class AnnCollection(object):
    def __init__(self, ann_id, data_dir=None):
        self.data_dir = self.get_data_dir(data_dir)
        self.ann_id = ann_id

    def get_data_dir(self, data_dir=None):
        if data_dir is None:
            path = str(xdg.BaseDirectory.save_data_path("fpos"))
        else:
            path = data_dir
        os.makedirs(path, exist_ok=True)
        return path

    def have_ann(self, did):
        raise NotImplementedError

    def is_canonical(self, did):
        raise NotImplementedError

    def get_canonical(self, did):
        raise NotImplementedError

    def load(self, did):
        raise NotImplementedError

    def load_metadata(self, did):
        raise NotImplementedError

    def store(self, did, ann):
        raise NotImplementedError

    def store_metadata(self, did, accept, reject, accepted):
        raise NotImplementedError

    def associate(self, cdid, adid):
        raise NotImplementedError

class SqlAnnCollection(AnnCollection):
    def __init__(self, data_dir=None):
        super().__init__(self, data_dir)
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

    def __enter__(self):
        self.db = sqlite3.connect(self.get_db_path())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.commit()
        self.db.close()

    def init_db(self, db):
        c = db.cursor()
        c.execute('''
        CREATE TABLE nn (
            did         TEXT PRIMARY KEY,
            accept      INTEGER NOT NULL,
            reject      INTEGER NOT NULL,
            ann         BLOB NOT NULL
        )''')
        c.execute('''
        CREATE TABLE assoc (
            ddid        TEXT PRIMARY KEY,
            sdid        TEXT NOT NULL
        )''')
        c.execute('''
        CREATE INDEX idx_assoc_sdid on assoc (sdid)
        ''')

    def have_ann(self, did):
        c = self.db.cursor()
        c.execute('SELECT COUNT(*) FROM assoc WHERE ddid=?', (did, ))
        res = c.fetchone()
        val = int(res[0])
        return val > 0

    def get_canonical(self, did):
        c = self.db.cursor()
        c.execute('SELECT sdid FROM assoc WHERE ddid=?', (did, ))
        return c.fetchone()[0]

    def is_canonical(self, did):
        c = self.db.cursor()
        c.execute('SELECT COUNT(*) FROM nn WHERE did=?', (did, ))
        return bool(c.fetchone())

    def load(self, did, description):
        if self.have_ann(did):
            c = self.db.cursor()
            c.execute('SELECT ann FROM nn, assoc WHERE assoc.ddid = ? and nn.did = assoc.sdid ', (did, ))
            nn = c.fetchone()[0]
            ann = pygenann.genann.loads(nn)
            return DescriptionAnn(did, ann, self)

        ann = pygenann.genann(100, 2, 100, 1)
        da = DescriptionAnn(did, ann, self)
        da.accept(description)
        return da

    def load_metadata(self, did):
        c = self.db.cursor()
        c.execute('SELECT accept, reject FROM nn, assoc WHERE assoc.ddid = ? and nn.did = assoc.sdid', (did, ))
        res = c.fetchone()
        if res is None:
            return did, False, False, set()
        else:
            accept, reject = res
        cdid = self.get_canonical(did)
        c.execute('SELECT ddid FROM assoc WHERE sdid = ?', (cdid, ))
        accepted = set(x[0] for x in c.fetchall())
        return did, accept, reject, accepted

    def store(self, did, ann):
        c = self.db.cursor()
        if self.have_ann(did):
            c.execute('UPDATE nn SET ann = ? WHERE did = ?', (ann.dumps(), did))
        else:
            c.execute('INSERT INTO nn (did, accept, reject, ann) VALUES (?, 0, 0, ?)',
                    (did, ann.dumps()))
            self.associate(did, did)

    def store_metadata(self, did, accept, reject, accepted):
        if not self.have_ann(did):
            raise ValueError("No such ID: {}".format(did))

        c = self.db.cursor()
        c.execute('UPDATE nn SET accept = ?, reject = ? WHERE did = ?',
                (accept, reject, self.get_canonical(did)))

    def associate(self, cdid, adid):
        c = self.db.cursor()
        if self.have_ann(adid):
            q = 'select sdid from assoc where ddid = ?'
            assert c.execute(q, (adid, )).fetchone()[0] == cdid
        else:
            c.execute('INSERT INTO assoc (ddid, sdid) VALUES (?, ?)', (adid, cdid))

class FsAnnCollection(AnnCollection):
    @staticmethod
    def gen_rel_dentries(did):
        return did[:2], did[2:]

    def __init__(self, data_dir=None):
        super().__init__(self, data_dir)
        print("FsAnnCollection")
        raise ValueError

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def _get_path(self, did):
        dentries = FsAnnCollection.gen_rel_dentries(did)
        return os.path.join(self.data_dir, *dentries)

    def get_data_dir(self, path=None):
        base = super().get_data_dir(path)
        path = os.path.join(base, "ann", "descriptions")
        os.makedirs(path, exist_ok=True)
        return path

    def have_ann(self, did):
        return os.path.exists(self._get_path(did))

    def _get_canonical(self, path):
        if os.path.islink(path):
            return os.readlink(path)
        return path

    def get_canonical(self, did):
        path = self._get_canonical(self._get_path(did))
        if os.path.exists(path + ".properties"):
            with open(path + ".properties", "r") as f:
                return f.readline().strip() # First line is the NN ID
        return did

    def is_canonical(self, did):
        cdid = self.get_canonical(description)
        return did == cdid

    def load(self, did, description):
        if self.have_ann(did):
            ann = pygenann.genann.read(self._get_path(did))
            return DescriptionAnn(did, ann, self)

        ann = pygenann.genann(100, 2, 100, 1)
        da = DescriptionAnn(did, ann, self)
        da.accept(description)
        return da

    def load_metadata(self, did):
        prop_path = self._get_path(self.get_canonical(did)) + ".properties"
        if not os.path.exists(prop_path):
            return did, False, False, set()

        with open(prop_path, "r", encoding="utf-8") as f:
            did = f.readline().strip()
            accept = f.readline().strip() == "True"
            reject = f.readline().strip() == "True"
            accepted = set()
            for line in f:
                accepted.add(line.strip())
            return (did, accept, reject, accepted)

    def store(self, did, ann):
        dentries = FsAnnCollection.gen_rel_dentries(did)
        path = os.path.join(self.data_dir, *dentries)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ann.write(path)

    def store_metadata(self, did, accept, reject, accepted):
        dentries = FsAnnCollection.gen_rel_dentries(did)
        path = os.path.join(self.data_dir, *dentries)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".properties", "w", encoding="utf-8") as f:
            f.write("{}\n".format(did))
            f.write("{}\n".format(repr(accept)))
            f.write("{}\n".format(repr(reject)))
            for did in accepted:
                f.write("{}\n".format(did))

    def associate(self, cdid, adid):
        src = self._get_path(cdid)
        dst = self._get_path(adid)
        if os.path.exists(dst):
            assert os.readlink(dst) == src
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.symlink(src, dst)

class DescriptionAnn(object):
    def __init__(self, did, ann, backend, polarised=None):
        self.id = did
        self.ann = ann

        self.ready = dict()
        vals = backend.load_metadata(self.id)
        self.ready['accept'] = vals[1]
        self.ready['reject'] = vals[2]
        self.accepted = vals[3]
        self.threshold = 3
        self.backend = backend

        if None is polarised:
            polarised = PolarisationDetector()
        self.pd = polarised

        self.pd.accept(self.ready['accept'])
        self.pd.reject(self.ready['reject'])

    def is_trained(self):
        return self.ready['accept'] and self.ready['reject']

    def is_polarised(self):
        return self.pd.is_polarised() 

    def meets_threshold(self):
        return len(self.accepted) > self.threshold

    def is_ready(self):
        return self.is_trained() and self.meets_threshold()

    def read_metadata(self):
        vals = self.backend.read_metadata(self.id)

    def write(self):
        self.backend.store(self.id, self.ann)

    def write_metadata(self):
        self.backend.store_metadata(self.id, self.ready['accept'], self.ready['reject'], self.accepted)

    def cache(self, description):
        if not self.backend.have_ann(self.id) or self.is_ready():
            self.write()
            self.write_metadata()

        did = gen_id(description, salt)
        if self.id != did:
            self.backend.associate(self.id, did)

    def accept(self, description, iters=300):
        # FIXME: 0.5
        accepted = self.ann.run(to_input(description))[0] >= 0.5
        self.pd.accept(accepted)
        self.ready['accept'] = accepted
        self.accepted.add(gen_id(description, salt))
        self.ann.train(to_input(description), [1.0], 3, iters=iters)
        self.cache(description)
        return self.ready['accept']

    def reject(self, description, iters=300, write=True):
        # FIXME: 0.5
        rejected = self.ann.run(to_input(description))[0] < 0.5
        self.pd.reject(rejected)
        self.ready['reject'] = rejected
        ret = self.ann.train(to_input(description), [0.0], 3, iters=iters)
        if write and self.is_ready():
            self.write()
        return self.ready['reject']

    def run(self, description):
        return self.ann.run(to_input(description))[0]

class CognitiveStrgrp(object):
    """ LOL """
    def __init__(self):
        self._collection = SqlAnnCollection()
        self._strgrp = Strgrp()
        self._grpanns = dict()
        self._status = StatusLine()

    def __iter__(self):
        return iter(self._strgrp)

    def __enter__(self):
        self._collection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._collection.__exit__(exc_type, exc_value, traceback)

    def _request_match(self, description, haystack):
        index = None
        need = True

        # None Of The Above
        nota = len(haystack)
        print("Which description best matches '{}'?".format(description))
        print()
        for i, needle in enumerate(haystack):
            print("[{}]\t{}".format(i, needle.key()))
        print("[{}]\tNone of the above".format(nota))
        print()

        while need:
            result = input("Select [0]: ")
            if len(result) == 0:
                result = 0
            try:
                index = int(result)
                need = not (0 <= index <= nota)
                if need:
                    print("\nInvalid value: {}".format(index))
            except ValueError:
                print("\nNot a number: '{}'".format(result))
                need = True

        if index == nota:
            return None

        return haystack[index]

    def _split_heap(self, heap):
        i = None
        for i, grpbin in enumerate(heap):
            if grpbin.is_acceptible(self._strgrp):
                key = gen_id(grpbin.key(), salt)
                if key not in self._grpanns:
                    self._grpanns[key] = self._collection.load(key, grpbin.key())
            else:
                break
        return heap[:i], heap[i:]

    def _train_positive(self, description, pick, candidates, hay):
        ann = self._grpanns[gen_id(pick.key(), salt)]

        accept = list(item.key() for item in pick)
        shuffle(accept)
        accept.insert(0, description)

        reject = [ x.key() for x in candidates if x is not pick ]
        reject.extend(hay[:max(7, len(accept) - len(reject))])
        shuffle(reject)

        i = 0
        while not (ann.accept(description) and ann.is_trained()):
            for (needle, straw) in zip(itertools.cycle(accept), reject):
                score = ann.run(description)
                line = "Positive training: ({}, {}, {}, {})".format(i, ann.ready,
                            ann.pd.count, score)
                self._status.write(line)

                if ann.is_trained():
                    break

                ann.reject(straw)
                ann.accept(needle)
                i += 1

                if ann.is_polarised():
                    break;

            if ann.is_polarised():
                break;

        score = ann.run(description)
        if i > 0:
            line = "Positive training: ({}, {}, {}, {})".format(i, ann.ready,
                        ann.pd.count, score)
            self._status.write(line, terminate=True)

        if ann.is_polarised():
            print("Observed {} polarisation events, not enough training material".format(ann.pd.limit))

    def _train_negative(self, description, grp, candidates, hay):
        ann = self._grpanns[gen_id(grp.key(), salt)]
        accept = list(item.key() for item in grp)
        shuffle(accept)

        reject = [ i.key() for x in candidates if x is not grp for i in grp ]
        reject.extend(hay[:max(7, len(reject))])
        shuffle(reject)
        reject = reject[:max(7, len(accept))]
        reject.insert(0, description)

        seq = itertools.cycle(zip(itertools.cycle(accept), reject))
        pred = lambda x: not (ann.is_trained() or ann.is_polarised())
        i = 0
        while not (ann.reject(description) and ann.is_trained()):
            for (needle, straw) in itertools.takewhile(pred, seq):
                score = ann.run(description)
                line = "Negative training: ({}, {}, {}, {})".format(i, ann.ready,
                            ann.pd.count, score)
                self._status.write(line)
                # Also train on the initial description
                ann.accept(needle)
                ann.reject(straw)
                i += 1

            if ann.is_polarised():
                break;

        score = ann.run(description)
        if i > 0:
            line = "Negative training: ({}, {}, {}, {})".format(i, ann.ready,
                        ann.pd.count, score)
            self._status.write(line, terminate=True)

        if ann.is_polarised():
            print("Observed {} polarisation events, not enough training material".format(ann.pd.limit))

    def train(self, description, pick, candidates, hay):
        shuffle(hay)
        # Black magic follows: Hacky attempt at training NNs.
        if pick:
            self._train_positive(description, pick, candidates, hay)

        for grp in candidates:
            if grp is pick:
                continue
            self._train_negative(description, grp, candidates, hay)

    def find_group(self, description):
        print("\nFinding group for '{}'".format(description))
        # Check for an exact match, don't need fuzzy behaviour if we have one
        grpbin = self._strgrp.grp_exact(description)
        if grpbin is not None:
            assert gen_id(grpbin.key(), salt) in self._grpanns
            print("Existing group: Exact match")
            return grpbin

        # Check for an existing mapping on disk
        did = gen_id(description, salt)
        if self._collection.have_ann(did):
            # Add description to a group that has an on-disk mapping:
            cid = self._collection.get_canonical(did)
            if cid in self._grpanns:
                # Group is already loaded
                print("Existing group: From on-disk NN mapping")
                return self._strgrp.grp_exact(self._grpanns[cid].description)
            # Likely the result of a time-bounded window on the database
            print("New group: Found on-disk NN mapping")
            return None

        # Use a binary output NN trained for each group to determine
        # membership. Leverage the groups generated with strgrp as training
        # sets, with user feedback to break ambiguity

        # needles is the set of groups breaking the strgrp fuzz threshold.
        # These are the candidates groups for the current description.
        needles, hay = self._split_heap(self._strgrp.grps_for(description))
        l_needles = len(needles)
        if l_needles == 0:
            print("New group: No needles in the haystack")
            return None

        # Score the description using each group's NN, to see if we find a
        # single candidate among the needles. If we do then we assume this is
        # the correct group
        anns = [ self._grpanns[gen_id(grpbin.key(), salt)]
                    for grpbin in needles ]
        scores = [ ann.run(description) for ann in anns ]
        # FIXME: 0.5
        passes = [ x >= 0.5 for x in scores ]
        n_passes = sum(passes)
        ready = [ ann.is_ready() for ann in anns ]
        hay_keys = [ grp.key() for grp in hay ]
        if all(ready):
            # if n_passes == 1 or (l_needles > 1 and n_passes == l_needles):
            if n_passes == 1:
                i = passes.index(True)
                self.train(description, needles[i], needles, hay_keys)
                print("Existing group: All NNs ready, one matched")
                return needles[i]
        elif all(ann.ready['reject'] for ann in anns):
            if n_passes == 1:
                print("One passing while all reject")
                i = passes.index(True)
                if anns[i].is_ready():
                    self.train(description, needles[i], needles, hay_keys)
                    print("Existing group: passing group is ready, under all-reject")
                    return needles[i]

        print("scores: {}".format(scores))
        print("passes: {}".format(passes))
        print("ready: {}".format(ready))

        # Otherwise get user input
        match = self._request_match(description, needles)

        # None means no group was matched an a new one should be created
        try:
            if match is None:
                self.train(description, None, needles, hay_keys)
                for ann in anns:
                    ann.write()
                print("New group: User provided answer")
                return None

            # Otherwise, if the user confirmed membership of the description to a
            # candidate group, if the NN correctly predicted the membership then
            # mark it as ready to use
            self.train(description, match, needles, [grp.key() for grp in hay])
            print("Existing group: User provided answer")
            return match
        finally:
            print()

    def insert(self, description, data, grpbin):
        if grpbin is None:
            print("New group for description '{}'".format(description))
            key = gen_id(description, salt)
            grpbin = self._strgrp.grp_new(description, data)
            self._grpanns[key] = self._collection.load(key, grpbin.key())
        else:
            print("Adding to group of '{}'".format(grpbin.key()))
            assert gen_id(grpbin.key(), salt) in self._grpanns
            grpbin.add(self._strgrp, description, data)

    def add(self, description, data):
        self.insert(description, data, self.find_group(description))
