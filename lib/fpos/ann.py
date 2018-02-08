import hashlib
import os
import pygenann
import xdg
from pystrgrp import Strgrp
import itertools
from random import shuffle
import random
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
                self.enter(self.S5)

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
                self.enter(self.S4)
        else:
            assert self.s == self.S7
            if val:
                self.enter(self.S3)

    def reset(self):
        self.count = 0

    def is_polarised(self):
        return (self.s in self.polarised and (self.count == self.limit))

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
            sdid        TEXT NOT NULL,
            FOREIGN KEY (sdid) REFERENCES nn(did)
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
            return DescriptionAnn(description, did, ann, self)

        # See: https://stats.stackexchange.com/questions/181/how-to-choose-the-number-of-hidden-layers-and-nodes-in-a-feedforward-neural-netw
        ann = pygenann.genann(100, 1, 50, 1)
        da = DescriptionAnn(description, did, ann, self)
        # da.accept(description)
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
        return did, bool(accept), bool(reject), accepted

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
            return DescriptionAnn(description, did, ann, self)

        # See: https://stats.stackexchange.com/questions/181/how-to-choose-the-number-of-hidden-layers-and-nodes-in-a-feedforward-neural-netw
        ann = pygenann.genann(100, 1, 50, 1)
        da = DescriptionAnn(description, did, ann, self)
        # da.accept(description)
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
    def __init__(self, description, did, ann, backend, polarised=None):
        self.description = description
        self.id = did
        self.ann = ann

        self.ready = dict()
        vals = backend.load_metadata(self.id)
        self.ready['accept'] = vals[1]
        self.ready['reject'] = vals[2]
        self.accepted = vals[3]
        self.threshold = 5
        self.backend = backend
        self.ready['ever'] = self.is_ready()

        if None is polarised:
            polarised = PolarisationDetector(limit=50)
        self.pd = polarised

        self.pd.accept(self.ready['accept'])
        self.pd.reject(self.ready['reject'])

    def is_trained(self):
        return self.ready['accept'] and self.ready['reject']

    def reset_polarised(self):
        self.pd.reset()

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

    def _learning_rate(self):
        if not self.ready['ever']:
            self.ready['ever'] = self.is_ready()
        return 0.5 if self.ready['ever'] else 3

    def accept(self, description, iters=300):
        # FIXME: 0.5
        accepted = self.ann.run(to_input(description))[0] >= 0.5
        self.pd.accept(accepted)
        self.ready['accept'] = accepted
        self.accepted.add(gen_id(description, salt))
        self.ann.train(to_input(description), [1.0], self._learning_rate(), iters=iters)
        self.cache(description)
        return self.ready['accept']

    def reject(self, description, iters=300, write=True):
        # FIXME: 0.5
        rejected = self.ann.run(to_input(description))[0] < 0.5
        self.pd.reject(rejected)
        self.ready['reject'] = rejected
        ret = self.ann.train(to_input(description), [0.0], self._learning_rate(), iters=iters)
        if write and self.is_ready():
            self.write()
        return self.ready['reject']

    def run(self, description):
        return self.ann.run(to_input(description))[0]

    def reset(self):
        # See: https://stats.stackexchange.com/questions/181/how-to-choose-the-number-of-hidden-layers-and-nodes-in-a-feedforward-neural-netw
        self.ann = pygenann.genann(100, 1, 50, 1)
        self.ready['accept'] = False
        self.ready['reject'] = False
        self.pd.reset()
        # Copy accepted as accept() updates it
        fixup = set(self.accepted)
        for desc in fixup:
            self.accept(desc)
        self.write()
        self.write_metadata()

class GroupProtocol(object):
    def __enter__(self):
        raise NotImplementedError

    def __exit__(self):
        raise NotImplementedError

    def _request_match(self, description, haystack):
        index = None
        need = True

        # None Of The Above
        print("Which description best matches '{}'?".format(description))
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

class BestGroup(GroupProtocol):
    def __init__(self):
        self._strgrp = Strgrp()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def find_group(self, description):
        return self._strgrp.grp_for(description)

    def insert(self, description, value, group=None):
        if group:
            group.add(self._strgrp, description, value)
        else:
            self._strgrp.add(description, value)

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
                break

        return ([], heap) if i is None else (heap[:i], heap[i:])

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

        needles, haystack = self._split_heap(self._strgrp.grps_for(description))
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

