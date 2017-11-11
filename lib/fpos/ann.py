import hashlib
import os
import pygenann
import xdg
from pystrgrp import Strgrp

def to_input(string):
    return [float(ord(x)) for x in string]

salt = "382a55c995b1e53f3ad0a3ed1c5ae735b9c7adc0".encode("UTF-8")

class DescriptionAnn(object):
    def __init__(self, cache=None, ann=None, inputs=100, layers=1, hidden=100, outputs=1, description=None):

        if cache is None:
            cache = DescriptionAnn.get_data_dir()
        self.data_dir = cache

        if ann is None:
            self.ready = { 'accept' : False, 'reject' : False }
            self.ann = pygenann.genann(inputs, layers, hidden, outputs)
        else:
            # Assume this for the moment
            self.ready = { 'accept' : True, 'reject' : True }
            self.ann = ann

        self.description = description
        if description is None:
            self.canonical_path = None
        else:
            self.canonical_path = DescriptionAnn.derive_canonical(self.data_dir, description)
            if ann is None:
                self.accept(self.description)

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
            return DescriptionAnn(cache=cache, ann=ann, description=description)
        return DescriptionAnn(cache=cache, inputs=100, layers=1, hidden=100, outputs=1, description=description)

    @staticmethod
    def get_canonical(path):
        if os.path.islink(path):
            return os.readlink(path)
        return path

    @staticmethod
    def derive_canonical(data_dir, description):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(data_dir, *dentries)
        DescriptionAnn.ensure_dir(data_dir, dentries)
        return DescriptionAnn.get_canonical(path)

    def is_ready(self):
        return self.ready['accept'] and self.ready['reject']

    def cache(self, description):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(self.data_dir, *dentries)
        DescriptionAnn.ensure_dir(self.data_dir, dentries)
        if self.canonical_path is None:
            self.canonical_path = DescriptionAnn.get_canonical(path)

        self.ann.write(self.canonical_path)

        if not (self.canonical_path == path or os.path.exists(path)):
            os.symlink(self.canonical_path, path)

    def write(self):
        assert(self.canonical_path is not None)
        self.ann.write(self.canonical_path)

    def accept(self, description, iters=300, write=True):
        # FIXME: 0.5
        self.ready['accept'] = (self.ann.run(to_input(description))[0] >= 0.5)
        ret = self.ann.train(to_input(description), [1.0], 3, iters=iters)
        if write and self.is_ready():
            self.cache(description)
        return ret

    def reject(self, description, iters=300, write=True):
        # FIXME: 0.5
        self.ready['reject'] = (self.ann.run(to_input(description))[0] < 0.5)
        ret = self.ann.train(to_input(description), [0.0], 3, iters=iters)
        if write and self.is_ready():
            self.write()
        return

    def run(self, description):
        return self.ann.run(to_input(description))[0]

class CognitiveStrgrp(object):
    """ LOL """
    def __init__(self):
        self._strgrp = Strgrp()
        self._grpanns = {}

    def __iter__(self):
        return iter(self._strgrp)

    def _request_match(self, description, haystack):
        index = None
        need = True

        nota = len(haystack)
        print("Which description best matches '{}'?".format(description))
        print()
        for i, needle in enumerate(haystack):
            print("({})\t{}".format(i, needle.key()))
        print("({})\tNone of the above".format(nota))
        print()

        while need:
            result = input("Select: ")
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
                if grpbin not in self._grpanns:
                    self._grpanns[grpbin] = DescriptionAnn.load(grpbin.key())
            else:
                break
        return heap[:i], heap[i:]

    def train(self, description, needle, needles, hay):
        # Black magic follows: Hacky attempt at training NNs.
        print("Learning from feedback...")
        for straw in hay:
            if needle.ready['reject']:
                break
            needle.reject(straw)
            needle.accept(description)

        while not needle.ready['accept']:
            needle.accept(description)
            needle.accept(needle.description)

        for ann in needles:
            if ann != needle:
                # For the unlucky needles, use the description for negative
                # training
                while not ann.ready['reject']:
                    ann.reject(description)
                    # Also train on the initial description
                    ann.accept(ann.description)
        print()

    def find_group(self, description):
        # Check for an exact match, don't need fuzzy behaviour if we have one
        grpbin = self._strgrp.grp_exact(description)
        if grpbin is not None:
            return grpbin

        # Use a binary output NN trained for each group to determine
        # membership. Leverage the groups generated with strgrp as training
        # sets, with user feedback to break ambiguity

        # needles is the set of groups breaking the strgrp fuzz threshold.
        # These are the candidates groups for the current description.
        needles, hay = self._split_heap(self._strgrp.grps_for(description))
        if len(needles) == 0:
            return None

        # Score the description using each group's NN, to see if we find a
        # single candidate among the needles. If we do then we assume this is
        # the correct group
        anns = [ self._grpanns[grpbin] for grpbin in needles ]
        scores = [ ann.run(description) for ann in anns ]
        curr_ann = DescriptionAnn.load(description)
        if curr_ann.is_ready() && curr_ann.run(description) > max(max(scores), 0.5):
            # We can't have seen it if it's strictly greater, therefore it's a
            # new group
            return None

        # FIXME: 0.5
        passes = [ x >= 0.5 for x in scores ]
        ready = [ ann.is_ready() for ann in anns ]
        if all(ready):
            l_passes = len(passes)
            n_passes = sum(passes)
            if n_passes == 1 or (l_passes > 1 and n_passes == l_passes):
                i = passes.index(True)
                self.train(description, anns[i], anns, [grp.key() for grp in hay])
                return needles[i]

        # Otherwise get user input
        match = self._request_match(description, needles)

        # None means no group was matched an a new one should be created
        if match is None:
            return None

        # Otherwise, if the user confirmed membership of the description to a
        # candidate group, if the NN correctly predicted the membership then
        # mark it as ready to use
        i = needles.index(match)
        self.train(description, anns[i], anns, [grp.key() for grp in hay])

        return match

    def insert(self, description, data, group):
        if group is None:
            grpbin = self._strgrp.grp_new(description, data)
            self._grpanns[grpbin] = DescriptionAnn.load(grpbin.key())
        else:
            group.add(description, data)

    def add(self, description, data):
        self.insert(description, data, self.find_group(description))