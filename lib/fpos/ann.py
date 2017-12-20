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

def to_input(string):
    return [float(ord(x)) for x in string]

salt = "382a55c995b1e53f3ad0a3ed1c5ae735b9c7adc0".encode("UTF-8")

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

class DescriptionAnn(object):
    @staticmethod
    def get_data_dir(head=None, tail=None):
        if head is None:
            head = str(xdg.BaseDirectory.save_data_path("fpos"))
        if tail is None:
            tail = ("ann", "descriptions")
        path = os.path.join(head, *tail)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def gen_id(description, salt):
        s = hashlib.sha1()
        s.update(str(description).encode("UTF-8"))
        s.update(salt)
        return s.hexdigest()

    @staticmethod
    def gen_rel_dentries(did):
        return did[:2], did[2:]

    @staticmethod
    def ensure_dir(data_dir, dentries):
        assert os.path.exists(data_dir), "Expected present: {}".format(data_dir)
        abspath = os.path.join(data_dir, dentries[0])
        if not os.path.exists(abspath):
            os.mkdir(abspath)

    @staticmethod
    def have_ann(path):
        return os.path.exists(path)

    @staticmethod
    def load(description, cache=None):
        if cache is None:
            cache = DescriptionAnn.get_data_dir()

        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(cache, *dentries)

        if DescriptionAnn.have_ann(path):
            ann = pygenann.genann.read(path)
        else:
            ann = pygenann.genann(100, 2, 100, 1)

        return DescriptionAnn(cache, ann, description)

    @staticmethod
    def get_path(description, data_dir=None):
        if data_dir is None:
            data_dir = DescriptionAnn.get_data_dir()

        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        return os.path.join(data_dir, *dentries)

    @staticmethod
    def get_canonical(path):
        if os.path.islink(path):
            return os.readlink(path)
        return path

    @staticmethod
    def is_canonical(description, data_dir=None):
        if data_dir is None:
            data_dir = DescriptionAnn.get_data_dir()

        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(data_dir, *dentries)
        return os.path.exists(path) and path == DescriptionAnn.get_canonical(path)

    @staticmethod
    def derive_canonical(description, data_dir=None):
        if data_dir is None:
            data_dir = DescriptionAnn.get_data_dir()

        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(data_dir, *dentries)
        DescriptionAnn.ensure_dir(data_dir, dentries)
        return DescriptionAnn.get_canonical(path)

    def __init__(self, cache, ann, description):
        self.id = self.gen_id(description, salt)
        self.pd = PolarisationDetector()
        self.accepted = set()
        self.threshold = 3
        self.ready = { 'accept' : False, 'reject' : False }
        self.data_dir = cache
        self.ann = ann
        self.description = description
        self.canonical_path = DescriptionAnn.derive_canonical(description, self.data_dir)
        self.read_metadata(self.canonical_path)
        self.pd.accept(self.ready['accept'])
        self.pd.reject(self.ready['reject'])
        self.accept(description)

    def read_metadata(self, path):
        prop_path = path + ".properties"
        if not os.path.exists(prop_path):
            return

        with open(prop_path, "r", encoding="utf-8") as f:
            self.id = f.readline().strip()
            self.ready['accept'] = f.readline().strip() == "True"
            self.ready['reject'] = f.readline().strip() == "True"
            for line in f:
                self.accepted.add(line.strip())

    def write_metadata(self, path):
        with open(path + ".properties", "w", encoding="utf-8") as f:
            f.write("{}\n".format(self.id))
            f.write("{}\n".format(repr(self.ready['accept'])))
            f.write("{}\n".format(repr(self.ready['reject'])))
            for description in self.accepted:
                f.write("{}\n".format(description))

    def is_trained(self):
        return self.ready['accept'] and self.ready['reject']

    def is_polarised(self):
        return self.pd.is_polarised() 

    def meets_threshold(self):
        return len(self.accepted) > self.threshold

    def is_ready(self):
        return self.is_trained() and self.meets_threshold()

    def cache(self, description):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(self.data_dir, *dentries)
        DescriptionAnn.ensure_dir(self.data_dir, dentries)

        if not self.have_ann(self.canonical_path) or self.is_ready():
            self.ann.write(self.canonical_path)
            self.write_metadata(self.canonical_path)

        if self.canonical_path != path and not os.path.exists(path):
            os.symlink(self.canonical_path, path)

    def write(self):
        assert(self.canonical_path is not None)
        self.ann.write(self.canonical_path)

    def accept(self, description, iters=300):
        # FIXME: 0.5
        accepted = self.ann.run(to_input(description))[0] >= 0.5
        self.pd.accept(accepted)
        self.ready['accept'] = accepted
        self.accepted.add(DescriptionAnn.gen_id(description, salt))
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

class StatusLine(object):
    def __init__(self):
        self.line = ""
        pass

    def write(self, line, terminate=False):
        erase = [ '\b' ] * max(0, len(line) - len(self.line))
        print("{}\r{}".format(erase, line), end='', flush=True)
        self.line = line;
        if terminate:
            self.terminate()

    def terminate(self):
        print("", flush=True)
        self.line = ""

class CognitiveStrgrp(object):
    """ LOL """
    def __init__(self):
        self._strgrp = Strgrp()
        self._grpanns = dict()
        self._status = StatusLine()

    def __iter__(self):
        return iter(self._strgrp)

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
                key = DescriptionAnn.gen_id(grpbin.key(), salt)
                if key not in self._grpanns:
                    self._grpanns[key] = DescriptionAnn.load(grpbin.key())
            else:
                break
        return heap[:i], heap[i:]

    def _train_positive(self, description, pick, candidates, hay):
        ann = self._grpanns[DescriptionAnn.gen_id(pick.key(), salt)]

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
        ann = self._grpanns[DescriptionAnn.gen_id(grp.key(), salt)]
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
            assert DescriptionAnn.gen_id(grpbin.key(), salt) in self._grpanns
            print("Existing group: Exact match")
            return grpbin

        # Check for an existing mapping on disk
        path = DescriptionAnn.get_path(description)
        if DescriptionAnn.have_ann(path):
            # Add description to a group that has an on-disk mapping:
            with open(DescriptionAnn.get_canonical(path) + ".properties", "r") as f:
                cid = f.readline().strip()
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
        anns = [ self._grpanns[DescriptionAnn.gen_id(grpbin.key(), salt)]
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
            key = DescriptionAnn.gen_id(description, salt)
            grpbin = self._strgrp.grp_new(description, data)
            self._grpanns[key] = DescriptionAnn.load(grpbin.key())
        else:
            print("Adding to group of '{}'".format(grpbin.key()))
            assert DescriptionAnn.gen_id(grpbin.key(), salt) in self._grpanns
            grpbin.add(self._strgrp, description, data)

    def add(self, description, data):
        self.insert(description, data, self.find_group(description))
