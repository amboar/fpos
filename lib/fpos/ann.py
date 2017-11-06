import hashlib
import os
import pygenann
import xdg

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
            ann = pygenann.genann(inputs, layers, hidden, outputs)
        else:
            # Assume this for the moment
            self.ready = { 'accept' : True, 'reject' : True }
        self.ann = ann

        self.description = description
        if description is None:
            self.canonical_path = None
        else:
            self.canonical_path = DescriptionAnn.derive_canonical(self.data_dir, description)
            self.accept(self.description)

    @staticmethod
    def get_data_dir(head=None, tail=None):
        if head is None:
            head = str(xdg.BaseDirectory.save_data_path("fpos"))
        if tail is None:
            tail = ("ann", "descriptions")
        return os.path.join(head, *tail)

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
            return os.path.readlink(path)
        return path

    @staticmethod
    def derive_canonical(data_dir, description):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(data_dir, *dentries)
        DescriptionAnn.ensure_dir(data_dir, dentries)
        return DescriptionAnn.get_canonical(path)

    def is_ready(self):
        print("{}: Ready? {}".format(self.description, repr(self.ready)))
        return self.ready['accept'] and self.ready['reject']

    def cache(self, description):
        did = DescriptionAnn.gen_id(description, salt)
        dentries = DescriptionAnn.gen_rel_dentries(did)
        path = os.path.join(self.data_dir, *dentries)
        print("Canonical description:\t{}".format(self.description))
        print("Provided description:\t{}".format(description))
        print("Description Path: {}".format(path))
        DescriptionAnn.ensure_dir(self.data_dir, dentries)
        if self.canonical_path is None:
            self.canonical_path = DescriptionAnn.get_canonical(path)
        
        print("Canonical path: {}".format(self.canonical_path))

        print("Writing ANN at canonical path")
        self.ann.write(self.canonical_path)

        if not (self.canonical_path == path or os.path.exists(path)):
            print("Linking description path to canonical path");
            os.symlink(self.canonical_path, path)

    def write(self):
        assert(self.canonical_path is not None)
        self.ann.write(self.canonical_path)

    def accept(self, description, iters=300, write=True):
        # FIXME: 0.5
        ret = self.ann.train(to_input(description), [1.0], 3, iters=iters)
        self.ready['accept'] = (self.ann.run(to_input(description))[0] >= 0.5)
        print("{}: Ready? {}".format(self.description, repr(self.ready)))
        if write and self.ready:
            self.cache(description)
        return ret

    def reject(self, description, iters=300, write=False):
        # FIXME: 0.5
        ret = self.ann.train(to_input(description), [0.0], 3, iters=iters)
        self.ready['reject'] = (self.ann.run(to_input(description))[0] < 0.5)
        print("{}: Ready? {}".format(self.description, repr(self.ready)))
        if write:
            self.write()
        return

    def run(self, description):
        return self.ann.run(to_input(description))[0]