class CognitiveGroups(GroupProtocol):
    """ LOL """
    def __init__(self):
        self._collection = SqlAnnCollection()
        self._strgrp = Strgrp(threshold=0.73)
        self._grpanns = dict()
        self._status = StatusLine()

    def __iter__(self):
        return iter(self._strgrp)

    def __enter__(self):
        self._collection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._collection.__exit__(exc_type, exc_value, traceback)

    def _split_heap(self, heap):
        i = None
        for i, grpbin in enumerate(heap):
            if grpbin.is_acceptible(self._strgrp):
                key = gen_id(grpbin.key(), salt)
                if key not in self._grpanns:
                    self._grpanns[key] = self._collection.load(key, grpbin.key())
            else:
                break
        return ([], heap) if i is None else (heap[:i + 1], heap[i + 1:])

    def _train_positive(self, description, pick, candidates, hay):
        ann = self._grpanns[gen_id(pick.key(), salt)]

        accept = list(item.key() for item in pick)
        shuffle(accept)
        accept.insert(0, description)

        reject = [ i.key() for x in candidates if x is not pick for i in x ]
        shuffle(reject)
        reject = reject[:max(4, len(accept) // 2)]
        reject.extend(hay[:max(16, 3 * len(reject) // 4)])
        shuffle(reject)

        # Make sure we have something to reject against.
        #
        # XXX: What happens for these early cases?
        if len(reject) < 4:
            return

        i = 0
        ann.reset_polarised()
        while not (ann.accept(description) and ann.reject(random.choice(reject)) and ann.is_trained()):
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

                if ann.is_polarised() or i >= 1000:
                    break

            if ann.is_polarised() or i >= 1000:
                break

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
        print(grp.key() + ":")
        print(*(["\t"] + accept), sep="\n\t")
        print()

        reject = [ i.key() for x in candidates if x is not grp for i in x ]
        shuffle(reject)
        reject = reject[:max(4, len(accept) // 2)]
        reject.extend(hay[:max(16, 3 * len(reject) // 4)])
        reject.insert(0, description)
        shuffle(reject)
        print(*(["\t"] + reject), sep="\n\t")
        print()

        seq = itertools.cycle(zip(itertools.cycle(accept), reject))
        pred = lambda x: not ((ann.is_trained() if ann.meets_threshold() else ann.ready['reject']) or ann.is_polarised())
        i = 0

        ann.reset_polarised()
        while not (ann.reject(description) and (ann.is_trained() if ann.meets_threshold() else True)):
            for (needle, straw) in itertools.takewhile(pred, seq):
                score = ann.run(description)
                line = "Negative training: ({}, {}, {}, {})".format(i, ann.ready,
                            ann.pd.count, score)
                self._status.write(line)
                ann.accept(needle)
                ann.reject(straw)
                i += 1

                if i >= 1000:
                    break

            if ann.is_polarised() or i >= 1000:
                break

        score = ann.run(description)
        if i > 0:
            line = "Negative training: ({}, {}, {}, {})".format(i, ann.ready,
                        ann.pd.count, score)
            self._status.write(line, terminate=True)

        if ann.is_polarised():
            print("Observed {} polarisation events, not enough training material".format(ann.pd.limit))

        # Lets try again, avoid long delays training nets into the ground
        if i >= 1000:
            ann.reset()
        else:
            pred = lambda x: not ann.is_trained()
            for desc in itertools.takewhile(pred, [ i.key() for i in grp]):
                ann.accept(desc)

    def train(self, description, pick, candidates, hay):
        shuffle(hay)
        # Black magic follows: Hacky attempt at training NNs.
        if pick:
            self._train_positive(description, pick, candidates, hay)

        for grp in candidates:
            if grp is not pick:
                self._train_negative(description, grp, candidates, hay)

    def find_group(self, description):
        # Check for an exact match, don't need fuzzy behaviour if we have one
        grpbin = self._strgrp.grp_exact(description)
        if grpbin is not None:
            assert gen_id(grpbin.key(), salt) in self._grpanns
            return grpbin

        # Check for an existing mapping on disk
        did = gen_id(description, salt)
        if self._collection.have_ann(did):
            # Add description to a group that has an on-disk mapping:
            cid = self._collection.get_canonical(did)
            if did in self._grpanns or cid in self._grpanns:
                # Group is already loaded
                return self._strgrp.grp_exact(self._grpanns[cid].description)
            # Likely the result of a time-bounded window on the database
            return None

        # Use a binary output NN trained for each group to determine
        # membership. Leverage the groups generated with strgrp as training
        # sets, with user feedback to break ambiguity

        # needles is the set of groups breaking the strgrp fuzz threshold.
        # These are the candidates groups for the current description.
        needles, hay = self._split_heap(self._strgrp.grps_for(description))
        hay = [ random.choice(list(grp)).key() for grp in hay ]
        l_needles = len(needles)
        if l_needles == 0:
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
        if n_passes == 1:
            if all(ready):
                    i = passes.index(True)
                    self.train(description, needles[i], needles, hay)
                    return needles[i]
            elif all(ann.ready['reject'] for ann in anns):
                    i = passes.index(True)
                    if anns[i].is_ready():
                        self.train(description, needles[i], needles, hay)
                        return needles[i]

        print("scores: {}".format(scores))
        print("passes: {}".format(passes))
        print("ready: {}".format(ready))

        # Otherwise get user input
        match = self._request_match(description, needles)

        # None means no group was matched an a new one should be created
        try:
            if match is None:
                self.train(description, None, needles, hay)
                for ann in anns:
                    ann.write()
                return None

            # Otherwise, if the user confirmed membership of the description to a
            # candidate group, if the NN correctly predicted the membership then
            # mark it as ready to use
            self.train(description, match, needles, hay)
            return match
        except Exception as e:
            print(e)
            input()
            raise Exception(e)
        finally:
            print()

    def insert(self, description, data, grpbin):
        if grpbin is None:
            needles, hay = self._split_heap(self._strgrp.grps_for(description))
            hay = [ random.choice(list(grp)).key() for grp in hay ]
            key = gen_id(description, salt)
            grpbin = self._strgrp.grp_new(description, data)
            self._grpanns[key] = self._collection.load(key, grpbin.key())
            if key not in self._grpanns[key].accepted:
                self._train_positive(description, grpbin, needles, hay)
        else:
            assert gen_id(grpbin.key(), salt) in self._grpanns
            grpbin.add(self._strgrp, description, data)

    def add(self, description, data):
        self.insert(description, data, self.find_group(description))
